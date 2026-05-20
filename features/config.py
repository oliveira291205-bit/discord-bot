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

WAKE_WORD_CONFIG = {
    "enabled": True,
    "names": ["goku", "cacaroto", "kakaroto"],
    "require_wake_word_for_natural_replies": True,
    "allow_direct_mention": True,
    "allow_reply_to_bot": True,
    "allow_active_conversation_window": True,
    "active_conversation_seconds": 120,
}

GIF_CONFIG = {
    "enabled": True,
    "gif_reply_chance": 0.22,
    "min_chance": 0.20,
    "max_chance": 0.25,
    "cooldown_seconds": 300,
    "max_gifs_per_channel_per_hour": 4,
    "max_gifs_per_user_per_hour": 3,
    "use_external_gif_api": False,
    "use_local_gif_pool": True,
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


@dataclass(frozen=True)
class WakeWordConfig:
    enabled: bool = True
    names: tuple[str, ...] = ("goku", "cacaroto", "kakaroto")
    require_wake_word_for_natural_replies: bool = True
    allow_direct_mention: bool = True
    allow_reply_to_bot: bool = True
    allow_active_conversation_window: bool = True
    active_conversation_seconds: int = 120

    @classmethod
    def from_env(cls) -> "WakeWordConfig":
        raw_names = os.getenv("REI_WAKE_WORDS", ",".join(WAKE_WORD_CONFIG["names"]))
        names = tuple(name.strip().lower() for name in raw_names.split(",") if name.strip())
        return cls(
            enabled=_as_bool("REI_WAKE_WORDS_ENABLED", WAKE_WORD_CONFIG["enabled"]),
            names=names or tuple(WAKE_WORD_CONFIG["names"]),
            require_wake_word_for_natural_replies=_as_bool(
                "REI_REQUIRE_WAKE_WORD_FOR_NATURAL",
                WAKE_WORD_CONFIG["require_wake_word_for_natural_replies"],
            ),
            allow_direct_mention=_as_bool("REI_ALLOW_DIRECT_MENTION", WAKE_WORD_CONFIG["allow_direct_mention"]),
            allow_reply_to_bot=_as_bool("REI_ALLOW_REPLY_TO_BOT", WAKE_WORD_CONFIG["allow_reply_to_bot"]),
            allow_active_conversation_window=_as_bool(
                "REI_ALLOW_ACTIVE_CONVERSATION",
                WAKE_WORD_CONFIG["allow_active_conversation_window"],
            ),
            active_conversation_seconds=_as_int(
                "REI_ACTIVE_CONVERSATION_SECONDS",
                WAKE_WORD_CONFIG["active_conversation_seconds"],
            ),
        )


@dataclass(frozen=True)
class GifConfig:
    enabled: bool = True
    gif_reply_chance: float = 0.22
    min_chance: float = 0.20
    max_chance: float = 0.25
    cooldown_seconds: int = 300
    max_gifs_per_channel_per_hour: int = 4
    max_gifs_per_user_per_hour: int = 3
    use_external_gif_api: bool = False
    use_local_gif_pool: bool = True

    @classmethod
    def from_env(cls) -> "GifConfig":
        min_chance = _as_float("REI_GIF_MIN_CHANCE", GIF_CONFIG["min_chance"])
        max_chance = _as_float("REI_GIF_MAX_CHANCE", GIF_CONFIG["max_chance"])
        chance = _as_float("REI_GIF_REPLY_CHANCE", GIF_CONFIG["gif_reply_chance"])
        chance = min(max(chance, min_chance), max_chance)
        return cls(
            enabled=_as_bool("REI_GIFS_ENABLED", GIF_CONFIG["enabled"]),
            gif_reply_chance=chance,
            min_chance=min_chance,
            max_chance=max_chance,
            cooldown_seconds=_as_int("REI_GIF_COOLDOWN_SECONDS", GIF_CONFIG["cooldown_seconds"]),
            max_gifs_per_channel_per_hour=_as_int(
                "REI_GIF_MAX_PER_CHANNEL_HOUR",
                GIF_CONFIG["max_gifs_per_channel_per_hour"],
            ),
            max_gifs_per_user_per_hour=_as_int("REI_GIF_MAX_PER_USER_HOUR", GIF_CONFIG["max_gifs_per_user_per_hour"]),
            use_external_gif_api=_as_bool("REI_GIF_USE_EXTERNAL_API", GIF_CONFIG["use_external_gif_api"]),
            use_local_gif_pool=_as_bool("REI_GIF_USE_LOCAL_POOL", GIF_CONFIG["use_local_gif_pool"]),
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
