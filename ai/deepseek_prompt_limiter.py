from __future__ import annotations

import logging
import os
from dataclasses import dataclass

from memory.memory_config import DEEPSEEK_PROMPT_CONFIG

LOGGER = logging.getLogger("rei_suzukawa.prompt_budget")


class PromptTooLargeError(RuntimeError):
    pass


@dataclass(frozen=True)
class PromptBudgetConfig:
    max_total_prompt_chars: int = 24000
    max_total_estimated_tokens: int = 6000
    max_system_prompt_chars: int = 4000
    max_memory_context_chars: int = 5000
    max_recent_context_chars: int = 4000
    max_user_message_chars: int = 3000
    max_injected_memories: int = 10
    max_chars_per_memory: int = 250
    hard_block_if_above_chars: int = 32000
    hard_block_if_above_estimated_tokens: int = 8000
    debug_prompt_size: bool = True

    @classmethod
    def from_env(cls) -> "PromptBudgetConfig":
        return cls(
            max_total_prompt_chars=_as_int("DEEPSEEK_MAX_TOTAL_PROMPT_CHARS", DEEPSEEK_PROMPT_CONFIG["max_total_prompt_chars"]),
            max_total_estimated_tokens=_as_int(
                "DEEPSEEK_MAX_TOTAL_ESTIMATED_TOKENS",
                DEEPSEEK_PROMPT_CONFIG["max_total_estimated_tokens"],
            ),
            max_system_prompt_chars=_as_int("DEEPSEEK_MAX_SYSTEM_PROMPT_CHARS", DEEPSEEK_PROMPT_CONFIG["max_system_prompt_chars"]),
            max_memory_context_chars=_as_int("DEEPSEEK_MAX_MEMORY_CONTEXT_CHARS", DEEPSEEK_PROMPT_CONFIG["max_memory_context_chars"]),
            max_recent_context_chars=_as_int("DEEPSEEK_MAX_RECENT_CONTEXT_CHARS", DEEPSEEK_PROMPT_CONFIG["max_recent_context_chars"]),
            max_user_message_chars=_as_int("DEEPSEEK_MAX_USER_MESSAGE_CHARS", DEEPSEEK_PROMPT_CONFIG["max_user_message_chars"]),
            max_injected_memories=_as_int("DEEPSEEK_MAX_INJECTED_MEMORIES", DEEPSEEK_PROMPT_CONFIG["max_injected_memories"]),
            max_chars_per_memory=_as_int("DEEPSEEK_MAX_CHARS_PER_MEMORY", DEEPSEEK_PROMPT_CONFIG["max_chars_per_memory"]),
            hard_block_if_above_chars=_as_int("DEEPSEEK_HARD_BLOCK_CHARS", DEEPSEEK_PROMPT_CONFIG["hard_block_if_above_chars"]),
            hard_block_if_above_estimated_tokens=_as_int(
                "DEEPSEEK_HARD_BLOCK_ESTIMATED_TOKENS",
                DEEPSEEK_PROMPT_CONFIG["hard_block_if_above_estimated_tokens"],
            ),
            debug_prompt_size=_as_bool("DEEPSEEK_DEBUG_PROMPT_SIZE", DEEPSEEK_PROMPT_CONFIG["debug_prompt_size"]),
        )


