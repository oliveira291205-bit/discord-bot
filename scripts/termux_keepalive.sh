#!/usr/bin/env sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$ROOT"

mkdir -p logs

while :; do
    ./scripts/termux_run.sh 2>&1 | tee -a logs/bot.log
    echo "Bot parou. Reiniciando em 10 segundos..." | tee -a logs/bot.log
    sleep 10
done
