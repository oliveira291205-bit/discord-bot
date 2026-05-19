#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from memory.memory_migration import import_obsidian_folder


def main() -> None:
    parser = argparse.ArgumentParser(description="Importa memorias antigas do Obsidian para SQLite local.")
    parser.add_argument("obsidian_path", help="Pasta antiga do cerebro no Obsidian")
    parser.add_argument("--sqlite-path", default="data/memory.sqlite3", help="Arquivo SQLite de destino")
    args = parser.parse_args()

    imported = import_obsidian_folder(args.obsidian_path, args.sqlite_path)
    print(f"Memorias importadas: {imported}")
    print("Arquivos originais do Obsidian nao foram apagados.")


if __name__ == "__main__":
    main()