class PromptBudgetManager:
    def __init__(self, config: PromptBudgetConfig) -> None:
        self.config = config

    def enforce(self, messages: list[dict[str, str]]) -> list[dict[str, str]]:
        limited = [dict(message) for message in messages]
        limited = self._trim_individual_sections(limited)
        limited = self._reduce_until_within_budget(limited)
        stats = self.stats(limited)
        if self.config.debug_prompt_size:
            LOGGER.info(
                "[DeepSeek Prompt Budget] system_prompt_chars=%s memory_context_chars=%s "
                "recent_context_chars=%s user_message_chars=%s total_chars=%s estimated_tokens=%s memories_injected=%s",
                stats["system_prompt_chars"],
                stats["memory_context_chars"],
                stats["recent_context_chars"],
                stats["user_message_chars"],
                stats["total_chars"],
                stats["estimated_tokens"],
                stats["memories_injected"],
            )
        if self._above_hard_limit(limited):
            fallback = self._safe_fallback(limited)
            if self._above_hard_limit(fallback):
                raise PromptTooLargeError("Prompt continuou acima do hard limit apos reducao.")
            return fallback
        return limited

    def stats(self, messages: list[dict[str, str]]) -> dict[str, int]:
        system_chars = 0
        memory_chars = 0
        recent_chars = 0
        user_chars = 0
        memories_injected = 0
        for index, message in enumerate(messages):
            content = message.get("content", "")
            kind = classify_message(message, index, len(messages))
            if kind == "memory":
                memory_chars += len(content)
                memories_injected += content.count("- ")
            elif kind == "recent":
                recent_chars += len(content)
            elif kind == "user":
                user_chars += len(content)
            else:
                system_chars += len(content)
        total = sum(len(message.get("content", "")) for message in messages)
        return {
            "system_prompt_chars": system_chars,
            "memory_context_chars": memory_chars,
            "recent_context_chars": recent_chars,
            "user_message_chars": user_chars,
            "total_chars": total,
            "estimated_tokens": estimate_tokens_from_messages(messages),
            "memories_injected": min(memories_injected, self.config.max_injected_memories),
        }

    def _trim_individual_sections(self, messages: list[dict[str, str]]) -> list[dict[str, str]]:
        result: list[dict[str, str]] = []
        for index, message in enumerate(messages):
            kind = classify_message(message, index, len(messages))
            content = message.get("content", "")
            if kind == "system":
                content = trim(content, self.config.max_system_prompt_chars)
            elif kind == "memory":
                content = trim_memory_block(
                    content,
                    max_block_chars=self.config.max_memory_context_chars,
                    max_items=self.config.max_injected_memories,
                    max_item_chars=self.config.max_chars_per_memory,
                )
            elif kind == "recent":
                content = trim(content, self.config.max_recent_context_chars // 2)
            elif kind == "user":
                content = trim(content, self.config.max_user_message_chars)
            item = dict(message)
            item["content"] = content
            result.append(item)
        return result

    def _reduce_until_within_budget(self, messages: list[dict[str, str]]) -> list[dict[str, str]]:
        result = list(messages)
        while self._above_soft_limit(result):
            memory_indexes = [i for i, msg in enumerate(result) if classify_message(msg, i, len(result)) == "memory"]
            if memory_indexes:
                for i in memory_indexes:
                    result[i]["content"] = trim_memory_block(
                        result[i].get("content", ""),
                        max_block_chars=max(800, self.config.max_memory_context_chars // 2),
                        max_items=max(3, self.config.max_injected_memories // 2),
                        max_item_chars=min(180, self.config.max_chars_per_memory),
                    )
                if not self._above_soft_limit(result):
                    break
            recent_indexes = [i for i, msg in enumerate(result) if classify_message(msg, i, len(result)) == "recent"]
            if recent_indexes:
                del result[recent_indexes[0]]
                continue
            removable_system = [
                i for i, msg in enumerate(result[:-1]) if classify_message(msg, i, len(result)) == "system" and i != 0
            ]
            if removable_system:
                del result[removable_system[-1]]
                continue
            result = self._safe_fallback(result)
            break
        return result

    def _safe_fallback(self, messages: list[dict[str, str]]) -> list[dict[str, str]]:
        system = next((msg for idx, msg in enumerate(messages) if classify_message(msg, idx, len(messages)) == "system"), None)
        user = next((msg for idx, msg in reversed(list(enumerate(messages))) if classify_message(msg, idx, len(messages)) == "user"), None)
        hard_chars = max(500, self.config.hard_block_if_above_chars - 200)
        system_limit = min(self.config.max_system_prompt_chars, max(200, hard_chars // 2))
        user_limit = min(self.config.max_user_message_chars, max(200, hard_chars - system_limit))
        fallback = []
        if system:
            fallback.append({"role": "system", "content": trim(system.get("content", ""), system_limit)})
        if user:
            fallback.append({"role": "user", "content": trim(user.get("content", ""), user_limit)})
        return fallback

    def _above_soft_limit(self, messages: list[dict[str, str]]) -> bool:
        total = total_chars(messages)
        return total > self.config.max_total_prompt_chars or estimate_tokens_from_messages(messages) > self.config.max_total_estimated_tokens

    def _above_hard_limit(self, messages: list[dict[str, str]]) -> bool:
        total = total_chars(messages)
        return (
            total > self.config.hard_block_if_above_chars
            or estimate_tokens_from_messages(messages) > self.config.hard_block_if_above_estimated_tokens
        )


def classify_message(message: dict[str, str], index: int, total_messages: int) -> str:
    content = message.get("content", "")
    role = message.get("role", "")
    if index == total_messages - 1 and role == "user":
        return "user"
    if "[MEMORIA" in content or "[MEMÓRIA" in content or "Memorias persistentes" in content:
        return "memory"
    if role in {"assistant", "user"} and index != total_messages - 1:
        return "recent"
    return "system"


def trim_memory_block(content: str, *, max_block_chars: int, max_items: int, max_item_chars: int) -> str:
    lines = []
    memory_count = 0
    for line in (content or "").splitlines():
        if line.startswith("- "):
            if memory_count >= max_items:
                continue
            memory_count += 1
            lines.append(trim(line, max_item_chars + 2))
        else:
            lines.append(line)
        if len("\n".join(lines)) >= max_block_chars:
            break
    return trim("\n".join(lines), max_block_chars)


def estimate_tokens(text: str) -> int:
    return int(len(text or "") / 4)


def estimate_tokens_from_messages(messages: list[dict[str, str]]) -> int:
    return estimate_tokens("\n".join(message.get("content", "") for message in messages))


def total_chars(messages: list[dict[str, str]]) -> int:
    return sum(len(message.get("content", "")) for message in messages)


def trim(text: str, limit: int) -> str:
    if len(text or "") <= limit:
        return text or ""
    return (text or "")[: max(0, limit - 18)].rstrip() + "\n...[cortado]"


def _as_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _as_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "sim", "yes", "on"}
