from __future__ import annotations

import io
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


MAX_EXTRACTED_CHARS = 9000
TEXT_EXTENSIONS = {".txt", ".md", ".csv", ".json", ".log", ".py", ".js", ".ts", ".html", ".css", ".xml"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}


class DiscordAttachment(Protocol):
    filename: str
    content_type: str | None
    size: int
    url: str

    async def read(self) -> bytes:
        ...


@dataclass(frozen=True)
class AttachmentAnalysis:
    filename: str
    content_type: str
    size: int
    url: str
    kind: str
    extracted_text: str
    note: str = ""

    @property
    def has_content(self) -> bool:
        return bool(self.extracted_text.strip())


async def analyze_attachment(attachment: DiscordAttachment, *, max_bytes: int) -> AttachmentAnalysis:
    filename = attachment.filename or "anexo"
    content_type = attachment.content_type or guess_content_type(filename)
    kind = classify_attachment(filename, content_type)

    if attachment.size > max_bytes:
        return AttachmentAnalysis(
            filename=filename,
            content_type=content_type,
            size=attachment.size,
            url=attachment.url,
            kind=kind,
            extracted_text="",
            note=f"arquivo ignorado porque tem {attachment.size} bytes e passa do limite de {max_bytes} bytes",
        )

    if kind == "outro":
        return AttachmentAnalysis(
            filename=filename,
            content_type=content_type,
            size=attachment.size,
            url=attachment.url,
            kind=kind,
            extracted_text="",
            note="tipo de arquivo sem leitor configurado",
        )

    data = await attachment.read()
    if kind == "pdf":
        text, note = extract_pdf_text(data)
    elif kind == "imagem":
        text, note = extract_image_text(data)
    else:
        text, note = extract_plain_text(data)

    return AttachmentAnalysis(
        filename=filename,
        content_type=content_type,
        size=attachment.size,
        url=attachment.url,
        kind=kind,
        extracted_text=trim_extracted_text(text),
        note=note,
    )


def classify_attachment(filename: str, content_type: str | None) -> str:
    lowered_name = filename.lower()
    lowered_type = (content_type or "").lower()
    suffix = "." + lowered_name.rsplit(".", 1)[-1] if "." in lowered_name else ""

    if lowered_type == "application/pdf" or suffix == ".pdf":
        return "pdf"
    if lowered_type.startswith("image/") or suffix in IMAGE_EXTENSIONS:
        return "imagem"
    if lowered_type.startswith("text/") or suffix in TEXT_EXTENSIONS:
        return "texto"
    return "outro"


def guess_content_type(filename: str) -> str:
    lowered = filename.lower()
    if lowered.endswith(".pdf"):
        return "application/pdf"
    if any(lowered.endswith(ext) for ext in IMAGE_EXTENSIONS):
        return "image/*"
    if any(lowered.endswith(ext) for ext in TEXT_EXTENSIONS):
        return "text/plain"
    return "application/octet-stream"


def extract_plain_text(data: bytes) -> tuple[str, str]:
    for encoding in ("utf-8", "latin-1"):
        try:
            return data.decode(encoding), f"texto lido como {encoding}"
        except UnicodeDecodeError:
            continue
    return "", "nao consegui decodificar o texto desse arquivo"


def extract_pdf_text(data: bytes) -> tuple[str, str]:
    try:
        from pypdf import PdfReader
    except ImportError:
        return "", "instale `pypdf` para ler PDFs"

    try:
        reader = PdfReader(io.BytesIO(data))
        pages: list[str] = []
        for index, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            if text.strip():
                pages.append(f"[pagina {index}]\n{text.strip()}")
        if pages:
            return "\n\n".join(pages), f"PDF lido com {len(reader.pages)} pagina(s)"
        return "", "PDF sem texto extraivel; se for escaneado, precisa OCR por imagem"
    except Exception as exc:
        return "", f"erro lendo PDF: {exc}"


def extract_image_text(data: bytes) -> tuple[str, str]:
    try:
        from PIL import Image
        import pytesseract
    except ImportError:
        return "", "instale `pillow` e `pytesseract` para OCR de imagens"

    tesseract_cmd = find_tesseract_command()
    if not tesseract_cmd:
        return "", "OCR indisponivel: binario `tesseract` nao esta instalado no sistema"

    try:
        if len(tesseract_cmd) == 1:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd[0]
            with Image.open(io.BytesIO(data)) as image:
                text = image_to_string_with_fallback(pytesseract, image)
        else:
            text = run_tesseract_command(data, tesseract_cmd)
        if text.strip():
            return text, "texto extraido da imagem por OCR"
        return "", "nao encontrei texto legivel na imagem"
    except Exception as exc:
        return "", f"erro fazendo OCR da imagem: {exc}"


