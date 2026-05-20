from __future__ import annotations

import random
import re
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Deque, DefaultDict

from .config import GifConfig


LOCAL_GIFS = {
    "success": [
        "https://media.giphy.com/media/GRSnxyhJnPsaQy9YLn/giphy.gif",
        "https://media.giphy.com/media/977YesTjNfQC7vQiph/giphy.gif",
    ],
    "training": [
        "https://media.giphy.com/media/ul1omlrGG6kpO/giphy.gif",
        "https://media.giphy.com/media/19JSJ5ucu91R5D7a3w/giphy.gif",
    ],
    "thinking": [
        "https://media.giphy.com/media/13mfssn73An6De/giphy.gif",
        "https://media.giphy.com/media/11YMhfLfGoq5Gg/giphy.gif",
    ],
    "battle": [
        "https://media.giphy.com/media/dlsGMYrO26cOWC7ViW/giphy.gif",
        "https://media.giphy.com/media/HeDLTI576bBgA/giphy.gif",
    ],
    "funny": [
        "https://media.giphy.com/media/SPuyENBLQCFCU/giphy.gif",
        "https://media.giphy.com/media/WwBwZqiPIvoE1tFgRS/giphy.gif",
    ],
    "serious": [],
    "greeting": [
        "https://media.giphy.com/media/12KDixncjK6l7G/giphy.gif",
        "https://media.giphy.com/media/irBHYSZxbUifTxTgBL/giphy.gif",
    ],
}


@dataclass
class GifReactionManager:
    config: GifConfig
    channel_events: DefaultDict[int, Deque[float]] = field(default_factory=lambda: defaultdict(deque))
    user_events: DefaultDict[int, Deque[float]] = field(default_factory=lambda: defaultdict(deque))
    last_by_channel: dict[int, float] = field(default_factory=dict)
    last_url_by_channel: dict[int, str] = field(default_factory=dict)

    def should_send_gif(
        self,
        *,
        channel_id: int,
        user_id: int,
        text: str,
        force: bool = False,
        now: float | None = None,
    ) -> bool:
        if not self.config.enabled:
            return False
        if is_serious_context(text):
            return False
        now = time.monotonic() if now is None else now
        self._trim(self.channel_events[channel_id], now)
        self._trim(self.user_events[user_id], now)
        if now - self.last_by_channel.get(channel_id, 0) < self.config.cooldown_seconds:
            return False
        if len(self.channel_events[channel_id]) >= self.config.max_gifs_per_channel_per_hour:
            return False
        if len(self.user_events[user_id]) >= self.config.max_gifs_per_user_per_hour:
            return False
        if not force and random.random() > self.config.gif_reply_chance:
            return False
        return True

    def select_gif_for_context(self, text: str, *, channel_id: int = 0) -> str | None:
        category = classify_gif_context(text)
        urls = LOCAL_GIFS.get(category) or LOCAL_GIFS.get("funny") or []
        last_url = self.last_url_by_channel.get(channel_id)
        candidates = [url for url in urls if url != last_url] or urls
        return random.choice(candidates) if candidates else None

    def record(self, *, channel_id: int, user_id: int, url: str, now: float | None = None) -> None:
        now = time.monotonic() if now is None else now
        self.last_by_channel[channel_id] = now
        self.last_url_by_channel[channel_id] = url
        self.channel_events[channel_id].append(now)
        self.user_events[user_id].append(now)

    @staticmethod
    def _trim(items: Deque[float], now: float) -> None:
        while items and now - items[0] > 3600:
            items.popleft()


def classify_gif_context(text: str) -> str:
    lowered = (text or "").lower()
    if is_serious_context(lowered):
        return "serious"
    if re.search(r"\b(consegui|deu certo|vitoria|vitória|boa|resolvi|xp|parabens|parabéns)\b", lowered):
        return "success"
    if re.search(r"\b(treino|estudo|calculo|cálculo|python|programacao|programação|aprender)\b", lowered):
        return "training"
    if re.search(r"\b(erro|bug|traceback|syntaxerror|modulenotfound|luta|dificil|difícil)\b", lowered):
        return "battle"
    if re.search(r"\b(duvida|dúvida|confuso|nao entendi|não entendi|pensando)\b", lowered):
        return "thinking"
    if re.search(r"\b(oi|opa|fala|salve|bom dia|boa noite)\b", lowered):
        return "greeting"
    return "funny"


def is_serious_context(text: str) -> bool:
    return bool(
        re.search(
            r"\b(serio|sério|sem zoeira|modo serio|modo sério|triste|ansiedade|depress|morte|luto|doenca|doença)\b",
            text or "",
            re.IGNORECASE,
        )
    )
