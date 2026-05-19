from __future__ import annotations

import random
import re
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import DefaultDict, Deque

from .memory_config import NaturalInteractionConfig
from .memory_service import MemoryService
from .memory_types import MemoryCandidate, MemoryContext, SCOPE_CHANNEL, SCOPE_USER


BUG_TEMPLATES = [
    "Esse erro ai tem cheiro de dependencia revoltada.",
    "O codigo nao quebrou, ele so escolheu o caos.",
    "Classico: funcionava ate alguem olhar.",
    "Isso ai parece gambiarra pedindo socorro.",
]

STUDY_TEMPLATES = [
    "Vamos por partes, sem invocar o demonio da algebra.",
    "Calma. Isso parece pior do que realmente e.",
    "Respira. A matematica so esta fazendo drama.",
    "Da para resolver se separar em pedacos.",
]

SUCCESS_TEMPLATES = [
    "Boa. Agora sim virou progresso.",
    "Ai sim. XP adquirido.",
    "Isso ai foi evolucao real.",
    "Finalmente o universo colaborou.",
]

MEME_TEMPLATES = [
    "Isso ai ta com aura estranha, mas tankei.",
    "Six seven de energia nesse momento, nao vou mentir.",
    "A lore desse canal esta ficando perigosa.",
    "Foi de base ou foi gain? Ainda estou calculando.",
]

GENERAL_TEMPLATES = [
    "Isso ai teve uma energia especifica demais pra eu ignorar.",
    "O canal acabou de ganhar mais um ponto de lore.",
    "Essa conversa esta estatisticamente suspeita.",
]

LORE_SUGGESTION = "Isso tem energia de momento historico do servidor. Quer que eu lembre disso como lore daqui?"
LORE_SAVED = "Fechado. Isso entrou na lore local desse canal."

BUG_PATTERN = re.compile(
    r"\b(bug|erro|traceback|exception|quebrou|crash|falhou|nao compila|não compila|deu ruim|dependencia|dependência)\b",
    re.IGNORECASE,
)
STUDY_PATTERN = re.compile(
    r"\b(prova|estudar|estudo|calculo|cálculo|matematica|matemática|faculdade|lista|exercicio|exercício|derivada|integral|limite|geometria)\b",
    re.IGNORECASE,
)
SUCCESS_PATTERN = re.compile(
    r"\b(consegui|terminei|finalmente|deu certo|passei|aprovado|resolvi|funcionou|compilei)\b",
    re.IGNORECASE,
)
MEME_PATTERN = re.compile(
    r"\b(meme|kkkk|kkk|intankavel|intankável|aura|six\s*seven|67|forth\s*teen|fourteen|loss|gain|foi de base|tankei)\b",
    re.IGNORECASE,
)
SERIOUS_PATTERN = re.compile(
    r"\b(serio|sério|desabafo|triste|ansiedade|depressao|depressão|morreu|luto|doente|hospital|urgente|assunto serio|assunto sério)\b",
    re.IGNORECASE,
)
HELP_PATTERN = re.compile(r"\b(me ajuda|ajuda|como faco|como faço|como faz|explica|duvida|dúvida)\b", re.IGNORECASE)
NO_JOKE_PATTERN = re.compile(
    r"\b(sem zoeira|faz graca nao|faz graça não|nao faz piada|não faz piada|fala serio|fala sério|modo serio|modo sério|para de zoar)\b",
    re.IGNORECASE,
)
ALLOW_JOKE_PATTERN = re.compile(r"\b(pode zoar|pode brincar|zoa ai|zoa aí)\b", re.IGNORECASE)
STOP_NICK_PATTERN = re.compile(
    r"\b(para de me chamar assim|nao gosto desse apelido|não gosto desse apelido|remove esse apelido)\b",
    re.IGNORECASE,
)
LORE_PATTERN = re.compile(r"\b(lembra do dia que|momento historico|momento histórico|lore do servidor|lore daqui)\b", re.IGNORECASE)
CONFIRM_PATTERN = re.compile(r"^\s*(sim|ss|lembra|guarda|salva|pode salvar|pode guardar|anota)\b", re.IGNORECASE)
QUESTION_PATTERN = re.compile(r"\?$|\b(porque|por que|como|qual|quais|quando|onde)\b", re.IGNORECASE)

