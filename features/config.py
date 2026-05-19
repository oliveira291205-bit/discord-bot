from __future__ import annotations

import os
from dataclasses import dataclass


FUN_CONFIG = {
    "enabled": True,
    "use_ai_for_fun_replies": False,
    "spontaneous_reply_chance": 0.03,
    "spontaneous_cooldown_seconds": 300,
    "max_fun_replies_per_channel_per_hour": 5,
    "safe_roasts_only": True,
}

XP_CONFIG = {
    "enabled": True,
    "cooldown_seconds": 180,
    "max_xp_per_user_per_hour": 100,
}

LOCAL_REPLY_CONFIG = {
    "enabled": True,
    "call_ai_only_when_needed": True,
}


@dataclass(frozen=True)
class FunConfig:
    enabled: bool = True
    use_ai_for_fun_replies: bool = False
    spontaneous_reply_chance: float = 0.03
    spontaneous_cooldown_seconds: int = 300
    max_fun_replies_per_channel_per_hour: int = 5
    safe_roasts_only: bool = True

    @classmethod
    def from_env(cls) -> "FunConfig":
        return cls(
            enabled=_as_bool("FUN_ENABLED", FUN_CONFIG["enabled"]),
            use_ai_for_fun_replies=_as_bool("FUN_USE_AI", FUN_CONFIG["use_ai_for_fun_replies"]),
            spontaneous_reply_chance=_as_float("FUN_REPLY_CHANCE", FUN_CONFIG["spontaneous_reply_chance"]),
            spontaneous_cooldown_seconds=_as_int(
                "FUN_COOLDOWN_SECONDS",
                FUN_CONFIG["spontaneous_cooldown_seconds"],
            ),
            max_fun_replies_per_channel_per_hour=_as_int(
                "FUN_MAX_PER_CHANNEL_HOUR",
                FUN_CONFIG["max_fun_replies_per_channel_per_hour"],
            ),
            safe_roasts_only=_as_bool("FUN_SAFE_ROASTS_ONLY", FUN_CONFIG["safe_roasts_only"]),
        )


@dataclass(frozen=True)
class XPConfig:
    enabled: bool = True
    cooldown_seconds: int = 180
    max_xp_per_user_per_hour: int = 100

    @classmethod
    def from_env(cls) -> "XPConfig":
        return cls(
            enabled=_as_bool("XP_ENABLED", XP_CONFIG["enabled"]),
            cooldown_seconds=_as_int("XP_COOLDOWN_SECONDS", XP_CONFIG["cooldown_seconds"]),
            max_xp_per_user_per_hour=_as_int("XP_MAX_PER_USER_HOUR", XP_CONFIG["max_xp_per_user_per_hour"]),
        )


@dataclass(frozen=True)
class LocalReplyConfig:
    enabled: bool = True
    call_ai_only_when_needed: bool = True

    @classmethod
    def from_env(cls) -> "LocalReplyConfig":
        return cls(
            enabled=_as_bool("LOCAL_REPLIES_ENABLED", LOCAL_REPLY_CONFIG["enabled"]),
            call_ai_only_when_needed=_as_bool(
                "LOCAL_REPLIES_CALL_AI_ONLY_WHEN_NEEDED",
                LOCAL_REPLY_CONFIG["call_ai_only_when_needed"],
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
