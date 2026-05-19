from __future__ import annotations

import re
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .config import XPConfig


TITLE_LEVELS = [
    (20, "Super Saiyajin Dev"),
    (15, "Guerreiro do Codigo"),
    (10, "Mestre do Termux"),
    (8, "Cacador de Bugs"),
    (5, "Dev em Treinamento"),
    (3, "Aluno do Mestre Kame"),
    (1, "Saiyajin Iniciante"),
]

ACHIEVEMENTS = {
    "first_bug": "Primeiro Bug Derrotado",
    "termux_survivor": "Sobrevivente do Termux",
    "dev_saiyan": "Dev Saiyajin",
    "traceback_hunter": "Cacador de Traceback",
    "git_pull_supreme": "Git Pull Supremo",
    "persistent_student": "Estudante Persistente",
    "calculus_training": "Treino de Calculo",
    "android_online": "Bot Online no Android",
}

REASON_XP = {
    "study": 5,
    "programming_help": 10,
    "error_solved": 15,
    "success": 20,
    "calculus": 25,
    "termux": 30,
    "git": 30,
}


@dataclass(frozen=True)
class XPEvent:
    xp_added: int
    level: int
    title: str
    achievements: list[str]
    message: str | None = None


class XPService:
    def __init__(self, sqlite_path: str | Path, config: XPConfig) -> None:
        self.path = Path(sqlite_path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.config = config
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.last_award_by_user: dict[tuple[str | None, str], float] = {}
        self.awards_by_hour: dict[tuple[str | None, str], list[tuple[float, int]]] = {}
        self._create_schema()

    def close(self) -> None:
        self.conn.close()

    def _create_schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS user_xp (
                user_id TEXT PRIMARY KEY,
                guild_id TEXT,
                xp INTEGER DEFAULT 0,
                level INTEGER DEFAULT 1,
                title TEXT,
                updated_at TEXT
            );
            CREATE TABLE IF NOT EXISTS user_achievements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                guild_id TEXT,
                achievement_key TEXT,
                achievement_name TEXT,
                unlocked_at TEXT,
                UNIQUE(user_id, guild_id, achievement_key)
            );
            CREATE INDEX IF NOT EXISTS idx_user_xp_guild ON user_xp(guild_id);
            CREATE INDEX IF NOT EXISTS idx_user_achievements_user ON user_achievements(user_id, guild_id);
            """
        )
        self.conn.commit()

    def classify_reason(self, text: str) -> str | None:
        lowered = (text or "").lower()
        if re.search(r"\b(termux|pkg install|dpkg|android|tesseract)\b", lowered):
            return "termux"
        if re.search(r"\b(git pull|git clone|git status|github)\b", lowered):
            return "git"
        if re.search(r"\b(traceback|syntaxerror|modulenotfounderror|importerror|bug|erro)\b", lowered):
            return "programming_help"
        if re.search(r"\b(calculo|cálculo|limite|derivada|integral|geometria)\b", lowered):
            return "calculus"
        if re.search(r"\b(python|programa[cç][aã]o|algoritmo|sql|banco de dados|estrutura de dados)\b", lowered):
            return "programming_help"
        if re.search(r"\b(estudo|prova|exercicio|exercício|faculdade)\b", lowered):
            return "study"
        if re.search(r"\b(deu certo|consegui|funcionou|terminei|resolvi)\b", lowered):
            return "success"
        return None

    def award(self, *, user_id: str | None, guild_id: str | None, reason: str | None) -> XPEvent | None:
        if not self.config.enabled or not user_id or not reason:
            return None
        amount = REASON_XP.get(reason)
        if not amount or not self._cooldown_allows(user_id, guild_id, amount):
            return None

        row = self.conn.execute("SELECT * FROM user_xp WHERE user_id=?", (user_id,)).fetchone()
        old_level = int(row["level"]) if row else 1
        old_xp = int(row["xp"]) if row else 0
        new_xp = old_xp + amount
        new_level = xp_to_level(new_xp)
        title = title_for_level(new_level)
        now = datetime.now().astimezone().isoformat(timespec="seconds")

        self.conn.execute(
            """
            INSERT INTO user_xp(user_id, guild_id, xp, level, title, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                guild_id=excluded.guild_id,
                xp=excluded.xp,
                level=excluded.level,
                title=excluded.title,
                updated_at=excluded.updated_at
            """,
            (user_id, guild_id, new_xp, new_level, title, now),
        )

        achievements = self._unlock_achievements(user_id, guild_id, reason, new_level, now)
        self.conn.commit()

        message = None
        if achievements:
            message = f"Conquista desbloqueada: {achievements[0]}. Isso conta como treino pesado."
        elif new_level > old_level:
            message = f"Subiu para nivel {new_level}: {title}. Treino dando resultado."
        return XPEvent(amount, new_level, title, achievements, message)

    def profile(self, user_id: str | None) -> str:
        if not user_id:
            return "Nao identifiquei o guerreiro."
        row = self.conn.execute("SELECT * FROM user_xp WHERE user_id=?", (user_id,)).fetchone()
        if not row:
            return "Ainda sem XP. Bora treinar um pouco."
        achievements = self.conn.execute(
            "SELECT achievement_name FROM user_achievements WHERE user_id=? ORDER BY unlocked_at DESC LIMIT 5",
            (user_id,),
        ).fetchall()
        names = ", ".join(item["achievement_name"] for item in achievements) or "nenhuma ainda"
        return f"Nivel {row['level']} - {row['title']} | XP: {row['xp']} | Conquistas: {names}"

    def _cooldown_allows(self, user_id: str, guild_id: str | None, amount: int) -> bool:
        now = time.monotonic()
        key = (guild_id, user_id)
        last = self.last_award_by_user.get(key, 0)
        if now - last < self.config.cooldown_seconds:
            return False
        hour_cutoff = now - 3600
        events = [(ts, xp) for ts, xp in self.awards_by_hour.get(key, []) if ts >= hour_cutoff]
        if sum(xp for _, xp in events) + amount > self.config.max_xp_per_user_per_hour:
            self.awards_by_hour[key] = events
            return False
        events.append((now, amount))
        self.awards_by_hour[key] = events
        self.last_award_by_user[key] = now
        return True

    def _unlock_achievements(
        self,
        user_id: str,
        guild_id: str | None,
        reason: str,
        level: int,
        now: str,
    ) -> list[str]:
        keys: list[str] = []
        if reason in {"programming_help", "error_solved"}:
            keys.extend(["first_bug", "dev_saiyan"])
        if reason == "termux":
            keys.extend(["termux_survivor", "android_online"])
        if reason == "git":
            keys.append("git_pull_supreme")
        if reason == "calculus":
            keys.append("calculus_training")
        if reason == "study":
            keys.append("persistent_student")
        if level >= 8:
            keys.append("traceback_hunter")

        unlocked: list[str] = []
        for key in keys:
            name = ACHIEVEMENTS[key]
            cursor = self.conn.execute(
                """
                INSERT OR IGNORE INTO user_achievements(user_id, guild_id, achievement_key, achievement_name, unlocked_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, guild_id, key, name, now),
            )
            if cursor.rowcount:
                unlocked.append(name)
        return unlocked


def xp_to_level(xp: int) -> int:
    return max(1, int((max(0, xp) / 100) ** 0.5) + 1)


def title_for_level(level: int) -> str:
    for minimum, title in TITLE_LEVELS:
        if level >= minimum:
            return title
    return "Saiyajin Iniciante"
