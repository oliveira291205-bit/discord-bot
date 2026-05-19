from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


MEMORY_CONFIG = {
    "enabled": True,
    "storage": "sqlite",
    "sqlite_path": "data/memory.sqlite3",
    "use_obsidian": False,
    "use_sqlite_fts5": True,
    "use_embeddings": False,
    "use_ai_for_memory_extraction": False,
    "use_ai_for_memory_summary": False,
    "max_injected_memories": 10,
    "max_memory_chars": 250,
    "recent_context_limit": 10,
    "allow_user_memory": True,
    "allow_channel_memory": True,
    "allow_guild_memory": True,
    "allow_global_memory": True,
    "allow_user_channel_memory": True,
    "allow_sensitive_memory": False,
    "max_memories_per_user": 200,
    "max_memories_per_channel": 500,
    "max_memories_per_guild": 1000,
    "summarize_after_messages": 50,
    "debug": False,
}


DEEPSEEK_PROMPT_CONFIG = {
    "max_total_prompt_chars": 24000,
    "max_total_estimated_tokens": 6000,
    "max_system_prompt_chars": 4000,
    "max_memory_context_chars": 5000,
    "max_recent_context_chars": 4000,
    "max_user_message_chars": 3000,
    "max_injected_memories": 10,
    "max_chars_per_memory": 250,
    "hard_block_if_above_chars": 32000,
    "hard_block_if_above_estimated_tokens": 8000,
    "debug_prompt_size": True,
}


NATURAL_INTERACTION_CONFIG = {
    "enabled": True,
    "allow_spontaneous_replies": True,
    "spontaneous_reply_chance": 0.03,
    "spontaneous_cooldown_seconds": 300,
    "max_spontaneous_replies_per_hour": 5,
    "max_spontaneous_replies_per_channel_per_hour": 3,
    "do_not_interrupt_serious_conversations": True,
    "use_ai_for_spontaneous_replies": False,
}


@dataclass(frozen=True)
class MemoryConfig:
    enabled: bool = True
    sqlite_path: Path = Path("data/memory.sqlite3")
    use_obsidian: bool = False
    use_sqlite_fts5: bool = True
    use_embeddings: bool = False
    use_ai_for_memory_extraction: bool = False
    use_ai_for_memory_summary: bool = False
    max_injected_memories: int = 10
    max_memory_chars: int = 250
    recent_context_limit: int = 10
    allow_user_memory: bool = True
    allow_channel_memory: bool = True
    allow_guild_memory: bool = True
    allow_global_memory: bool = True
    allow_user_channel_memory: bool = True
    allow_sensitive_memory: bool = False
    max_memories_per_user: int = 200
    max_memories_per_channel: int = 500
    max_memories_per_guild: int = 1000
    summarize_after_messages: int = 50
    debug: bool = False

    @classmethod
    def from_env(cls) -> "MemoryConfig":
        return cls(
            enabled=_as_bool("REI_MEMORY_ENABLED", MEMORY_CONFIG["enabled"]),
            sqlite_path=Path(os.getenv("REI_MEMORY_SQLITE_PATH", str(MEMORY_CONFIG["sqlite_path"]))).expanduser(),
            use_obsidian=_as_bool("REI_MEMORY_USE_OBSIDIAN", False),
            use_sqlite_fts5=_as_bool("REI_MEMORY_USE_SQLITE_FTS5", True),
            use_embeddings=_as_bool("REI_MEMORY_USE_EMBEDDINGS", False),
            use_ai_for_memory_extraction=_as_bool("REI_MEMORY_USE_AI_EXTRACTION", False),
            use_ai_for_memory_summary=_as_bool("REI_MEMORY_USE_AI_SUMMARY", False),
            max_injected_memories=_as_int("REI_MEMORY_MAX_INJECTED", 10),
            max_memory_chars=_as_int("REI_MEMORY_MAX_CHARS", 250),
            recent_context_limit=_as_int("REI_MEMORY_RECENT_CONTEXT_LIMIT", 10),
            allow_user_memory=_as_bool("REI_MEMORY_ALLOW_USER", True),
            allow_channel_memory=_as_bool("REI_MEMORY_ALLOW_CHANNEL", True),
            allow_guild_memory=_as_bool("REI_MEMORY_ALLOW_GUILD", True),
            allow_global_memory=_as_bool("REI_MEMORY_ALLOW_GLOBAL", True),
            allow_user_channel_memory=_as_bool("REI_MEMORY_ALLOW_USER_CHANNEL", True),
            allow_sensitive_memory=_as_bool("REI_MEMORY_ALLOW_SENSITIVE", False),
            max_memories_per_user=_as_int("REI_MEMORY_MAX_PER_USER", 200),
            max_memories_per_channel=_as_int("REI_MEMORY_MAX_PER_CHANNEL", 500),
            max_memories_per_guild=_as_int("REI_MEMORY_MAX_PER_GUILD", 1000),
            summarize_after_messages=_as_int("REI_MEMORY_SUMMARIZE_AFTER", 50),
            debug=_as_bool("REI_MEMORY_DEBUG", False),
        )


@dataclass(frozen=True)
class NaturalInteractionConfig:
    enabled: bool = True
    allow_spontaneous_replies: bool = True
    spontaneous_reply_chance: float = 0.03
    spontaneous_cooldown_seconds: int = 300
    max_spontaneous_replies_per_hour: int = 5
    max_spontaneous_replies_per_channel_per_hour: int = 3
    do_not_interrupt_serious_conversations: bool = True
    use_ai_for_spontaneous_replies: bool = False

    @classmethod
    def from_env(cls) -> "NaturalInteractionConfig":
        return cls(
            enabled=_as_bool("REI_NATURAL_INTERACTIONS_ENABLED", NATURAL_INTERACTION_CONFIG["enabled"]),
            allow_spontaneous_replies=_as_bool(
                "REI_NATURAL_ALLOW_SPONTANEOUS",
                NATURAL_INTERACTION_CONFIG["allow_spontaneous_replies"],
            ),
            spontaneous_reply_chance=_as_float(
                "REI_NATURAL_REPLY_CHANCE",
                NATURAL_INTERACTION_CONFIG["spontaneous_reply_chance"],
            ),
            spontaneous_cooldown_seconds=_as_int(
                "REI_NATURAL_COOLDOWN_SECONDS",
                NATURAL_INTERACTION_CONFIG["spontaneous_cooldown_seconds"],
            ),
            max_spontaneous_replies_per_hour=_as_int(
                "REI_NATURAL_MAX_PER_HOUR",
                NATURAL_INTERACTION_CONFIG["max_spontaneous_replies_per_hour"],
            ),
            max_spontaneous_replies_per_channel_per_hour=_as_int(
                "REI_NATURAL_MAX_PER_CHANNEL_HOUR",
                NATURAL_INTERACTION_CONFIG["max_spontaneous_replies_per_channel_per_hour"],
            ),
            do_not_interrupt_serious_conversations=_as_bool(
                "REI_NATURAL_AVOID_SERIOUS",
                NATURAL_INTERACTION_CONFIG["do_not_interrupt_serious_conversations"],
            ),
            use_ai_for_spontaneous_replies=_as_bool(
                "REI_NATURAL_USE_AI",
                NATURAL_INTERACTION_CONFIG["use_ai_for_spontaneous_replies"],
            ),
        )


def _as_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "sim", "yes", "on"}


def _as_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _as_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default
