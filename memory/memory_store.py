from __future__ import annotations

import json
import logging
import re
import sqlite3
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Iterable

from .memory_types import Memory, MemoryCandidate, MemoryContext

LOGGER = logging.getLogger("rei_suzukawa.memory")


class SQLiteMemoryStore:
    def __init__(self, sqlite_path: str | Path, *, use_fts5: bool = True, debug: bool = False) -> None:
        self.path = Path(sqlite_path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.debug = debug
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.fts_enabled = False
        self._create_schema(use_fts5=use_fts5)

    def close(self) -> None:
        self.conn.close()

    def _create_schema(self, *, use_fts5: bool) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id TEXT NULL,
                channel_id TEXT NULL,
                user_id TEXT NULL,
                scope_type TEXT NOT NULL,
                scope_id TEXT NOT NULL,
                memory_type TEXT NOT NULL,
                content TEXT NOT NULL,
                tags TEXT NULL,
                importance INTEGER DEFAULT 5,
                confidence REAL DEFAULT 0.8,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_used_at TEXT NULL,
                expires_at TEXT NULL,
                source_message_id TEXT NULL,
                source_author_id TEXT NULL,
                is_sensitive INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1
            );
            CREATE INDEX IF NOT EXISTS idx_memories_guild_id ON memories(guild_id);
            CREATE INDEX IF NOT EXISTS idx_memories_channel_id ON memories(channel_id);
            CREATE INDEX IF NOT EXISTS idx_memories_user_id ON memories(user_id);
            CREATE INDEX IF NOT EXISTS idx_memories_scope ON memories(scope_type, scope_id);
            CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(memory_type);
            CREATE INDEX IF NOT EXISTS idx_memories_importance ON memories(importance);
            CREATE INDEX IF NOT EXISTS idx_memories_updated ON memories(updated_at);
            CREATE INDEX IF NOT EXISTS idx_memories_active ON memories(is_active);
            """
        )
        if use_fts5:
            try:
                self.conn.execute(
                    "CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(content, tags)"
                )
                self.fts_enabled = True
            except sqlite3.DatabaseError as exc:
                self.fts_enabled = False
                LOGGER.warning("SQLite FTS5 indisponivel, usando LIKE: %s", exc)
        self.conn.commit()

    def upsert_memory(
        self,
        candidate: MemoryCandidate,
        context: MemoryContext,
        *,
        source_message_id: str | None = None,
        source_author_id: str | None = None,
    ) -> Memory | None:
        existing = self.find_similar(candidate, context)
        now = context.now_iso
        if existing:
            merged = merge_memory_content(existing.content, candidate.content)
            tags = sorted(set(existing.tags) | set(candidate.tags))
            importance = max(existing.importance, candidate.importance)
            confidence = max(existing.confidence, candidate.confidence)
            self.conn.execute(
                """
                UPDATE memories
                SET content=?, tags=?, importance=?, confidence=?, updated_at=?, expires_at=?, is_active=1
                WHERE id=?
                """,
                (merged, json.dumps(tags, ensure_ascii=False), importance, confidence, now, candidate.expires_at, existing.id),
            )
            self._sync_fts(existing.id, merged, tags)
            self.conn.commit()
            return self.get_by_id(existing.id)

        scope_id = build_scope_id(candidate.scope_type, context)
        row = {
            "guild_id": context.guild_id,
            "channel_id": context.channel_id,
            "user_id": context.user_id,
            "scope_type": candidate.scope_type,
            "scope_id": scope_id,
            "memory_type": candidate.memory_type,
            "content": candidate.content,
            "tags": json.dumps(candidate.tags, ensure_ascii=False),
            "importance": candidate.importance,
            "confidence": candidate.confidence,
            "created_at": now,
            "updated_at": now,
            "last_used_at": None,
            "expires_at": candidate.expires_at,
            "source_message_id": source_message_id,
            "source_author_id": source_author_id,
            "is_sensitive": 0,
            "is_active": 1,
        }
        cursor = self.conn.execute(
            """
            INSERT INTO memories (
                guild_id, channel_id, user_id, scope_type, scope_id, memory_type, content, tags,
                importance, confidence, created_at, updated_at, last_used_at, expires_at,
                source_message_id, source_author_id, is_sensitive, is_active
            ) VALUES (
                :guild_id, :channel_id, :user_id, :scope_type, :scope_id, :memory_type, :content, :tags,
                :importance, :confidence, :created_at, :updated_at, :last_used_at, :expires_at,
                :source_message_id, :source_author_id, :is_sensitive, :is_active
            )
            """,
            row,
        )
        memory_id = int(cursor.lastrowid)
        self._sync_fts(memory_id, candidate.content, candidate.tags)
        self.conn.commit()
        return self.get_by_id(memory_id)

    def insert_imported_memory(
        self,
        *,
        content: str,
        tags: list[str],
        scope_type: str = "global",
        memory_type: str = "summary",
        importance: int = 4,
    ) -> bool:
        context = MemoryContext(guild_id=None, channel_id=None, user_id=None)
        candidate = MemoryCandidate(
            scope_type=scope_type,
            memory_type=memory_type,
            content=content,
            tags=tags,
            importance=importance,
            confidence=0.6,
        )
        before = self.count_all()
        self.upsert_memory(candidate, context)
        return self.count_all() > before

    def get_by_id(self, memory_id: int) -> Memory | None:
        row = self.conn.execute("SELECT * FROM memories WHERE id=?", (memory_id,)).fetchone()
        return row_to_memory(row) if row else None

    def find_similar(self, candidate: MemoryCandidate, context: MemoryContext) -> Memory | None:
        scope_id = build_scope_id(candidate.scope_type, context)
        tokens = significant_tokens(candidate.content)
        if not tokens:
            return None
        rows = self.conn.execute(
            """
            SELECT * FROM memories
            WHERE is_active=1 AND scope_type=? AND scope_id=? AND memory_type=?
            ORDER BY updated_at DESC LIMIT 80
            """,
            (candidate.scope_type, scope_id, candidate.memory_type),
        ).fetchall()
        best: tuple[float, Memory] | None = None
        for row in rows:
            memory = row_to_memory(row)
            overlap = token_overlap(tokens, significant_tokens(memory.content))
            if overlap >= 0.55 and (best is None or overlap > best[0]):
                best = (overlap, memory)
        return best[1] if best else None

    def search(
        self,
        *,
        query: str,
        context: MemoryContext,
        scopes: list[tuple[str, str]],
        limit: int,
        allow_sensitive: bool = False,
    ) -> list[Memory]:
        now = context.now_iso
        params: list[object] = [now]
        scope_filters = []
        for scope_type, scope_id in scopes:
            scope_filters.append("(scope_type=? AND scope_id=?)")
            params.extend([scope_type, scope_id])
        if not scope_filters:
            return []

        base_where = (
            "is_active=1 AND (expires_at IS NULL OR expires_at > ?) "
            f"AND ({' OR '.join(scope_filters)})"
        )
        if not allow_sensitive:
            base_where += " AND is_sensitive=0"

        if self.fts_enabled and significant_tokens(query):
            fts_query = " OR ".join(escape_fts_token(token) for token in significant_tokens(query)[:8])
            rows = self.conn.execute(
                f"""
                SELECT m.*, bm25(memories_fts) AS fts_score
                FROM memories_fts
                JOIN memories m ON m.id = memories_fts.rowid
                WHERE memories_fts MATCH ? AND {base_where}
                ORDER BY m.importance DESC, m.updated_at DESC
                LIMIT ?
                """,
                [fts_query, *params, limit * 4],
            ).fetchall()
        else:
            like_terms = significant_tokens(query)[:8]
            like_clause = ""
            like_params: list[object] = []
            if like_terms:
                like_clause = " AND (" + " OR ".join("(content LIKE ? OR tags LIKE ?)" for _ in like_terms) + ")"
                for token in like_terms:
                    like_params.extend([f"%{token}%", f"%{token}%"])
            rows = self.conn.execute(
                f"""
                SELECT * FROM memories
                WHERE {base_where}{like_clause}
                ORDER BY importance DESC, updated_at DESC
                LIMIT ?
                """,
                [*params, *like_params, limit * 4],
            ).fetchall()

        memories = [row_to_memory(row) for row in rows]
        if not memories:
            rows = self.conn.execute(
                f"""
                SELECT * FROM memories
                WHERE {base_where}
                ORDER BY importance DESC, updated_at DESC
                LIMIT ?
                """,
                [*params, limit],
            ).fetchall()
            memories = [row_to_memory(row) for row in rows]

        ranked = sorted(memories, key=lambda item: score_memory(item, query), reverse=True)[:limit]
        self.mark_used([memory.id for memory in ranked])
        return ranked

    def list_memories(
        self,
        *,
        scope_type: str | None = None,
        scope_id: str | None = None,
        user_id: str | None = None,
        guild_id: str | None = None,
        channel_id: str | None = None,
        limit: int = 20,
    ) -> list[Memory]:
        clauses = ["is_active=1", "is_sensitive=0"]
        params: list[object] = []
        if scope_type:
            clauses.append("scope_type=?")
            params.append(scope_type)
        if scope_id:
            clauses.append("scope_id=?")
            params.append(scope_id)
        if user_id:
            clauses.append("user_id=?")
            params.append(user_id)
        if guild_id:
            clauses.append("guild_id=?")
            params.append(guild_id)
        if channel_id:
            clauses.append("channel_id=?")
            params.append(channel_id)
        rows = self.conn.execute(
            f"SELECT * FROM memories WHERE {' AND '.join(clauses)} ORDER BY importance DESC, updated_at DESC LIMIT ?",
            [*params, limit],
        ).fetchall()
        return [row_to_memory(row) for row in rows]

    def deactivate_scope(self, *, scope_type: str, scope_id: str) -> int:
        cursor = self.conn.execute(
            "UPDATE memories SET is_active=0, updated_at=? WHERE scope_type=? AND scope_id=? AND is_active=1",
            (datetime.now().astimezone().isoformat(timespec="seconds"), scope_type, scope_id),
        )
        self.conn.commit()
        return int(cursor.rowcount)

    def deactivate_user(self, user_id: str) -> int:
        cursor = self.conn.execute(
            "UPDATE memories SET is_active=0, updated_at=? WHERE user_id=? AND is_active=1",
            (datetime.now().astimezone().isoformat(timespec="seconds"), user_id),
        )
        self.conn.commit()
        return int(cursor.rowcount)

    def deactivate_channel(self, channel_id: str) -> int:
        cursor = self.conn.execute(
            "UPDATE memories SET is_active=0, updated_at=? WHERE channel_id=? AND is_active=1",
            (datetime.now().astimezone().isoformat(timespec="seconds"), channel_id),
        )
        self.conn.commit()
        return int(cursor.rowcount)

    def deactivate_guild(self, guild_id: str) -> int:
        cursor = self.conn.execute(
            "UPDATE memories SET is_active=0, updated_at=? WHERE guild_id=? AND is_active=1",
            (datetime.now().astimezone().isoformat(timespec="seconds"), guild_id),
        )
        self.conn.commit()
        return int(cursor.rowcount)

    def forget_related(self, *, context: MemoryContext, query: str, limit: int = 8) -> int:
        scopes = [
            ("user_channel", build_scope_id("user_channel", context)),
            ("user", build_scope_id("user", context)),
            ("channel", build_scope_id("channel", context)),
        ]
        memories = self.search(query=query, context=context, scopes=scopes, limit=limit, allow_sensitive=False)
        if not memories:
            return 0
        ids = [memory.id for memory in memories]
        placeholders = ",".join("?" for _ in ids)
        cursor = self.conn.execute(f"UPDATE memories SET is_active=0 WHERE id IN ({placeholders})", ids)
        self.conn.commit()
        return int(cursor.rowcount)

    def export_scope(self, *, scope_type: str, scope_id: str) -> list[dict[str, object]]:
        memories = self.list_memories(scope_type=scope_type, scope_id=scope_id, limit=1000)
        return [asdict(memory) for memory in memories]

    def counts_for_context(self, context: MemoryContext) -> dict[str, int]:
        scopes = {
            "global": ("global", "global"),
            "guild": ("guild", context.guild_id or ""),
            "channel": ("channel", context.channel_id or ""),
            "user": ("user", context.user_id or ""),
            "user_channel": ("user_channel", f"{context.user_id}:{context.channel_id}" if context.user_id and context.channel_id else ""),
        }
        result: dict[str, int] = {}
        for name, (scope_type, scope_id) in scopes.items():
            if not scope_id:
                result[name] = 0
                continue
            row = self.conn.execute(
                "SELECT COUNT(*) AS count FROM memories WHERE is_active=1 AND scope_type=? AND scope_id=?",
                (scope_type, scope_id),
            ).fetchone()
            result[name] = int(row["count"] if row else 0)
        return result

    def count_all(self) -> int:
        row = self.conn.execute("SELECT COUNT(*) AS count FROM memories WHERE is_active=1").fetchone()
        return int(row["count"] if row else 0)

    def mark_used(self, ids: Iterable[int]) -> None:
        ids = list(ids)
        if not ids:
            return
        placeholders = ",".join("?" for _ in ids)
        self.conn.execute(
            f"UPDATE memories SET last_used_at=? WHERE id IN ({placeholders})",
            [datetime.now().astimezone().isoformat(timespec="seconds"), *ids],
        )
        self.conn.commit()

    def _sync_fts(self, memory_id: int, content: str, tags: list[str]) -> None:
        if not self.fts_enabled:
            return
        self.conn.execute("DELETE FROM memories_fts WHERE rowid=?", (memory_id,))
        self.conn.execute(
            "INSERT INTO memories_fts(rowid, content, tags) VALUES (?, ?, ?)",
            (memory_id, content, " ".join(tags)),
        )


def build_scope_id(scope_type: str, context: MemoryContext) -> str:
    if scope_type == "global":
        return "global"
    if scope_type == "guild":
        return context.guild_id or "dm"
    if scope_type == "channel":
        return context.channel_id or "dm"
    if scope_type == "user":
        return context.user_id or "unknown"
    if scope_type == "user_channel":
        return f"{context.user_id or 'unknown'}:{context.channel_id or 'dm'}"
    if scope_type == "session":
        return f"{context.channel_id or 'dm'}:session"
    return "global"


def row_to_memory(row: sqlite3.Row) -> Memory:
    tags = []
    try:
        parsed = json.loads(row["tags"] or "[]")
        if isinstance(parsed, list):
            tags = [str(item) for item in parsed]
    except json.JSONDecodeError:
        tags = []
    return Memory(
        id=int(row["id"]),
        guild_id=row["guild_id"],
        channel_id=row["channel_id"],
        user_id=row["user_id"],
        scope_type=row["scope_type"],
        scope_id=row["scope_id"],
        memory_type=row["memory_type"],
        content=row["content"],
        tags=tags,
        importance=int(row["importance"] or 5),
        confidence=float(row["confidence"] or 0.8),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        last_used_at=row["last_used_at"],
        expires_at=row["expires_at"],
        source_message_id=row["source_message_id"],
        source_author_id=row["source_author_id"],
        is_sensitive=bool(row["is_sensitive"]),
        is_active=bool(row["is_active"]),
    )


def significant_tokens(text: str) -> list[str]:
    tokens = re.findall(r"[a-zA-Z0-9_]{3,}", normalize_text(text))
    stop = {"que", "com", "para", "uma", "por", "isso", "este", "esta", "voce", "você", "usuario", "canal"}
    return [token for token in tokens if token not in stop][:12]


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower())


def token_overlap(left: list[str], right: list[str]) -> float:
    if not left or not right:
        return 0.0
    a = set(left)
    b = set(right)
    return len(a & b) / max(1, len(a | b))


def score_memory(memory: Memory, query: str) -> float:
    query_tokens = significant_tokens(query)
    overlap = token_overlap(query_tokens, significant_tokens(memory.content + " " + " ".join(memory.tags)))
    scope_bonus = {
        "user_channel": 4.0,
        "channel": 3.2,
        "user": 3.0,
        "guild": 2.0,
        "global": 1.2,
        "session": 1.0,
    }.get(memory.scope_type, 1.0)
    return overlap * 12 + memory.importance + memory.confidence + scope_bonus


def merge_memory_content(old: str, new: str) -> str:
    if normalize_text(new) in normalize_text(old):
        return old
    if len(old) + len(new) < 420:
        return f"{old.rstrip('.')} ; {new}"
    return new if len(new) > len(old) else old


def escape_fts_token(token: str) -> str:
    return '"' + token.replace('"', '""') + '"'