SERIOUS_CHANNEL_WORDS = {
    "aviso",
    "avisos",
    "regra",
    "regras",
    "admin",
    "mod",
    "moderacao",
    "moderação",
    "suporte",
    "anuncio",
    "anuncios",
    "anúncio",
    "anúncios",
}


@dataclass(frozen=True)
class NaturalDecision:
    should_reply: bool
    reason: str = ""
    tone: str = "general"


class NaturalInteractionManager:
    def __init__(self, config: NaturalInteractionConfig, *, rng: random.Random | None = None) -> None:
        self.config = config
        self.rng = rng or random.Random()
        self.last_global_reply = 0.0
        self.last_channel_reply: dict[str, float] = {}
        self.global_reply_times: Deque[float] = deque()
        self.channel_reply_times: DefaultDict[str, Deque[float]] = defaultdict(deque)
        self.last_template_by_channel: dict[str, str] = {}
        self.phrase_counts: DefaultDict[str, dict[str, int]] = defaultdict(dict)
        self.pending_lore: dict[tuple[str | None, str | None], tuple[float, str]] = {}

    def handle_preference_signal(
        self,
        *,
        context: MemoryContext,
        text: str,
        memory_service: MemoryService,
    ) -> str | None:
        clean = " ".join((text or "").split())
        if not clean:
            return None

        lowered = clean.lower()
        if STOP_NICK_PATTERN.search(clean):
            memory_service.save_candidates(
                context=context,
                candidates=[
                    MemoryCandidate(
                        scope_type=SCOPE_USER,
                        memory_type="preference",
                        content="O usuario pediu para nao usar o apelido anterior.",
                        tags=["apelido", "limite"],
                        importance=9,
                        confidence=0.9,
                    )
                ],
            )
            return "Beleza. Parei com esse apelido."

        if NO_JOKE_PATTERN.search(clean):
            memory_service.save_candidates(
                context=context,
                candidates=[
                    MemoryCandidate(
                        scope_type=SCOPE_USER,
                        memory_type="preference",
                        content="O usuario prefere respostas sem zoeira quando pedir seriedade.",
                        tags=["tom", "serio", "sem-zoeira"],
                        importance=8,
                        confidence=0.86,
                    )
                ],
            )
            return "Fechado. Sem zoeira agora."

        if ALLOW_JOKE_PATTERN.search(clean):
            memory_service.save_candidates(
                context=context,
                candidates=[
                    MemoryCandidate(
                        scope_type=SCOPE_USER,
                        memory_type="preference",
                        content="O usuario permite humor leve e zoeira segura.",
                        tags=["tom", "zoeira"],
                        importance=9,
                        confidence=0.78,
                    )
                ],
            )
            return "Anotado. Zueira leve liberada."

        nickname_match = re.search(r"\b(?:me chama de|pode me chamar de)\s+([^,.!?;]{2,40})", clean, re.IGNORECASE)
        if nickname_match:
            nickname = clean_name(nickname_match.group(1))
            if not nickname:
                return None
            memory_service.save_candidates(
                context=context,
                candidates=[
                    MemoryCandidate(
                        scope_type=SCOPE_USER,
                        memory_type="preference",
                        content=f"O usuario prefere ser chamado de {nickname}.",
                        tags=["apelido"],
                        importance=10,
                        confidence=0.9,
                    )
                ],
            )
            return f"Fechado, {nickname}."

        return None

    def maybe_handle_lore_confirmation(
        self,
        *,
        context: MemoryContext,
        text: str,
        memory_service: MemoryService,
    ) -> str | None:
        key = (context.channel_id, context.user_id)
        pending = self.pending_lore.get(key)
        if not pending:
            return None
        created_at, lore_text = pending
        if time.monotonic() - created_at > 180:
            self.pending_lore.pop(key, None)
            return None
        if not CONFIRM_PATTERN.search(text or ""):
            return None

        memory_service.save_candidates(
            context=context,
            candidates=[
                MemoryCandidate(
                    scope_type=SCOPE_CHANNEL,
                    memory_type="joke",
                    content=f"Lore recorrente deste canal: {trim(lore_text, 180)}.",
                    tags=["lore", "piada-interna", context.channel_name or "canal"],
                    importance=7,
                    confidence=0.74,
                )
            ],
        )
        self.pending_lore.pop(key, None)
        self.record_reply(context.channel_id)
        return LORE_SAVED

    def should_interact_naturally(
        self,
        *,
        message: object,
        context: MemoryContext,
        was_mentioned: bool,
        triggered: bool,
        is_command: bool,
        memory_service: MemoryService | None = None,
    ) -> NaturalDecision:
        if not self.config.enabled or not self.config.allow_spontaneous_replies:
            return NaturalDecision(False, "disabled")
        if was_mentioned or triggered or is_command:
            return NaturalDecision(False, "direct-flow")

        text = getattr(message, "content", "") or ""
        clean = " ".join(text.split())
        if len(clean) < 4:
            return NaturalDecision(False, "too-short")

        tone = self.classify_tone(clean, context.channel_name)
        if self.config.do_not_interrupt_serious_conversations and tone == "serious":
            return NaturalDecision(False, "serious", tone)
        if memory_service is not None and self._user_blocks_jokes(context, memory_service):
            return NaturalDecision(False, "user-prefers-serious", tone)
        if not self._cooldown_allows(context.channel_id):
            return NaturalDecision(False, "cooldown", tone)

        reason = self._signal_reason(clean, tone)
        if not reason:
            self._observe_repeated_phrase(context, clean, memory_service=None)
            return NaturalDecision(False, "no-signal", tone)

        chance = self._chance_for_reason(reason)
        if self.rng.random() > chance:
            return NaturalDecision(False, "chance", tone)

        return NaturalDecision(True, reason, tone)

    def generate_natural_interaction(
        self,
        *,
        message: object,
        context: MemoryContext,
        memory_service: MemoryService,
    ) -> str | None:
        text = getattr(message, "content", "") or ""
        clean = " ".join(text.split())
        if not clean:
            return None

        if LORE_PATTERN.search(clean):
            self.pending_lore[(context.channel_id, context.user_id)] = (time.monotonic(), clean)
            return LORE_SUGGESTION

        tone = self.classify_tone(clean, context.channel_name)
        if tone == "serious":
            return None

        self._observe_repeated_phrase(context, clean, memory_service=memory_service)

        templates = templates_for_tone(tone)
        if not templates:
            return None
        chosen = self._choose_template(context.channel_id, tone, templates)
        nickname = self._nickname_for(context, memory_service)
        if nickname and self.rng.random() < 0.35:
            chosen = f"{nickname}, {lower_first(chosen)}"
        return chosen

    def record_reply(self, channel_id: str | None) -> None:
        now = time.monotonic()
        channel_key = channel_id or "dm"
        self.last_global_reply = now
        self.last_channel_reply[channel_key] = now
        self.global_reply_times.append(now)
        self.channel_reply_times[channel_key].append(now)
        self._drop_old_reply_times(now)

    def classify_tone(self, text: str, channel_name: str | None) -> str:
        channel = (channel_name or "").lower()
        if any(word in channel for word in SERIOUS_CHANNEL_WORDS) or SERIOUS_PATTERN.search(text):
            return "serious"
        if BUG_PATTERN.search(text) or any(word in channel for word in ("programacao", "programação", "codigo", "código", "python", "dev")):
            return "bug"
        if SUCCESS_PATTERN.search(text):
            return "success"
        if STUDY_PATTERN.search(text) or any(word in channel for word in ("estudo", "calculo", "cálculo", "math", "faculdade")):
            return "study"
        if MEME_PATTERN.search(text) or any(word in channel for word in ("meme", "geral", "zoeira")):
            return "meme"
        if HELP_PATTERN.search(text) or QUESTION_PATTERN.search(text):
            return "help"
        return "general"

    def _signal_reason(self, text: str, tone: str) -> str | None:
        if LORE_PATTERN.search(text):
            return "lore"
        if tone in {"bug", "success", "study", "meme"}:
            return tone
        if tone == "help":
            return None
        if MEME_PATTERN.search(text) or len(text) > 80:
            return "general"
        return None

    def _chance_for_reason(self, reason: str) -> float:
        base = max(0.0, min(1.0, self.config.spontaneous_reply_chance))
        multipliers = {
            "lore": 2.4,
            "success": 2.0,
            "bug": 1.6,
            "study": 1.4,
            "meme": 1.3,
            "general": 1.0,
        }
        return min(0.12, base * multipliers.get(reason, 1.0))

    def _cooldown_allows(self, channel_id: str | None) -> bool:
        now = time.monotonic()
        channel_key = channel_id or "dm"
        self._drop_old_reply_times(now)

        if now - self.last_global_reply < self.config.spontaneous_cooldown_seconds:
            return False
        if now - self.last_channel_reply.get(channel_key, 0.0) < self.config.spontaneous_cooldown_seconds:
            return False
        if len(self.global_reply_times) >= self.config.max_spontaneous_replies_per_hour:
            return False
        if len(self.channel_reply_times[channel_key]) >= self.config.max_spontaneous_replies_per_channel_per_hour:
            return False
        return True

    def _drop_old_reply_times(self, now: float) -> None:
        cutoff = now - 3600
        while self.global_reply_times and self.global_reply_times[0] < cutoff:
            self.global_reply_times.popleft()
        for times in self.channel_reply_times.values():
            while times and times[0] < cutoff:
                times.popleft()

    def _choose_template(self, channel_id: str | None, tone: str, templates: list[str]) -> str:
        key = f"{channel_id or 'dm'}:{tone}"
        last = self.last_template_by_channel.get(key)
        choices = [template for template in templates if template != last] or templates
        chosen = self.rng.choice(choices)
        self.last_template_by_channel[key] = chosen
        return chosen

    def _nickname_for(self, context: MemoryContext, memory_service: MemoryService) -> str | None:
        if not context.user_id:
            return None
        memories = memory_service.store.list_memories(user_id=context.user_id, scope_type=SCOPE_USER, limit=20)
        blocked = any("nao usar o apelido" in normalize(memory.content) for memory in memories)
        if blocked:
            return None
        for memory in memories:
            if "apelido" not in memory.tags:
                continue
            match = re.search(r"chamado de ([^,.!?;]{2,40})", memory.content, flags=re.IGNORECASE)
            if match:
                return clean_name(match.group(1))
        return None

    def _user_blocks_jokes(self, context: MemoryContext, memory_service: MemoryService) -> bool:
        if not context.user_id:
            return False
        memories = memory_service.store.list_memories(user_id=context.user_id, scope_type=SCOPE_USER, limit=20)
        for memory in memories:
            if "tom" not in memory.tags:
                continue
            content = normalize(memory.content)
            if "permite humor" in content or "zoeira segura" in content:
                return False
            if "sem zoeira" in content or "pedir seriedade" in content:
                return True
        return False

    def _observe_repeated_phrase(
        self,
        context: MemoryContext,
        text: str,
        *,
        memory_service: MemoryService | None,
    ) -> None:
        phrase = repeated_phrase_candidate(text)
        if not phrase:
            return
        channel_key = context.channel_id or "dm"
        counts = self.phrase_counts[channel_key]
        counts[phrase] = counts.get(phrase, 0) + 1
        if counts[phrase] != 3 or memory_service is None:
            return
        memory_service.save_candidates(
            context=context,
            candidates=[
                MemoryCandidate(
                    scope_type=SCOPE_CHANNEL,
                    memory_type="joke",
                    content=f"Piada interna recorrente neste canal: {phrase}.",
                    tags=["piada-interna", "lore", context.channel_name or "canal"],
                    importance=6,
                    confidence=0.68,
                )
            ],
        )


