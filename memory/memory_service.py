from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict

from .memory_config import MemoryConfig
from .memory_extractor import extract_memories_from_message
from .memory_privacy import (
    asks_channel_memory,
    asks_self_memory,
    is_sensitive_memory,
    wants_forget,
    wants_no_save,
)
from .memory_retriever import MemoryRetriever
from .memory_store import SQLiteMemoryStore, build_scope_id
from .memory_summarizer import summarize_memories
from .memory_types import Memory, MemoryCandidate, MemoryContext

LOGGER = logging.getLogger("rei_suzukawa.memory")
DIRECT_NATURAL_SAVE_PATTERN = re.compile(
    r"\b(lembra que|guarda isso|salva isso|salva isso na sua memoria|salva isso na sua memória|nao esquece|não esquece)\b",
    re.IGNORECASE,
)


class MemoryService:
    def __init__(self, config: MemoryConfig) -> None:
        self.config = config
        self.store = SQLiteMemoryStore(config.sqlite_path, use_fts5=config.use_sqlite_fts5, debug=config.debug)
        self.retriever = MemoryRetriever(self.store, config)

    def close(self) -> None:
        self.store.close()

    def context_from_message(self, message: object) -> MemoryContext:
        guild = getattr(message, "guild", None)
        channel = getattr(message, "channel", None)
        author = getattr(message, "author", None)
        return MemoryContext(
            guild_id=str(getattr(guild, "id", "")) if guild else None,
            channel_id=str(getattr(channel, "id", "")) if channel else None,
            user_id=str(getattr(author, "id", "")) if author else None,
            message_id=str(getattr(message, "id", "")) if getattr(message, "id", None) else None,
            author_name=getattr(author, "display_name", None) if author else None,
            guild_name=getattr(guild, "name", None) if guild else None,
            channel_name=getattr(channel, "name", None) if channel else None,
        )

    def get_prompt_context(
        self,
        *,
        context: MemoryContext,
        current_message: str,
    ) -> tuple[str, list[Memory]]:
        if not self.config.enabled:
            return "", []
        try:
            memories = self.retriever.get_relevant_memories(
                guild_id=context.guild_id,
                channel_id=context.channel_id,
                user_id=context.user_id,
                current_message=current_message,
                limit=self.config.max_injected_memories,
            )
            return format_memory_block(memories, max_chars=self.config.max_memory_chars), memories
        except Exception:
            LOGGER.exception("Erro recuperando memorias")
            return "", []

    def save_from_user_message(
        self,
        *,
        context: MemoryContext,
        text: str,
    ) -> list[Memory]:
        if not self.config.enabled or wants_no_save(text):
            return []
        try:
            candidates = extract_memories_from_message(text, channel_name=context.channel_name)
            return self.save_candidates(context=context, candidates=candidates)
        except Exception:
            LOGGER.exception("Erro extraindo memorias")
            return []

    def save_manual_memory(self, *, context: MemoryContext, text: str) -> Memory | None:
        if not text.strip() or is_sensitive_memory(text):
            return None
        candidate = MemoryCandidate(
            scope_type="user",
            memory_type="fact",
            content=f"O usuario pediu para lembrar: {text.strip()}",
            tags=["manual", "lembrado"],
            importance=10,
            confidence=0.92,
        )
        saved = self.save_candidates(context=context, candidates=[candidate])
        return saved[0] if saved else None

    def save_attachment_memory(self, *, context: MemoryContext, text: str, tags: list[str]) -> Memory | None:
        if not text.strip() or is_sensitive_memory(text):
            return None
        candidate = MemoryCandidate(
            scope_type="user_channel",
            memory_type="context",
            content=trim(text, 900),
            tags=["anexo", *tags],
            importance=7,
            confidence=0.78,
        )
        saved = self.save_candidates(context=context, candidates=[candidate])
        return saved[0] if saved else None

    def save_observed_message(self, *, context: MemoryContext, text: str) -> list[Memory]:
        if not self.config.enabled or wants_no_save(text):
            return []
        saved = self.save_from_user_message(context=context, text=text)
        if is_sensitive_memory(text):
            return saved

        clean = trim(text, 500)
        if len(clean) < 3:
            return saved

        observed = MemoryCandidate(
            scope_type="user_channel",
            memory_type="context",
            content=f"Mensagem observada de {context.author_name or 'usuario'} neste canal: {clean}",
            tags=["chat", "observado", context.channel_name or "canal"],
            importance=2,
            confidence=0.55,
        )
        return [*saved, *self.save_candidates(context=context, candidates=[observed])]

    def save_candidates(self, *, context: MemoryContext, candidates: list[MemoryCandidate]) -> list[Memory]:
        saved: list[Memory] = []
        for candidate in candidates:
            if not self.is_scope_allowed(candidate.scope_type) or is_sensitive_memory(candidate.content):
                if self.config.debug:
                    LOGGER.debug("Memoria bloqueada por privacidade ou escopo: %s", candidate.scope_type)
                continue
            try:
                memory = self.store.upsert_memory(
                    candidate,
                    context,
                    source_message_id=context.message_id,
                    source_author_id=context.user_id,
                )
                if memory:
                    saved.append(memory)
                    if self.config.debug:
                        LOGGER.debug("Memoria salva/atualizada: id=%s scope=%s", memory.id, memory.scope_type)
            except Exception:
                LOGGER.exception("Erro salvando memoria")
        return saved

    def handle_natural_memory_command(self, *, context: MemoryContext, text: str) -> str | None:
        clean = text or ""
        if asks_self_memory(clean):
            return self.render_user_memories(context)
        if asks_channel_memory(clean):
            return self.render_channel_memories(context)
        if DIRECT_NATURAL_SAVE_PATTERN.search(clean) and not wants_no_save(clean):
            saved = self.save_from_user_message(context=context, text=clean)
            return "Guardei isso na memoria local." if saved else "Tentei guardar, mas nao vi uma informacao util ou segura nisso."
        if wants_forget(clean):
            removed = self.store.forget_related(context=context, query=clean)
            return f"Apaguei {removed} memoria(s) relacionada(s)." if removed else "Nao achei memoria relacionada para apagar."
        if "limpa minha memoria" in clean.lower() or "limpa minha memória" in clean.lower():
            removed = self.forget_user(context)
            return f"Limpei {removed} memoria(s) suas."
        if "limpa a memoria deste canal" in clean.lower() or "limpa a memória deste canal" in clean.lower():
            removed = self.forget_channel(context)
            return f"Limpei {removed} memoria(s) deste canal."
        return None

    def render_user_memories(self, context: MemoryContext, *, limit: int = 12) -> str:
        if not context.user_id:
            return "Nao tenho usuario identificado aqui."
        memories = self.store.list_memories(user_id=context.user_id, limit=limit)
        return render_memory_list("O que lembro de voce", memories)

    def render_channel_memories(self, context: MemoryContext, *, limit: int = 12) -> str:
        if not context.channel_id:
            return "Nao tenho canal identificado aqui."
        memories = self.store.list_memories(channel_id=context.channel_id, limit=limit)
        return render_memory_list("O que lembro deste canal", memories)

    def render_guild_memories(self, context: MemoryContext, *, limit: int = 12) -> str:
        if not context.guild_id:
            return "Nao tenho servidor identificado aqui."
        memories = self.store.list_memories(guild_id=context.guild_id, limit=limit)
        return render_memory_list("O que lembro deste servidor", memories)

    def export_user_memories(self, context: MemoryContext) -> str:
        if not context.user_id:
            return "[]"
        data = self.store.export_scope(scope_type="user", scope_id=build_scope_id("user", context))
        return json.dumps(data, ensure_ascii=False, indent=2)

    def debug_memories(self, context: MemoryContext, text: str) -> str:
        block, memories = self.get_prompt_context(context=context, current_message=text)
        if not memories:
            return "Nenhuma memoria seria injetada."
        ids = ", ".join(str(memory.id) for memory in memories)
        return f"IDs injetados: {ids}\n\n{block}"

    def summarize_user(self, context: MemoryContext) -> str:
        return summarize_memories(self.store.list_memories(user_id=context.user_id, limit=200) if context.user_id else [])

    def forget_user(self, context: MemoryContext) -> int:
        if not context.user_id:
            return 0
        return self.store.deactivate_user(context.user_id)

    def forget_channel(self, context: MemoryContext) -> int:
        if not context.channel_id:
            return 0
        return self.store.deactivate_channel(context.channel_id)

    def forget_guild(self, context: MemoryContext) -> int:
        if not context.guild_id:
            return 0
        return self.store.deactivate_guild(context.guild_id)

    def status(self, context: MemoryContext) -> dict[str, int | str | bool]:
        return {
            "enabled": self.config.enabled,
            "sqlite_path": str(self.config.sqlite_path),
            "fts5": self.store.fts_enabled,
            "total": self.store.count_all(),
            **self.store.counts_for_context(context),
        }

    def is_scope_allowed(self, scope_type: str) -> bool:
        return {
            "global": self.config.allow_global_memory,
            "guild": self.config.allow_guild_memory,
            "channel": self.config.allow_channel_memory,
            "user": self.config.allow_user_memory,
            "user_channel": self.config.allow_user_channel_memory,
            "session": True,
        }.get(scope_type, False)


