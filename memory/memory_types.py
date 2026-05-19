from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


SCOPE_GLOBAL = "global"
SCOPE_GUILD = "guild"
SCOPE_CHANNEL = "channel"
SCOPE_USER = "user"
SCOPE_USER_CHANNEL = "user_channel"
SCOPE_SESSION = "session"

MEMORY_TYPES = {
    "fact",
    "preference",
    "project",
    "joke",
    "rule",
    "summary",
    "relationship",
    "warning",
    "context",
    "correction",
    "personality",
}


@dataclass(frozen=True)
class Memory:
    id: int
    guild_id: str | None
    channel_id: str | None
    user_id: str | None
    scope_type: str
    scope_id: str
    memory_type: str
    content: str
    tags: list[str] = field(default_factory=list)
    importance: int = 5
    confidence: float = 0.8
    created_at: str = ""
    updated_at: str = ""
    last_used_at: str | None = None
    expires_at: str | None = None
    source_message_id: str | None = None
    source_author_id: str | None = None
    is_sensitive: bool = False
    is_active: bool = True
    score: float = 0.0


@dataclass(frozen=True)
class MemoryCandidate:
    scope_type: str
    memory_type: str
    content: str
    tags: list[str] = field(default_factory=list)
    importance: int = 5
    confidence: float = 0.8
    expires_at: str | None = None


@dataclass(frozen=True)
class MemoryContext:
    guild_id: str | None
    channel_id: str | None
    user_id: str | None
    message_id: str | None = None
    author_name: str | None = None
    guild_name: str | None = None
    channel_name: str | None = None

    @property
    def now_iso(self) -> str:
        return datetime.now().astimezone().isoformat(timespec="seconds")
