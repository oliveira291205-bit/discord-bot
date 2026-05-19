#!/usr/bin/env sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
cd "$ROOT"

mask_status() {
    name="$1"
    eval "value=\${$name:-}"
    if [ -n "$value" ]; then
        echo "[debug] $name=OK"
    else
        echo "[debug] $name=VAZIO"
    fi
}

DEBUG=false
if [ "${1:-}" = "--debug" ]; then
    DEBUG=true
fi

if [ ! -f ".env" ]; then
    echo "Arquivo .env nao existe. Rode: ./install_termux.sh"
    exit 1
fi

set -a
. ./.env
set +a

if [ -x ".venv/bin/python" ]; then
    PYTHON_CMD=".venv/bin/python"
elif command -v python >/dev/null 2>&1; then
    PYTHON_CMD="python"
else
    PYTHON_CMD="python3"
fi

if [ "$DEBUG" = "true" ]; then
    echo "[debug] pasta: $ROOT"
    echo "[debug] python: $("$PYTHON_CMD" --version 2>&1)"
    echo "[debug] .env: OK"
    mask_status DISCORD_TOKEN
    mask_status DEEPSEEK_API_KEY
    mask_status DEEPSEEK_BASE_URL
    mask_status DEEPSEEK_MODEL
    mask_status BOT_ENTRYPOINT
    "$PYTHON_CMD" termux_check.py || true
fi

if [ -z "${DISCORD_TOKEN:-}" ]; then
    echo "DISCORD_TOKEN nao configurado. Rode: python setup_env.py"
    exit 1
fi

if [ -z "${DEEPSEEK_API_KEY:-}" ]; then
    echo "DEEPSEEK_API_KEY nao configurada. Rode: python setup_env.py"
    exit 1
fi

ENTRYPOINT="${BOT_ENTRYPOINT:-}"
if [ -z "$ENTRYPOINT" ]; then
    if [ -f "main.py" ]; then
        ENTRYPOINT="main.py"
    elif [ -f "bot.py" ]; then
        ENTRYPOINT="bot.py"
    elif [ -f "app.py" ]; then
        ENTRYPOINT="app.py"
    elif [ -f "rei_suzukawa/bot.py" ]; then
        ENTRYPOINT="rei_suzukawa.bot"
    else
        echo "Nao achei arquivo principal. Configure BOT_ENTRYPOINT no .env, exemplo: BOT_ENTRYPOINT=rei_suzukawa.bot"
        exit 1
    fi
fi

mkdir -p data logs

echo "Iniciando bot..."
if [ -f "$ENTRYPOINT" ]; then
    exec "$PYTHON_CMD" "$ENTRYPOINT"
fi

case "$ENTRYPOINT" in
    *.py)
        echo "BOT_ENTRYPOINT aponta para arquivo que nao existe: $ENTRYPOINT"
        exit 1
        ;;
    *)
        exec "$PYTHON_CMD" -m "$ENTRYPOINT"
        ;;
esac
