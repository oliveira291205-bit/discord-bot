from __future__ import annotations

import re

from .memory_privacy import is_sensitive_memory, wants_no_save
from .memory_types import MemoryCandidate, SCOPE_CHANNEL, SCOPE_GUILD, SCOPE_USER, SCOPE_USER_CHANNEL


DIRECT_REMEMBER_PATTERN = re.compile(r"\b(lembra que|guarda isso|salva isso|nao esquece|não esquece)\b", re.IGNORECASE)


def extract_memories_from_message(message: str, *, channel_name: str | None = None) -> list[MemoryCandidate]:
    text = " ".join((message or "").split())
    if len(text) < 8 or wants_no_save(text) or is_sensitive_memory(text):
        return []

    candidates: list[MemoryCandidate] = []
    lowered = text.lower()
    direct = bool(DIRECT_REMEMBER_PATTERN.search(text))

    channel_context = bool(re.search(r"\bneste canal|nesse canal|aqui no canal\b", text, flags=re.IGNORECASE))
    add_user_patterns(candidates, text, direct, channel_context=channel_context)
    add_user_channel_patterns(candidates, text, direct)
    add_channel_patterns(candidates, text, channel_name, direct)
    add_guild_patterns(candidates, text, direct)

    if direct and not candidates:
        cleaned = clean_directive(text)
        if cleaned:
            candidates.append(
                MemoryCandidate(
                    scope_type=SCOPE_USER,
                    memory_type="fact",
                    content=f"O usuario pediu para lembrar: {cleaned}.",
                    tags=["lembrado", "manual"],
                    importance=10,
                    confidence=0.9,
                )
            )

    if "corrige" in lowered or "correcao" in lowered or "correção" in lowered:
        candidates.append(
            MemoryCandidate(
                scope_type=SCOPE_USER,
                memory_type="correction",
                content=f"O usuario fez uma correcao: {text}.",
                tags=["correcao"],
                importance=8,
                confidence=0.75,
            )
        )

    return dedupe_candidates(candidates)


def add_user_patterns(candidates: list[MemoryCandidate], text: str, direct: bool, *, channel_context: bool = False) -> None:
    patterns = [
        (r"\bmeu nome (?:e|é) ([^,.!?;]{2,80})", "O usuario declarou que seu nome e {}.", "fact", ["nome"], 10),
        (r"\bme chama de ([^,.!?;]{2,80})", "O usuario prefere ser chamado de {}.", "preference", ["apelido"], 10),
        (r"\bpode me chamar de ([^,.!?;]{2,80})", "O usuario prefere ser chamado de {}.", "preference", ["apelido"], 10),
        (r"\beu gosto de ([^,.!?;]{3,160})", "O usuario gosta de {}.", "preference", ["gosto"], 7),
        (r"\bgosto de ([^,.!?;]{3,160})", "O usuario gosta de {}.", "preference", ["gosto"], 7),
        (r"\beu prefiro ([^,.!?;]{3,160})", "O usuario prefere {}.", "preference", ["preferencia"], 8),
        (r"\bprefiro ([^,.!?;]{3,160})", "O usuario prefere {}.", "preference", ["preferencia"], 8),
        (r"\bmeu projeto (?:e|é|atual e|atual é) ([^,.!?;]{3,180})", "O projeto atual do usuario e {}.", "project", ["projeto"], 9),
        (r"\bestou criando ([^,.!?;]{3,180})", "O usuario esta criando {}.", "project", ["projeto"], 8),
        (r"\bestou fazendo ([^,.!?;]{3,180})", "O usuario esta fazendo {}.", "project", ["projeto"], 7),
        (r"\beu estudo ([^,.!?;]{3,160})", "O usuario estuda {}.", "fact", ["estudo"], 7),
        (r"\bestou estudando ([^,.!?;]{3,160})", "O usuario esta estudando {}.", "fact", ["estudo"], 7),
        (r"\beu trabalho com ([^,.!?;]{3,160})", "O usuario trabalha com {}.", "fact", ["trabalho"], 8),
        (r"\bquero que voce responda ([^,.!?;]{3,180})", "O usuario prefere que o Goku responda {}.", "preference", ["tom", "resposta"], 9),
        (r"\bquero que você responda ([^,.!?;]{3,180})", "O usuario prefere que o Goku responda {}.", "preference", ["tom", "resposta"], 9),
    ]
    channel_scoped_tags = {"gosto", "estudo"}
    for pattern, template, memory_type, tags, importance in patterns:
        if channel_context and set(tags) & channel_scoped_tags:
            continue
        for match in re.findall(pattern, text, flags=re.IGNORECASE):
            value = clean_value(match)
            if value:
                candidates.append(
                    MemoryCandidate(
                        scope_type=SCOPE_USER,
                        memory_type=memory_type,
                        content=template.format(value),
                        tags=tags,
                        importance=10 if direct and importance < 10 else importance,
                        confidence=0.9 if direct else 0.82,
                    )
                )