def image_to_string_with_fallback(pytesseract_module: object, image: object) -> str:
    errors: list[str] = []
    for language in ("por+eng", "eng", None):
        try:
            if language:
                return pytesseract_module.image_to_string(image, lang=language)
            return pytesseract_module.image_to_string(image)
        except Exception as exc:
            errors.append(str(exc))
    raise RuntimeError("; ".join(errors[-2:]) or "OCR falhou")


def find_tesseract_command() -> list[str] | None:
    configured = os.getenv("TESSERACT_CMD")
    if configured:
        return [configured]

    local = shutil.which("tesseract")
    if local:
        return [local]

    flatpak_spawn = shutil.which("flatpak-spawn")
    if flatpak_spawn:
        try:
            result = subprocess.run(
                [flatpak_spawn, "--host", "sh", "-lc", "command -v tesseract"],
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
            )
        except (OSError, subprocess.SubprocessError):
            result = None
        if result and result.returncode == 0 and result.stdout.strip():
            return [flatpak_spawn, "--host", result.stdout.strip().splitlines()[0]]

    return None


def run_tesseract_command(data: bytes, command: list[str]) -> str:
    from PIL import Image

    temp_root = Path(os.getenv("REI_OCR_TMP_DIR", Path.cwd()))
    with tempfile.TemporaryDirectory(prefix="rei-suzukawa-ocr-", dir=temp_root) as tmp:
        tmp_path = Path(tmp)
        input_path = tmp_path / "imagem.png"
        output_base = tmp_path / "saida"
        with Image.open(io.BytesIO(data)) as image:
            image.save(input_path)

        last_error = ""
        for language in ("por+eng", "eng", ""):
            args = [*command, str(input_path), str(output_base)]
            if language:
                args.extend(["-l", language])
            result = subprocess.run(
                args,
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
            )
            output_path = output_base.with_suffix(".txt")
            if result.returncode == 0 and output_path.exists():
                return output_path.read_text(encoding="utf-8", errors="replace")
            last_error = result.stderr.strip() or "sem detalhe"
        raise RuntimeError(f"tesseract falhou: {last_error}")


def trim_extracted_text(text: str, limit: int = MAX_EXTRACTED_CHARS) -> str:
    clean = "\n".join(line.rstrip() for line in (text or "").splitlines()).strip()
    if len(clean) <= limit:
        return clean
    return clean[:limit].rstrip() + "\n...[conteudo cortado para caber no prompt]"


def format_attachment_context(analyses: list[AttachmentAnalysis]) -> str:
    if not analyses:
        return ""

    lines = ["Anexos desta conversa:"]
    for index, analysis in enumerate(analyses, start=1):
        lines.append(
            f"{index}. {analysis.filename} ({analysis.kind}, {analysis.content_type}, {analysis.size} bytes)"
        )
        lines.append(f"   URL: {analysis.url}")
        if analysis.note:
            lines.append(f"   Nota: {analysis.note}")
        if analysis.extracted_text:
            lines.append("   Conteudo extraido:")
            lines.append(indent_block(analysis.extracted_text, "   "))
    return "\n".join(lines)


def format_attachment_memory(analyses: list[AttachmentAnalysis]) -> str:
    context = format_attachment_context(analyses)
    if not context:
        return ""
    return "Anexos recebidos no Discord e processados pelo Goku.\n" + context


def attachment_branches(analyses: list[AttachmentAnalysis]) -> list[str]:
    branches = ["anexos"]
    kinds = {analysis.kind for analysis in analyses}
    if "imagem" in kinds:
        branches.append("imagens")
    if "pdf" in kinds:
        branches.append("pdfs")
    if "texto" in kinds:
        branches.append("documentos")
    if any(
        "cardap" in analysis.extracted_text.lower()
        or "menu" in analysis.extracted_text.lower()
        or "cardap" in analysis.filename.lower()
        for analysis in analyses
    ):
        branches.append("cardapios")
    return branches


def indent_block(text: str, prefix: str) -> str:
    return "\n".join(f"{prefix}{line}" for line in text.splitlines())
