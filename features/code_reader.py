from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


ALLOWED_SUFFIXES = {
    ".py",
    ".md",
    ".txt",
    ".sh",
    ".toml",
    ".yaml",
    ".yml",
    ".json",
    ".example",
}
ALLOWED_FILENAMES = {".gitignore", "AGENTS.md", "README.md", "README_TERMUX.md"}
BLOCKED_NAMES = {".env", ".env.local"}
BLOCKED_PARTS = {".git", ".venv", "venv", "__pycache__", "data", "logs", ".vscode", ".idea"}
BLOCKED_SUFFIXES = {".sqlite3", ".db", ".log", ".pyc", ".png", ".jpg", ".jpeg", ".gif", ".pdf"}


@dataclass(frozen=True)
class CodeReadResult:
    ok: bool
    path: str
    content: str
    truncated: bool = False


def list_code_files(root: Path, limit: int = 140) -> list[str]:
    base = root.resolve()
    paths: list[str] = []
    for item in sorted(base.rglob("*")):
        if not item.is_file() or _is_blocked_path(base, item):
            continue
        if not _is_allowed_file(item):
            continue
        paths.append(item.relative_to(base).as_posix())
        if len(paths) >= limit:
            break
    return paths


def summarize_codebase(root: Path) -> str:
    files = list_code_files(root)
    groups: dict[str, list[str]] = {}
    for file_path in files:
        top = file_path.split("/", 1)[0]
        groups.setdefault(top, []).append(file_path)

    lines = [
        "Eu consigo ler meu proprio codigo em modo seguro, mas nao altero arquivo nenhum.",
        "Mapa rapido do projeto:",
    ]
    for group, group_files in sorted(groups.items()):
        shown = ", ".join(group_files[:5])
        extra = len(group_files) - 5
        if extra > 0:
            shown = f"{shown}, +{extra} arquivo(s)"
        lines.append(f"- {group}: {shown}")
    return "\n".join(lines)


def read_code_file(root: Path, requested_path: str, max_chars: int = 6000) -> CodeReadResult:
    base = root.resolve()
    raw = (requested_path or "").strip()
    if not raw:
        return CodeReadResult(False, "", "Me diz o caminho do arquivo. Exemplo: `!codigo arquivo rei_suzukawa/bot.py`.")

    try:
        target = _resolve_inside(base, raw)
    except ValueError as exc:
        return CodeReadResult(False, raw, str(exc))

    if not target.exists() or not target.is_file():
        return CodeReadResult(False, raw, "Nao achei esse arquivo no projeto.")
    if _is_blocked_path(base, target) or not _is_allowed_file(target):
        return CodeReadResult(False, raw, "Esse arquivo nao pode ser lido por seguranca.")

    try:
        text = target.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return CodeReadResult(False, raw, f"Nao consegui ler esse arquivo: {exc}")

    truncated = len(text) > max_chars
    if truncated:
        text = text[:max_chars].rstrip() + "\n\n... [arquivo cortado por limite de leitura]"

    return CodeReadResult(True, target.relative_to(base).as_posix(), text, truncated=truncated)


def _resolve_inside(base: Path, requested_path: str) -> Path:
    raw_path = Path(requested_path)
    if raw_path.is_absolute():
        raise ValueError("Use caminho relativo dentro do projeto, nao caminho absoluto.")
    target = (base / raw_path).resolve()
    try:
        target.relative_to(base)
    except ValueError as exc:
        raise ValueError("Esse caminho tenta sair da pasta do projeto, entao bloqueei.") from exc
    return target


def _is_blocked_path(base: Path, path: Path) -> bool:
    try:
        relative = path.resolve().relative_to(base)
    except ValueError:
        return True
    parts = set(relative.parts)
    if parts & BLOCKED_PARTS:
        return True
    name = path.name.lower()
    if name in BLOCKED_NAMES or ".env" in name:
        return True
    return path.suffix.lower() in BLOCKED_SUFFIXES


def _is_allowed_file(path: Path) -> bool:
    if path.name in ALLOWED_FILENAMES:
        return True
    return path.suffix.lower() in ALLOWED_SUFFIXES
