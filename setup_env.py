from __future__ import annotations

import getpass
from pathlib import Path


ENV_PATH = Path(".env")

DEFAULTS = {
    "DISCORD_TOKEN": "coloque_seu_token_aqui",
    "DEEPSEEK_API_KEY": "coloque_sua_key_aqui",
    "BOT_ENTRYPOINT": "rei_suzukawa.bot",
    "DEEPSEEK_BASE_URL": "https://api.deepseek.com",
    "DEEPSEEK_MODEL": "deepseek-v4-flash",
    "REI_PREFIX": "!",
    "REI_MAX_HISTORY": "14",
    "REI_TEMPERATURE": "0.55",
    "REI_AUTO_MEMORY": "true",
    "REI_OBSERVE_ALL_MESSAGES": "true",
    "REI_NATURAL_INTERACTIONS_ENABLED": "true",
    "REI_NATURAL_ALLOW_SPONTANEOUS": "true",
    "REI_NATURAL_REPLY_CHANCE": "0.03",
    "REI_NATURAL_COOLDOWN_SECONDS": "300",
    "REI_NATURAL_MAX_PER_HOUR": "5",
    "REI_NATURAL_MAX_PER_CHANNEL_HOUR": "3",
    "REI_NATURAL_AVOID_SERIOUS": "true",
    "REI_NATURAL_USE_AI": "false",
    "REI_MEMORY_ENABLED": "true",
    "REI_MEMORY_SQLITE_PATH": "data/memory.sqlite3",
    "REI_OCR_TMP_DIR": "data",
    "REI_MEMORY_USE_OBSIDIAN": "false",
    "REI_MEMORY_USE_EMBEDDINGS": "false",
    "REI_MEMORY_USE_AI_EXTRACTION": "false",
    "REI_MEMORY_USE_AI_SUMMARY": "false",
    "REI_MEMORY_MAX_INJECTED": "10",
    "REI_MEMORY_MAX_CHARS": "250",
    "REI_MEMORY_RECENT_CONTEXT_LIMIT": "10",
    "REI_RESENHA_LIMIT": "250",
    "REI_ATTACHMENT_MAX_BYTES": "8388608",
    "REI_GIFS_ENABLED": "true",
    "REI_GIF_COOLDOWN_SECONDS": "600",
    "REI_GIF_SEARCH_LIMIT": "12",
    "DEEPSEEK_MAX_TOTAL_PROMPT_CHARS": "24000",
    "DEEPSEEK_MAX_TOTAL_ESTIMATED_TOKENS": "6000",
    "DEEPSEEK_MAX_SYSTEM_PROMPT_CHARS": "4000",
    "DEEPSEEK_MAX_MEMORY_CONTEXT_CHARS": "5000",
    "DEEPSEEK_MAX_RECENT_CONTEXT_CHARS": "4000",
    "DEEPSEEK_MAX_USER_MESSAGE_CHARS": "3000",
    "DEEPSEEK_MAX_INJECTED_MEMORIES": "10",
    "DEEPSEEK_MAX_CHARS_PER_MEMORY": "250",
    "DEEPSEEK_HARD_BLOCK_CHARS": "32000",
    "DEEPSEEK_HARD_BLOCK_ESTIMATED_TOKENS": "8000",
    "DEEPSEEK_DEBUG_PROMPT_SIZE": "true",
}

SECRET_KEYS = {"DISCORD_TOKEN", "DEEPSEEK_API_KEY"}
PROMPT_KEYS = ["DISCORD_TOKEN", "DEEPSEEK_API_KEY", "BOT_ENTRYPOINT"]


def main() -> None:
    print("Configurando .env local. Nenhuma chave sera exibida ou enviada para internet.")
    values = DEFAULTS | read_env(ENV_PATH)

    for key in PROMPT_KEYS:
        current = values.get(key, "")
        if key in SECRET_KEYS:
            values[key] = prompt_secret(key, current)
        else:
            values[key] = prompt_text(key, current or DEFAULTS[key], required=True)

    for key, default in DEFAULTS.items():
        values.setdefault(key, default)

    write_env(ENV_PATH, values)
    try:
        ENV_PATH.chmod(0o600)
    except OSError:
        pass

    if not ENV_PATH.exists():
        raise SystemExit("Falha: .env nao foi criado.")
    print(".env configurado com seguranca. Valores secretos nao foram exibidos.")


def read_env(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def prompt_secret(key: str, current: str) -> str:
    if current and not is_placeholder(current):
        if ask_yes_no(f"{key}=OK. Manter valor atual? [S/n] ", default=True):
            return current
    while True:
        value = getpass.getpass(f"{key}: ").strip()
        if value:
            return value
        print(f"{key} nao pode ficar vazio.")


def prompt_text(key: str, current: str, *, required: bool) -> str:
    shown = current or DEFAULTS.get(key, "")
    answer = input(f"{key} [{shown}]: ").strip()
    value = answer or shown
    while required and not value:
        value = input(f"{key}: ").strip()
    return value


def ask_yes_no(prompt: str, *, default: bool) -> bool:
    answer = input(prompt).strip().lower()
    if not answer:
        return default
    return answer in {"s", "sim", "y", "yes"}


def is_placeholder(value: str) -> bool:
    lowered = value.lower()
    return "coloque_" in lowered or "seu_token" in lowered or "sua_key" in lowered


def write_env(path: Path, values: dict[str, str]) -> None:
    ordered_keys = list(DEFAULTS)
    extra_keys = sorted(key for key in values if key not in DEFAULTS)
    lines = []
    for key in [*ordered_keys, *extra_keys]:
        lines.append(f"{key}={values[key]}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
