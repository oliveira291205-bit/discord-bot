from __future__ import annotations

import os
import shutil
import sqlite3
from pathlib import Path


def main() -> None:
    print("[check] Diagnostico local do bot")
    check_env()
    check_sqlite()
    check_imports()
    check_tesseract()


def check_env() -> None:
    env_path = Path(".env")
    print(f"[check] .env: {'OK' if env_path.exists() else 'FALTANDO'}")
    values = read_env(env_path)
    for key in ("DISCORD_TOKEN", "DEEPSEEK_API_KEY", "REI_MEMORY_SQLITE_PATH"):
        print(f"[check] {key}: {'OK' if values.get(key) else 'VAZIO'}")


def check_sqlite() -> None:
    db_path = Path(os.getenv("REI_MEMORY_SQLITE_PATH", "data/memory.sqlite3"))
    try:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE IF NOT EXISTS termux_check (id INTEGER PRIMARY KEY, ok TEXT)")
        conn.execute("INSERT INTO termux_check(ok) VALUES ('ok')")
        conn.commit()
        conn.close()
        print(f"[check] SQLite escrita: OK ({db_path})")
    except Exception as exc:
        print(f"[check] SQLite escrita: ERRO ({exc})")


def check_imports() -> None:
    for module in (
        "discord",
        "httpx",
        "pypdf",
        "PIL",
        "pytesseract",
        "features.member_index",
        "features.gif_reactions",
        "features.activation",
    ):
        try:
            __import__(module)
            print(f"[check] import {module}: OK")
        except Exception as exc:
            print(f"[check] import {module}: ERRO ({exc})")


def check_tesseract() -> None:
    configured = os.getenv("TESSERACT_CMD")
    command = configured or shutil.which("tesseract")
    if command:
        print(f"[check] tesseract: OK ({command})")
    else:
        print("[check] tesseract: FALTANDO. Instale com: pkg install tesseract")


def read_env(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


if __name__ == "__main__":
    main()
