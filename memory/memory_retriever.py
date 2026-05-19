from __future__ import annotations

from .memory_config import MemoryConfig
from .memory_store import SQLiteMemoryStore, build_scope_id
from .memory_types import Memory, MemoryContext


class MemoryRetriever:
    def __init__(self, store: SQLiteMemoryStore, config: MemoryConfig) -> None:
        self.store = store
        self.config = config

    def get_relevant_memories(
        self,
        *,
        guild_id: str | None,
        channel_id: str | None,
        user_id: str | None,
        current_message: str,
        limit: int | None = None,
    ) -> list[Memory]:
        context = MemoryContext(guild_id=guild_id, channel_id=channel_id, user_id=user_id)
        scopes = []
        if self.config.allow_global_memory:
            scopes.append(("global", "global"))
        if self.config.allow_guild_memory and guild_id:
            scopes.append(("guild", build_scope_id("guild", context)))
        if self.config.allow_channel_memory and channel_id:
            scopes.append(("channel", build_scope_id("channel", context)))
        if self.config.allow_user_memory and user_id:
            scopes.append(("user", build_scope_id("user", context)))
        if self.config.allow_user_channel_memory and user_id and channel_id:
            scopes.append(("user_channel", build_scope_id("user_channel", context)))

        return self.store.search(
            query=current_message,
            context=context,
            scopes=scopes,
            limit=limit or self.config.max_injected_memories,
            allow_sensitive=self.config.allow_sensitive_memory,
        )
