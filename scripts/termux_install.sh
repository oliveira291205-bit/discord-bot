#!/usr/bin/env sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$ROOT"

if command -v pkg >/dev/null 2>&1; then
    pkg update -y
    pkg install -y python git clang libjpeg-turbo zlib freetype libpng
fi

PYTHON_BIN="${PYTHON_BIN:-python}"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    PYTHON_BIN="python3"
fi

if [ ! -x ".venv/bin/python" ]; then
    "$PYTHON_BIN" -m venv .venv
fi

.venv/bin/python -m pip install --upgrade pip setuptools wheel
.venv/bin/python -m pip install -r requirements.txt

mkdir -p data logs

if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "Criei .env a partir de .env.example. Edite DISCORD_TOKEN e DEEPSEEK_API_KEY antes de rodar."
else
    echo ".env ja existe. Nao mexi nele."
fi

echo "Instalacao Termux concluida."
echo "Para rodar: ./scripts/termux_run.sh"
