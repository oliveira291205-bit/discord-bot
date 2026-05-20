from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Mapping

from .config import WakeWordConfig


@dataclass(frozen=True)
class ActivationDecision:
    should_respond: bool
    reason: str = ""
    cleaned_content: str = ""


def clean_wake_words(text: str, names: tuple[str, ...]) -> str:
    clean = text or ""
    if names:
        pattern = re.compile(rf"(?<!\w)(?:{'|'.join(re.escape(name) for name in names)})(?!\w)", re.IGNORECASE)
        clean = pattern.sub(" ", clean)
    return re.sub(r"\s+", " ", clean.replace(",", " ")).strip()


def contains_wake_word(text: str, names: tuple[str, ...]) -> bool:
    if not names:
        return False
    pattern = re.compile(rf"(?<!\w)(?:{'|'.join(re.escape(name) for name in names)})(?!\w)", re.IGNORECASE)
    return bool(pattern.search(text or ""))


def should_respond_to_message(
    message: object,
    *,
    bot_user: object | None,
    config: WakeWordConfig,
    active_conversations: Mapping[tuple[int, int], float] | None = None,
    now: float | None = None,
) -> ActivationDecision:
    content = getattr(message, "content", "") or ""
    bot_id = getattr(bot_user, "id", None)
    channel_id = int(getattr(getattr(message, "channel", None), "id", 0) or 0)
    author_id = int(getattr(getattr(message, "author", None), "id", 0) or 0)
    now = time.monotonic() if now is None else now

    if config.allow_direct_mention and bot_user is not None:
        mentions = getattr(message, "mentions", []) or []
        if any(getattr(user, "id", None) == bot_id for user in mentions):
            return ActivationDecision(True, "mention", clean_wake_words(content, config.names))
        if bot_id is not None and re.search(rf"<@!?{re.escape(str(bot_id))}>", content):
            return ActivationDecision(True, "mention", clean_wake_words(content, config.names))

    if config.enabled and contains_wake_word(content, config.names):
        return ActivationDecision(True, "wake_word", clean_wake_words(content, config.names))

    if config.allow_reply_to_bot and _is_reply_to_bot(message, bot_id):
        return ActivationDecision(True, "reply_to_bot", clean_wake_words(content, config.names))

    if config.allow_active_conversation_window and active_conversations:
        last_seen = active_conversations.get((channel_id, author_id))
        if last_seen is not None and now - last_seen <= config.active_conversation_seconds:
            return ActivationDecision(True, "active_conversation", clean_wake_words(content, config.names))

    return ActivationDecision(False, "quiet", clean_wake_words(content, config.names))


def _is_reply_to_bot(message: object, bot_id: int | None) -> bool:
    if bot_id is None:
        return False
    reference = getattr(message, "reference", None)
    if reference is None:
        return False
    resolved = getattr(reference, "resolved", None)
    if resolved is not None:
        author = getattr(resolved, "author", None)
        return getattr(author, "id", None) == bot_id
    return getattr(reference, "message_id", None) is not None and getattr(reference, "cached_message_author_id", None) == bot_id
