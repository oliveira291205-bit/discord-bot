from __future__ import annotations

import re
import sqlite3
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


MENTION_RE = re.compile(r"<@!?(\d+)>")
BLOCKED_MENTION_TEXT = re.compile(r"@(everyone|here)|todo mundo|todos\b|geral\b", re.IGNORECASE)
MENTION_REQUEST_RE = re.compile(
    r"\b(?:marca|marque|chama|chame|avisa|avise|menciona|mencione|tagueia|tagueie|da um salve|dá um salve)\b\s+(?:o|a|ao|aos|usuario|usuário|user|@)?\s*([^,.!?]+)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class MemberRecord:
    guild_id: str
    user_id: str
    username: str | None = None
    global_name: str | None = None
    display_name: str | None = None
    nick: str | None = None
    discriminator: str | None = None
    mention: str | None = None
    bot: bool = False
    joined_at: str | None = None
    updated_at: str = ""
    is_active: bool = True

    @property
    def label(self) -> str:
        return self.display_name or self.nick or self.global_name or self.username or self.user_id


@dataclass(frozen=True)
class MemberResolution:
    status: str
    member: MemberRecord | None = None
    matches: tuple[MemberRecord, ...] = ()
    reason: str = ""


class MemberDirectory:
    def __init__(self, sqlite_path: str | Path) -> None:
        self.path = Path(sqlite_path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self._create_schema()

    def close(self) -> None:
        self.conn.close()

    def _create_schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS guild_members (
                guild_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                username TEXT,
                global_name TEXT,
                display_name TEXT,
                nick TEXT,
                discriminator TEXT,
                mention TEXT,
                bot INTEGER DEFAULT 0,
                joined_at TEXT NULL,
                updated_at TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                PRIMARY KEY (guild_id, user_id)
            );
            CREATE INDEX IF NOT EXISTS idx_guild_members_guild_id ON guild_members(guild_id);
            CREATE INDEX IF NOT EXISTS idx_guild_members_user_id ON guild_members(user_id);
            CREATE INDEX IF NOT EXISTS idx_guild_members_username ON guild_members(username);
            CREATE INDEX IF NOT EXISTS idx_guild_members_global_name ON guild_members(global_name);
            CREATE INDEX IF NOT EXISTS idx_guild_members_display_name ON guild_members(display_name);
            CREATE INDEX IF NOT EXISTS idx_guild_members_nick ON guild_members(nick);
            CREATE INDEX IF NOT EXISTS idx_guild_members_active ON guild_members(is_active);

            CREATE TABLE IF NOT EXISTS member_social_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                channel_id TEXT NULL,
                memory_type TEXT NOT NULL,
                content TEXT NOT NULL,
                tags TEXT NULL,
                importance INTEGER DEFAULT 5,
                confidence REAL DEFAULT 0.8,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                is_active INTEGER DEFAULT 1
            );
            CREATE INDEX IF NOT EXISTS idx_member_social_guild_user ON member_social_memory(guild_id, user_id);
            CREATE INDEX IF NOT EXISTS idx_member_social_channel ON member_social_memory(channel_id);
            """
        )
        self.conn.commit()

    async def sync_all_guilds(self, bot: object) -> dict[str, int]:
        result: dict[str, int] = {}
        for guild in getattr(bot, "guilds", []) or []:
            result[str(guild.id)] = await self.sync_guild_members(guild)
        return result

    async def sync_guild_members(self, guild: object) -> int:
        count = 0
        try:
            if hasattr(guild, "chunk"):
                await guild.chunk(cache=True)
        except Exception:
            pass
        for member in getattr(guild, "members", []) or []:
            self.upsert_member(str(getattr(guild, "id", "")), member)
            count += 1
        return count

    def upsert_member(self, guild_id: str, member: object) -> None:
        now = datetime.now().astimezone().isoformat(timespec="seconds")
        user_id = str(getattr(member, "id", ""))
        if not guild_id or not user_id:
            return
        joined_at = getattr(getattr(member, "joined_at", None), "isoformat", lambda **_: None)(timespec="seconds")
        self.conn.execute(
            """
            INSERT INTO guild_members (
                guild_id, user_id, username, global_name, display_name, nick, discriminator,
                mention, bot, joined_at, updated_at, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            ON CONFLICT(guild_id, user_id) DO UPDATE SET
                username=excluded.username,
                global_name=excluded.global_name,
                display_name=excluded.display_name,
                nick=excluded.nick,
                discriminator=excluded.discriminator,
                mention=excluded.mention,
                bot=excluded.bot,
                joined_at=excluded.joined_at,
                updated_at=excluded.updated_at,
                is_active=1
            """,
            (
                guild_id,
                user_id,
                getattr(member, "name", None),
                getattr(member, "global_name", None),
                getattr(member, "display_name", None),
                getattr(member, "nick", None),
                getattr(member, "discriminator", None),
                getattr(member, "mention", f"<@{user_id}>"),
                1 if getattr(member, "bot", False) else 0,
                joined_at,
                now,
            ),
        )
        self.conn.commit()

    def mark_member_inactive(self, guild_id: str, user_id: str) -> None:
        self.conn.execute(
            "UPDATE guild_members SET is_active=0, updated_at=? WHERE guild_id=? AND user_id=?",
            (datetime.now().astimezone().isoformat(timespec="seconds"), guild_id, user_id),
        )
        self.conn.commit()

    def count_members(self, guild_id: str) -> int:
        row = self.conn.execute(
            "SELECT COUNT(*) AS count FROM guild_members WHERE guild_id=? AND is_active=1",
            (guild_id,),
        ).fetchone()
        return int(row["count"] if row else 0)

    def last_sync(self, guild_id: str) -> str | None:
        row = self.conn.execute(
            "SELECT MAX(updated_at) AS updated_at FROM guild_members WHERE guild_id=?",
            (guild_id,),
        ).fetchone()
        return str(row["updated_at"]) if row and row["updated_at"] else None

    def resolve_member(self, guild_id: str, query: str) -> MemberResolution:
        clean_query = clean_member_query(query)
        if not clean_query:
            return MemberResolution("not_found", reason="nome vazio")
        if BLOCKED_MENTION_TEXT.search(query or ""):
            return MemberResolution("blocked", reason="mencao ampla bloqueada")
        mention = MENTION_RE.search(query or "")
        if mention:
            record = self.get_member(guild_id, mention.group(1))
            return MemberResolution("found", member=record) if record else MemberResolution("not_found")
        if clean_query.isdigit():
            record = self.get_member(guild_id, clean_query)
            return MemberResolution("found", member=record) if record else MemberResolution("not_found")

        records = self.list_guild_members(guild_id)
        scored: list[tuple[float, MemberRecord]] = []
        for record in records:
            score = member_score(record, clean_query)
            if score >= 0.62:
                scored.append((score, record))
        scored.sort(key=lambda item: item[0], reverse=True)
        if not scored:
            return MemberResolution("not_found")
        best_score = scored[0][0]
        best = [record for score, record in scored if best_score - score < 0.08][:5]
        if len(best) == 1 or best_score >= 0.96:
            return MemberResolution("found", member=scored[0][1])
        return MemberResolution("ambiguous", matches=tuple(best))

    def get_member(self, guild_id: str, user_id: str) -> MemberRecord | None:
        row = self.conn.execute(
            "SELECT * FROM guild_members WHERE guild_id=? AND user_id=? AND is_active=1",
            (guild_id, user_id),
        ).fetchone()
        return row_to_member(row) if row else None

    def list_guild_members(self, guild_id: str, limit: int = 5000) -> list[MemberRecord]:
        rows = self.conn.execute(
            "SELECT * FROM guild_members WHERE guild_id=? AND is_active=1 LIMIT ?",
            (guild_id, limit),
        ).fetchall()
        return [row_to_member(row) for row in rows]


def extract_member_request(text: str) -> tuple[str, str] | None:
    if BLOCKED_MENTION_TEXT.search(text or ""):
        return ("", "blocked")
    match = MENTION_REQUEST_RE.search(text or "")
    if not match:
        return None
    target = clean_member_query(match.group(1))
    tail = (text or "")[match.end() :].strip(" ,.-")
    return target, tail


def clean_member_query(text: str) -> str:
    clean = normalize_name(text)
    clean = re.sub(r"\b(pelo id|por id|aqui|ai|aí|pra|para|vir|olhar|grupo|chat)\b", " ", clean)
    return re.sub(r"\s+", " ", clean.replace("@", " ")).strip()


def normalize_name(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text or "")
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    normalized = re.sub(r"[^a-zA-Z0-9_ @<>!-]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip().lower()


def member_score(record: MemberRecord, query: str) -> float:
    candidates = [
        record.user_id,
        record.username or "",
        record.global_name or "",
        record.display_name or "",
        record.nick or "",
    ]
    scores = []
    for value in candidates:
        clean = normalize_name(value)
        if not clean:
            continue
        if clean == query:
            scores.append(1.0)
        elif clean.startswith(query):
            scores.append(0.9)
        elif query in clean:
            scores.append(0.78)
        else:
            query_parts = set(query.split())
            value_parts = set(clean.split())
            if query_parts and query_parts <= value_parts:
                scores.append(0.84)
            elif query_parts & value_parts:
                scores.append(0.64)
    return max(scores or [0.0])


def row_to_member(row: sqlite3.Row) -> MemberRecord:
    return MemberRecord(
        guild_id=str(row["guild_id"]),
        user_id=str(row["user_id"]),
        username=row["username"],
        global_name=row["global_name"],
        display_name=row["display_name"],
        nick=row["nick"],
        discriminator=row["discriminator"],
        mention=row["mention"],
        bot=bool(row["bot"]),
        joined_at=row["joined_at"],
        updated_at=row["updated_at"],
        is_active=bool(row["is_active"]),
    )