def templates_for_tone(tone: str) -> list[str]:
    if tone == "bug":
        return BUG_TEMPLATES
    if tone == "study":
        return STUDY_TEMPLATES
    if tone == "success":
        return SUCCESS_TEMPLATES
    if tone == "meme":
        return MEME_TEMPLATES
    if tone == "general":
        return GENERAL_TEMPLATES
    return []


def repeated_phrase_candidate(text: str) -> str | None:
    clean = normalize(text)
    if len(clean) < 12 or len(clean) > 80:
        return None
    if BUG_PATTERN.search(clean) or STUDY_PATTERN.search(clean) or SERIOUS_PATTERN.search(clean):
        return None
    words = clean.split()
    if len(words) < 3 or len(words) > 8:
        return None
    return " ".join(words)


def clean_name(value: str) -> str:
    return re.sub(r"[^0-9A-Za-zÀ-ÿ _.-]+", "", value).strip()[:32]


def lower_first(text: str) -> str:
    if not text:
        return text
    return text[0].lower() + text[1:]


def trim(text: str, limit: int) -> str:
    clean = " ".join((text or "").split())
    if len(clean) <= limit:
        return clean
    return clean[: limit - 3].rstrip() + "..."


def normalize(text: str) -> str:
    return re.sub(r"[^0-9a-zA-ZÀ-ÿ]+", " ", text.lower()).strip()
