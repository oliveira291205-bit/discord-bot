from __future__ import annotations

import platform
import shutil
import sys
import time
from dataclasses import dataclass
from pathlib import Path


STATUS_PATTERN_WORDS = (
    "status do bot",
    "goku status",
    "bot ta online",
    "bot tá online",
    "como voce esta",
    "como você está",
    "diagnostico",
    "diagnóstico",
)


@dataclass(frozen=True)
class BotStatusInfo:
    deepseek_enabled: bool
    memory_ok: bool
    memory_error: str | None
    sqlite_path: str
    started_at: float


def wants_status(text: str) -> bool:
    lowered = (text or "").lower()
    return any(word in lowered for word in STATUS_PATTERN_WORDS)


def render_status(info: BotStatusInfo) -> str:
    uptime = format_uptime(time.monotonic() - info.started_at)
    tesseract = "OK" if shutil.which("tesseract") else "indisponivel"
    environment = "Termux" if is_termux() else platform.system()
    memory = "OK" if info.memory_ok else f"ERRO ({info.memory_error or 'sem detalhe'})"
    return (
        "Status do treino:\n"
        f"- Bot: online\n"
        f"- DeepSeek: {'configurado' if info.deepseek_enabled else 'sem key'}\n"
        f"- SQLite/memoria: {memory}\n"
        f"- Banco: `{info.sqlite_path}`\n"
        f"- OCR/Tesseract: {tesseract}\n"
        f"- Ambiente: {environment}\n"
        f"- Python: {sys.version.split()[0]}\n"
        f"- Uptime: {uptime}"
    )


def is_termux() -> bool:
    prefix = Path(sys.prefix)
    return "com.termux" in str(prefix) or Path("/data/data/com.termux").exists()


def format_uptime(seconds: float) -> str:
    total = int(max(0, seconds))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}h {minutes}m {secs}s"
    if minutes:
        return f"{minutes}m {secs}s"
    return f"{secs}s"
