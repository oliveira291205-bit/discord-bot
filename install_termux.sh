#!/usr/bin/env sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
cd "$ROOT"

echo "Preparando bot no Termux..."

if command -v pkg >/dev/null 2>&1; then
    pkg update -y
    pkg install -y python git nano openssl clang libjpeg-turbo zlib freetype libpng
    pkg install -y tesseract || echo "Aviso: nao consegui instalar tesseract automaticamente."
    pkg install -y tesseract-lang-por || pkg install -y tesseract-lang || echo "Aviso: pacote de idioma do tesseract indisponivel; OCR tentara ingles/padrao."
    echo "Opcional: para usar termux-wake-lock, instale o app Termux:API e rode: pkg install termux-api"
else
    echo "pkg nao encontrado. Continuando sem instalar pacotes do sistema."
fi

PYTHON_BIN="${PYTHON_BIN:-python}"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    PYTHON_BIN="python3"
fi
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    echo "Python nao encontrado. Instale com: pkg install python"
    exit 1
fi

PIP_TARGET="system"
if "$PYTHON_BIN" -m venv .venv >/tmp/goku_venv.log 2>&1; then
    PYTHON_CMD=".venv/bin/python"
    PIP_TARGET="venv"
else
    echo "Nao consegui criar .venv; vou instalar no Python local do Termux."
    cat /tmp/goku_venv.log 2>/dev/null || true
    PYTHON_CMD="$PYTHON_BIN"
fi

"$PYTHON_CMD" -m ensurepip --upgrade >/dev/null 2>&1 || true
"$PYTHON_CMD" -m pip install --upgrade pip setuptools wheel

if [ -f requirements.txt ]; then
    "$PYTHON_CMD" -m pip install -r requirements.txt
else
    echo "requirements.txt nao encontrado. Instale as dependencias manualmente."
fi

mkdir -p data logs

"$PYTHON_CMD" setup_env.py
"$PYTHON_CMD" termux_check.py || true

chmod +x run_bot.sh

echo "Instalacao concluida usando: $PIP_TARGET"
echo "Para iniciar o bot: ./run_bot.sh"
echo "Para debug seguro: ./run_bot.sh --debug"

printf "Iniciar o bot agora? [s/N] "
read START_NOW || START_NOW=""
case "$START_NOW" in
    s|S|sim|SIM|y|Y|yes|YES) ./run_bot.sh ;;
    *) echo "Beleza. Quando quiser rodar: ./run_bot.sh" ;;
esac