def add_user_channel_patterns(candidates: list[MemoryCandidate], text: str, direct: bool) -> None:
    if re.search(r"\bneste canal|nesse canal|aqui no canal|aqui\b", text, flags=re.IGNORECASE):
        for pattern, template, tags in [
            (r"\bestou estudando ([^,.!?;]{3,160})", "Neste canal, o usuario costuma estudar {}.", ["estudo", "canal"]),
            (r"\beu gosto de ([^,.!?;]{3,160})", "Neste canal, o usuario gosta de {}.", ["gosto", "canal"]),
            (r"\bgosto de ([^,.!?;]{3,160})", "Neste canal, o usuario gosta de {}.", ["gosto", "canal"]),
            (r"\beu prefiro ([^,.!?;]{3,160})", "Neste canal, o usuario prefere {}.", ["preferencia", "canal"]),
            (r"\bprefiro ([^,.!?;]{3,160})", "Neste canal, o usuario prefere {}.", ["preferencia", "canal"]),
            (r"\bestou criando ([^,.!?;]{3,180})", "Neste canal, o usuario trabalha em {}.", ["projeto", "canal"]),
        ]:
            for match in re.findall(pattern, text, flags=re.IGNORECASE):
                value = clean_value(match)
                if value:
                    candidates.append(
                        MemoryCandidate(
                            scope_type=SCOPE_USER_CHANNEL,
                            memory_type="context",
                            content=template.format(value),
                            tags=tags,
                            importance=8 if direct else 6,
                            confidence=0.82,
                        )
                    )


def add_channel_patterns(
    candidates: list[MemoryCandidate],
    text: str,
    channel_name: str | None,
    direct: bool,
) -> None:
    patterns = [
        (r"\bneste canal a gente (?:so|só) fala de ([^,.!?;]{3,160})", "Este canal e usado principalmente para {}.", ["canal", "regra"]),
        (r"\bnesse canal a gente (?:so|só) fala de ([^,.!?;]{3,160})", "Este canal e usado principalmente para {}.", ["canal", "regra"]),
        (r"\ba regra aqui (?:e|é) ([^,.!?;]{3,180})", "Regra deste canal: {}.", ["canal", "regra"]),
    ]
    for pattern, template, tags in patterns:
        for match in re.findall(pattern, text, flags=re.IGNORECASE):
            value = clean_value(match)
            if value:
                candidates.append(
                    MemoryCandidate(
                        scope_type=SCOPE_CHANNEL,
                        memory_type="rule",
                        content=template.format(value),
                        tags=[*tags, channel_name or "canal"],
                        importance=10 if direct else 9,
                        confidence=0.88,
                    )
                )


def add_guild_patterns(candidates: list[MemoryCandidate], text: str, direct: bool) -> None:
    patterns = [
        (r"\bnesse servidor ([^,.!?;]{3,180})", "Contexto do servidor: {}.", "context", ["servidor"]),
        (r"\ba regra do servidor (?:e|é) ([^,.!?;]{3,180})", "Regra do servidor: {}.", "rule", ["servidor", "regra"]),
    ]
    for pattern, template, memory_type, tags in patterns:
        for match in re.findall(pattern, text, flags=re.IGNORECASE):
            value = clean_value(match)
            if value:
                candidates.append(
                    MemoryCandidate(
                        scope_type=SCOPE_GUILD,
                        memory_type=memory_type,
                        content=template.format(value),
                        tags=tags,
                        importance=10 if direct else 8,
                        confidence=0.78,
                    )
                )


def clean_directive(text: str) -> str:
    cleaned = re.sub(r"\b(lembra que|guarda isso|salva isso|nao esquece|não esquece)\b", " ", text, flags=re.IGNORECASE)
    return clean_value(cleaned)


def clean_value(value: object) -> str:
    text = " ".join(str(value or "").split()).strip(" .,:;!?")
    text = re.split(r"\s+e\s+(?:eu|estou|meu|minha|nesse|neste)\b", text, maxsplit=1, flags=re.IGNORECASE)[0]
    return text[:220].strip(" .,:;!?")


def dedupe_candidates(candidates: list[MemoryCandidate]) -> list[MemoryCandidate]:
    seen: set[tuple[str, str, str]] = set()
    unique: list[MemoryCandidate] = []
    for candidate in candidates:
        key = (candidate.scope_type, candidate.memory_type, normalize(candidate.content))
        if key in seen:
            continue
        seen.add(key)
        unique.append(candidate)
    return unique[:8]


def normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()
