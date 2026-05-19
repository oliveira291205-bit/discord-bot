from __future__ import annotations

import random
import re
from dataclasses import dataclass


BUG_TEMPLATES = [
    "Esse bug ai parece inimigo forte, mas da pra derrotar por partes.",
    "O codigo nao quebrou. Ele so escolheu o caos.",
    "Classico: funcionava ate alguem olhar.",
    "Vamos ver esse erro com calma.",
]

SUCCESS_TEMPLATES = [
    "Boa. Isso ai foi progresso real.",
    "Ai sim. XP adquirido.",
    "Treino concluido com sucesso.",
    "Agora sim, guerreiro.",
]

STUDY_TEMPLATES = [
    "Vamos por partes, sem invocar o demonio da algebra.",
    "Calma. Isso parece pior do que realmente e.",
    "Primeiro a gente entende, depois resolve.",
    "Treino de mente agora.",
]

GREETING_TEMPLATES = [
    "Opa, bora treinar?",
    "Fala. Pronto pra mais uma batalha?",
    "Cheguei. Qual e o desafio?",
]

THANKS_PATTERN = re.compile(r"^\s*(valeu|obrigad[ao]|vlw|thanks|tmj)\s*[!.]*\s*$", re.I)
GREETING_PATTERN = re.compile(r"^\s*(bom dia|boa tarde|boa noite|opa|oi|e ai|e aí|salve|fala)\s*[!.]*\s*$", re.I)
SUCCESS_PATTERN = re.compile(r"\b(deu certo|consegui|funcionou|resolvi|terminei|compilei|subiu)\b", re.I)
SHORT_LAUGH_PATTERN = re.compile(r"^\s*(k{2,}|kkk+|haha+|rs+)\s*$", re.I)
STUDY_PATTERN = re.compile(
    r"\b(calculo|cálculo|limite|derivada|integral|matematica|matemática|python|programa[cç][aã]o|algoritmo|git|banco de dados|sql|estrutura de dados)\b",
    re.I,
)
QUESTION_PATTERN = re.compile(r"\?|como faço|como faz|me ajuda|explica|por que|porque", re.I)


@dataclass(frozen=True)
class LocalReply:
    text: str
    xp_reason: str | None = None
    needs_ai: bool = False


class LocalReplyEngine:
    def __init__(self, *, enabled: bool = True, rng: random.Random | None = None) -> None:
        self.enabled = enabled
        self.rng = rng or random.Random()

    def generate(self, text: str, *, direct: bool) -> LocalReply | None:
        if not self.enabled:
            return None
        clean = " ".join((text or "").split())
        if not clean:
            return None

        if GREETING_PATTERN.fullmatch(clean):
            return LocalReply(self.rng.choice(GREETING_TEMPLATES))
        if THANKS_PATTERN.fullmatch(clean):
            return LocalReply("Tamo junto. Mais um treino vencido.")
        if SHORT_LAUGH_PATTERN.fullmatch(clean):
            return LocalReply("Hehe, essa foi boa.")
        if SUCCESS_PATTERN.search(clean) and len(clean) <= 120:
            return LocalReply(self.rng.choice(SUCCESS_TEMPLATES), xp_reason="success")
        if direct and STUDY_PATTERN.search(clean) and not QUESTION_PATTERN.search(clean) and len(clean) <= 120:
            return LocalReply(self.rng.choice(STUDY_TEMPLATES), xp_reason="study")
        return None


def is_study_or_programming(text: str) -> bool:
    return bool(STUDY_PATTERN.search(text or ""))


def needs_teacher_mode(text: str) -> bool:
    clean = text or ""
    return bool(STUDY_PATTERN.search(clean) and QUESTION_PATTERN.search(clean))
