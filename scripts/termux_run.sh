#!/usr/bin/env sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$ROOT"

if [ ! -f ".env" ]; then
    echo "Arquivo .env nao existe. Rode ./scripts/termux_install.sh e preencha os tokens."
    exit 1
fi

if [ ! -x ".venv/bin/python" ]; then
    echo "Ambiente .venv nao existe. Rode ./scripts/termux_install.sh primeiro."
    exit 1
fi

mkdir -p data logs
exec .venv/bin/python -m rei_suzukawa.bot
