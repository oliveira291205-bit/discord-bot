from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ErrorHint:
    key: str
    title: str
    reply: str
    xp_reason: str = "programming_help"


ERROR_RULES: list[tuple[re.Pattern[str], ErrorHint]] = [
    (
        re.compile(r"ModuleNotFoundError: No module named ['\"]?discord|python: No module named discord", re.I),
        ErrorHint(
            "missing_discord",
            "discord.py faltando",
            "Esse erro significa que o `discord.py` nao esta instalado no ambiente atual.\n\n"
            "Tenta:\n```bash\npip install discord.py\n```\n"
            "Se estiver usando venv:\n```bash\n. .venv/bin/activate\npip install discord.py\n```",
        ),
    ),
    (
        re.compile(r"ModuleNotFoundError: No module named ['\"]?([a-zA-Z0-9_.-]+)['\"]?", re.I),
        ErrorHint(
            "missing_module",
            "modulo Python faltando",
            "Esse erro e modulo faltando no Python. Confere se voce esta no ambiente certo e instala o pacote:\n"
            "```bash\n. .venv/bin/activate  # se existir\npip install NOME_DO_PACOTE\n```",
        ),
    ),
    (
        re.compile(r"SyntaxError|IndentationError", re.I),
        ErrorHint(
            "syntax_error",
            "erro de sintaxe",
            "Isso e erro de sintaxe. O Python travou antes de rodar o codigo.\n\n"
            "Olha a linha marcada no erro e confere parenteses, aspas, dois-pontos e indentacao. "
            "Treino basico, mas derrota muito guerreiro.",
        ),
    ),
    (
        re.compile(r"Permission denied|permiss[aã]o negada", re.I),
        ErrorHint(
            "permission_denied",
            "permissao negada",
            "Permissao negada. No Termux, normalmente resolve assim:\n```bash\nchmod +x arquivo.sh\n```\n"
            "Se for pasta de armazenamento, rode:\n```bash\ntermux-setup-storage\n```",
            "termux",
        ),
    ),
    (
        re.compile(r"No such file or directory|arquivo ou diret[oó]rio inexistente", re.I),
        ErrorHint(
            "missing_file",
            "arquivo nao encontrado",
            "O caminho nao existe ou voce esta na pasta errada.\n\n"
            "Tenta:\n```bash\npwd\nls -la\n```\nDepois entra na pasta certa com `cd nome_da_pasta`.",
            "termux",
        ),
    ),
    (
        re.compile(r"dpkg was interrupted|dpkg --configure -a", re.I),
        ErrorHint(
            "dpkg_interrupted",
            "dpkg interrompido",
            "O pacote do Termux ficou pela metade. Corrige com:\n```bash\ndpkg --configure -a\npkg update -y\n```",
            "termux",
        ),
    ),
    (
        re.compile(r"maturin|jiter|rustc target|Rust not found", re.I),
        ErrorHint(
            "jiter_maturin",
            "build Rust/jiter no Termux",
            "Isso costuma acontecer quando algum pacote tenta compilar Rust no Android. "
            "Neste projeto, atualize e reinstale limpo:\n```bash\ngit pull\nrm -rf .venv\n./install_termux.sh\n```",
            "termux",
        ),
    ),
    (
        re.compile(r"fatal:.*git|git pull|git clone", re.I),
        ErrorHint(
            "git_error",
            "erro de Git",
            "Erro de Git. Primeiro confere a pasta e o remoto:\n```bash\npwd\ngit status\ngit remote -v\n```\n"
            "Se o repo estiver baguncado, manda o erro completo que a gente derrota por partes.",
            "git",
        ),
    ),
    (
        re.compile(r"\.env.*(not found|nao existe|não existe)|DISCORD_TOKEN nao configurado|DEEPSEEK_API_KEY nao", re.I),
        ErrorHint(
            "env_missing",
            ".env faltando",
            "Falta configurar o `.env`. No Termux roda:\n```bash\npython setup_env.py\n./run_bot.sh --debug\n```",
            "termux",
        ),
    ),
    (
        re.compile(r"PrivilegedIntentsRequired|Message Content Intent", re.I),
        ErrorHint(
            "discord_intents",
            "intent do Discord faltando",
            "O Discord recusou porque falta ativar `Message Content Intent` no Developer Portal.\n"
            "Vai em Application > Bot > Privileged Gateway Intents > ativa Message Content Intent > Save.",
        ),
    ),
    (
        re.compile(r"sqlite|database is locked|unable to open database", re.I),
        ErrorHint(
            "sqlite_error",
            "erro de SQLite",
            "Erro no SQLite. Confere se a pasta `data` existe e se da para escrever:\n```bash\nmkdir -p data\npython termux_check.py\n```",
            "termux",
        ),
    ),
    (
        re.compile(r"tesseract|OCR indisponivel|pytesseract", re.I),
        ErrorHint(
            "tesseract_error",
            "OCR/Tesseract",
            "OCR precisa do Tesseract instalado no Termux:\n```bash\npkg install tesseract\npkg install tesseract-lang-por || true\npython termux_check.py\n```",
            "termux",
        ),
    ),
    (
        re.compile(r"Traceback \(most recent call last\):", re.I),
        ErrorHint(
            "traceback",
            "traceback Python",
            "Isso e um traceback do Python. A parte mais importante geralmente fica nas ultimas linhas. "
            "Manda o final do erro ou olha a ultima excecao para atacar o inimigo certo.",
        ),
    ),
]


def detect_error_reply(text: str) -> ErrorHint | None:
    if not text or len(text.strip()) < 6:
        return None
    for pattern, hint in ERROR_RULES:
        if pattern.search(text):
            return hint
    return None
