from __future__ import annotations

import re


NO_SAVE_PATTERN = re.compile(
    r"\b(nao|não)\s+(guarda|salva|memoriza|lembra)|\b(nao|não)\s+registre|\bsem\s+guardar\b",
    re.IGNORECASE,
)
FORGET_PATTERN = re.compile(
    r"\b(esquece|apaga|remove|limpa)\s+(isso|essa|esse|da sua memoria|da memória|minha memoria|minha memória)\b",
    re.IGNORECASE,
)
QUERY_SELF_PATTERN = re.compile(r"\bo que (voce|você) lembra de mim\??", re.IGNORECASE)
QUERY_CHANNEL_PATTERN = re.compile(r"\bo que (voce|você) lembra (deste|desse|do) canal\??", re.IGNORECASE)

SENSITIVE_PATTERNS = [
    re.compile(r"\b(senha|password|token|api[_-]?key|apikey|secret|authorization|bearer)\b", re.IGNORECASE),
    re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b"),
    re.compile(r"\b\d{2}\.?\d{3}\.?\d{3}-?\d\b"),
    re.compile(r"\b(?:\d[ -]*?){13,19}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"\b[A-Za-z0-9_-]{24,}\.[A-Za-z0-9_-]{6,}\.[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\b(?:rua|avenida|av\.|travessa)\s+[^,]{3,80},\s*\d{1,6}\b", re.IGNORECASE),
    re.compile(r"\b(conta|agencia|agência|banco|pix)\b.{0,40}\b\d{4,}\b", re.IGNORECASE),
]


def wants_no_save(text: str) -> bool:
    return bool(NO_SAVE_PATTERN.search(text or ""))


def wants_forget(text: str) -> bool:
    return bool(FORGET_PATTERN.search(text or ""))


def asks_self_memory(text: str) -> bool:
    return bool(QUERY_SELF_PATTERN.search(text or ""))


def asks_channel_memory(text: str) -> bool:
    return bool(QUERY_CHANNEL_PATTERN.search(text or ""))


def is_sensitive_memory(text: str) -> bool:
    clean = text or ""
    return any(pattern.search(clean) for pattern in SENSITIVE_PATTERNS)


def redact_sensitive(text: str) -> str:
    clean = text or ""
    for pattern in SENSITIVE_PATTERNS:
        clean = pattern.sub("[dado sensivel]", clean)
    return clean
