from __future__ import annotations

import logging
from pathlib import Path

from .memory_config import MemoryConfig
from .memory_store import SQLiteMemoryStore

LOGGER = logging.getLogger("rei_suzukawa.memory_migration")


def import_obsidian_folder(obsidian_path: str | Path, sqlite_path: str | Path, *, limit_chars: int = 900) -> int:
    root = Path(obsidian_path).expanduser()
    if not root.exists():
        raise FileNotFoundError(f"Pasta nao encontrada: {root}")

    store = SQLiteMemoryStore(sqlite_path, use_fts5=True)
    imported = 0
    try:
        for path in sorted(root.rglob("*.md")):
            text = extract_markdown_memory(path.read_text(encoding="utf-8", errors="replace"))
            if not text:
                continue
            if len(text) > limit_chars:
                text = text[: limit_chars - 3].rstrip() + "..."
            tags = ["obsidian_import", *[part for part in path.relative_to(root).parts[:-1]][:4]]
            if store.insert_imported_memory(content=text, tags=tags, scope_type="global", memory_type="summary", importance=4):
                imported += 1
    finally:
        store.close()
    return imported


def extract_markdown_memory(content: str) -> str:
    clean = strip_frontmatter(content)
    lines = []
    for line in clean.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("Hub:") or stripped.startswith("Ramos:") or stripped.startswith("Usuario:"):
            continue
        lines.append(stripped)
        if len(" ".join(lines)) > 900:
            break
    return " ".join(lines).strip()


def strip_frontmatter(content: str) -> str:
    if content.startswith("---\n") and "\n---\n" in content[4:]:
        return content.split("\n---\n", 1)[1]
    return content