def format_memory_block(memories: list[Memory], *, max_chars: int) -> str:
    if not memories:
        return ""
    grouped: dict[str, list[str]] = {
        "global": [],
        "guild": [],
        "channel": [],
        "user": [],
        "user_channel": [],
        "session": [],
    }
    labels = {
        "global": "[MEMORIA GLOBAL]",
        "guild": "[MEMORIA DO SERVIDOR]",
        "channel": "[MEMORIA DO CANAL ATUAL]",
        "user": "[MEMORIA DO USUARIO]",
        "user_channel": "[MEMORIA DO USUARIO NESTE CANAL]",
        "session": "[CONTEXTO RECENTE]",
    }
    for memory in memories:
        grouped.setdefault(memory.scope_type, []).append(f"- {trim(memory.content, max_chars)}")

    sections = [
        "Use as memorias abaixo apenas como contexto. Nao invente memorias. Nao diga que possui banco de dados interno. "
        "Nao cite memorias desnecessariamente. Nao misture informacoes de canais diferentes. "
        "Se houver conflito, priorize a memoria mais recente e mais confiavel."
    ]
    for scope, items in grouped.items():
        if items:
            sections.append(labels.get(scope, f"[{scope.upper()}]"))
            sections.extend(items)
    return "\n".join(sections)


def render_memory_list(title: str, memories: list[Memory]) -> str:
    if not memories:
        return f"{title}: nada salvo ainda."
    lines = [f"{title}:"]
    for index, memory in enumerate(memories[:12], start=1):
        tags = ", ".join(memory.tags[:4]) or "sem tags"
        lines.append(f"{index}. {trim(memory.content, 180)} (`{memory.scope_type}`, `{memory.memory_type}`, {tags})")
    return "\n".join(lines)


def trim(text: str, limit: int) -> str:
    clean = " ".join((text or "").split())
    if len(clean) <= limit:
        return clean
    return clean[: limit - 3].rstrip() + "..."
