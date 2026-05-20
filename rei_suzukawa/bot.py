from __future__ import annotations

import asyncio
import logging
import os
import random
import re
import sys
import time
import unicodedata
from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path
from typing import DefaultDict, Deque

import discord
from discord.ext import commands
from dotenv import load_dotenv

if __package__:
    from ai.deepseek_prompt_limiter import PromptBudgetConfig, PromptBudgetManager, PromptTooLargeError
    from features.config import FunConfig, LocalReplyConfig, XPConfig
    from features.code_reader import list_code_files, read_code_file, summarize_codebase
    from features.error_detector import detect_error_reply
    from features.local_replies import LocalReplyEngine, is_study_or_programming, needs_teacher_mode
    from features.status import BotStatusInfo, render_status, wants_status
    from features.xp import XPService
    from memory.memory_commands import MemoryCommands
    from memory.memory_config import MemoryConfig, NaturalInteractionConfig
    from memory.natural_interactions import NaturalInteractionManager
    from memory.memory_privacy import wants_no_save
    from memory.memory_service import MemoryService
    from .attachments import (
        AttachmentAnalysis,
        analyze_attachment,
        attachment_branches,
        format_attachment_context,
        format_attachment_memory,
    )
    from .deepseek import DeepSeekClient, DeepSeekNotConfigured, DeepSeekRequestError, DeepSeekSettings
    from .gif_search import GifSearchSettings, search_free_gif
    from .logic import (
        BOT_NAME,
        build_emotion_prompt,
        build_system_prompt,
        chunk_text,
        clean_user_prompt,
        detect_emotional_mode,
        detect_resenha_trigger,
        detect_trigger,
        is_friend_bot_name,
    )
else:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from ai.deepseek_prompt_limiter import PromptBudgetConfig, PromptBudgetManager, PromptTooLargeError
    from features.config import FunConfig, LocalReplyConfig, XPConfig
    from features.code_reader import list_code_files, read_code_file, summarize_codebase
    from features.error_detector import detect_error_reply
    from features.local_replies import LocalReplyEngine, is_study_or_programming, needs_teacher_mode
    from features.status import BotStatusInfo, render_status, wants_status
    from features.xp import XPService
    from memory.memory_commands import MemoryCommands
    from memory.memory_config import MemoryConfig, NaturalInteractionConfig
    from memory.natural_interactions import NaturalInteractionManager
    from memory.memory_privacy import wants_no_save
    from memory.memory_service import MemoryService
    from rei_suzukawa.attachments import (
        AttachmentAnalysis,
        analyze_attachment,
        attachment_branches,
        format_attachment_context,
        format_attachment_memory,
    )
    from rei_suzukawa.deepseek import DeepSeekClient, DeepSeekNotConfigured, DeepSeekRequestError, DeepSeekSettings
    from rei_suzukawa.gif_search import GifSearchSettings, search_free_gif
    from rei_suzukawa.logic import (
        BOT_NAME,
        build_emotion_prompt,
        build_system_prompt,
        chunk_text,
        clean_user_prompt,
        detect_emotional_mode,
        detect_resenha_trigger,
        detect_trigger,
        is_friend_bot_name,
    )

LOGGER = logging.getLogger("rei_suzukawa")
GIF_MARKER_PATTERN = re.compile(r"\s*\[gif:([^\]]+)\]\s*", re.IGNORECASE)
GIF_LINK_PATTERN = re.compile(r"https?://\S*(?:giphy\.com|media\.giphy\.com|\\.gif)\S*", re.IGNORECASE)
GIF_REQUEST_PATTERN = re.compile(r"\b(gif|gifs|manda.*gif|mandar.*gif|outro.*gif|diferente.*gif)\b", re.IGNORECASE)
GIF_THEME_ALIASES = {
    "risada": "risada",
    "rindo": "risada",
    "engracado": "risada",
    "engracada": "risada",
    "raiva": "raiva",
    "bravo": "raiva",
    "irritado": "raiva",
    "confuso": "confuso",
    "confusao": "confuso",
    "comemoracao": "comemoracao",
    "comemorando": "comemoracao",
    "vitoria": "comemoracao",
    "conforto": "conforto",
    "apoio": "conforto",
}
GIF_URLS = {
    "risada": [
        "https://media.giphy.com/media/SPuyENBLQCFCU/giphy.gif",
        "https://media.giphy.com/media/WwBwZqiPIvoE1tFgRS/giphy.gif",
    ],
    "raiva": [
        "https://media.giphy.com/media/dJHaTbNQOjYMWdHSTG/giphy.gif",
        "https://media.giphy.com/media/uaELpZyJI4Kv7qgKoF/giphy.gif",
    ],
    "confuso": [
        "https://media.giphy.com/media/xUNd9Ljg37yeVcCHyE/giphy.gif",
        "https://media.giphy.com/media/SPuyENBLQCFCU/giphy.gif",
    ],
    "comemoracao": [
        "https://media.giphy.com/media/dJHaTbNQOjYMWdHSTG/giphy.gif",
        "https://media.giphy.com/media/uaELpZyJI4Kv7qgKoF/giphy.gif",
    ],
    "conforto": [
        "https://media.giphy.com/media/WwBwZqiPIvoE1tFgRS/giphy.gif",
        "https://media.giphy.com/media/xUNd9Ljg37yeVcCHyE/giphy.gif",
    ],
}


@dataclass(frozen=True)
class BotSettings:
    discord_token: str
    prefix: str
    max_history: int
    memory: MemoryConfig
    natural_interactions: NaturalInteractionConfig
    fun: FunConfig
    xp: XPConfig
    local_replies: LocalReplyConfig
    prompt_budget: PromptBudgetConfig
    auto_memory_enabled: bool
    observe_all_messages: bool
    resenha_history_limit: int
    attachment_max_bytes: int
    gifs_enabled: bool
    gif_cooldown_seconds: int
    gif_search: GifSearchSettings
    deepseek: DeepSeekSettings

    @classmethod
    def from_env(cls) -> "BotSettings":
        load_dotenv()
        return cls(
            discord_token=os.getenv("DISCORD_TOKEN", "").strip(),
            prefix=os.getenv("REI_PREFIX", "!").strip() or "!",
            max_history=_as_int("REI_MAX_HISTORY", 14),
            memory=MemoryConfig.from_env(),
            natural_interactions=NaturalInteractionConfig.from_env(),
            fun=FunConfig.from_env(),
            xp=XPConfig.from_env(),
            local_replies=LocalReplyConfig.from_env(),
            prompt_budget=PromptBudgetConfig.from_env(),
            auto_memory_enabled=_as_bool("REI_AUTO_MEMORY", True),
            observe_all_messages=_as_bool("REI_OBSERVE_ALL_MESSAGES", True),
            resenha_history_limit=_as_int("REI_RESENHA_LIMIT", 250),
            attachment_max_bytes=_as_int("REI_ATTACHMENT_MAX_BYTES", 8 * 1024 * 1024),
            gifs_enabled=_as_bool("REI_GIFS_ENABLED", True),
            gif_cooldown_seconds=_as_int("REI_GIF_COOLDOWN_SECONDS", 600),
            gif_search=GifSearchSettings(limit=_as_int("REI_GIF_SEARCH_LIMIT", 12)),
            deepseek=DeepSeekSettings(
                api_key=os.getenv("DEEPSEEK_API_KEY", "").strip(),
                base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").strip(),
                model=os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash").strip(),
                temperature=_as_float("REI_TEMPERATURE", 0.8),
            ),
        )


class ReiSuzukawaBot(commands.Bot):
    def __init__(self, settings: BotSettings) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        intents.messages = True
        intents.guilds = True

        super().__init__(
            command_prefix=commands.when_mentioned_or(settings.prefix, "goku ", "kakaroto ", "kakarot ", "rei ", "suzukawa "),
            intents=intents,
            case_insensitive=True,
            help_command=None,
            allowed_mentions=discord.AllowedMentions(everyone=False, roles=False, users=True, replied_user=False),
        )
        self.settings = settings
        self.deepseek = DeepSeekClient(settings.deepseek)
        self.memory_service = MemoryService(settings.memory)
        self.xp_service = XPService(settings.memory.sqlite_path, settings.xp)
        self.local_replies = LocalReplyEngine(enabled=settings.local_replies.enabled)
        self.natural_interactions = NaturalInteractionManager(settings.natural_interactions)
        self.prompt_budget = PromptBudgetManager(settings.prompt_budget)
        self.started_at = time.monotonic()
        self.channel_history: DefaultDict[int, Deque[dict[str, str]]] = defaultdict(
            lambda: deque(maxlen=settings.max_history)
        )
        self.user_memories: DefaultDict[int, list[str]] = defaultdict(list)
        self.last_gif_by_channel: dict[int, float] = {}
        self.last_gif_url_by_channel: dict[int, str] = {}
        self.attachment_cache: dict[int, list[AttachmentAnalysis]] = {}

    async def setup_hook(self) -> None:
        await self.add_cog(ReiCommands(self))
        await self.add_cog(MemoryCommands(self, self.memory_service))

    async def close(self) -> None:
        self.xp_service.close()
        self.memory_service.close()
        await super().close()

    async def on_ready(self) -> None:
        user = self.user or BOT_NAME
        LOGGER.info("%s esta online como %s", BOT_NAME, user)
        await self.change_presence(activity=discord.Game(name="diga goku ou kakaroto"))

    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot and not is_friend_bot_name(message.author.display_name):
            return

        if message.author.bot and self.user and message.author.id == self.user.id:
            return

        attachment_analyses = await self.collect_attachment_analyses(message)
        self.attachment_cache[message.id] = attachment_analyses
        if len(self.attachment_cache) > 200:
            self.attachment_cache.pop(next(iter(self.attachment_cache)))
        if attachment_analyses:
            self.save_attachment_memory(message, attachment_analyses)
        self.observe_message_memory(message)

        if detect_resenha_trigger(message.content):
            async with message.channel.typing():
                answer = await self.generate_channel_resenha(message)
            await self.send_ai_reply(message, answer)
            return

        ctx = await self.get_context(message)
        if ctx.valid:
            await self.invoke(ctx)
            return

        context = self.memory_service.context_from_message(message)
        xp_event = self.xp_service.award(
            user_id=context.user_id,
            guild_id=context.guild_id,
            reason=self.xp_service.classify_reason(message.content),
        )

        error_hint = detect_error_reply(message.content)
        if error_hint:
            event = self.xp_service.award(
                user_id=context.user_id,
                guild_id=context.guild_id,
                reason=error_hint.xp_reason,
            )
            await self.send_text_reply_with_gif(
                message,
                append_xp_message(error_hint.reply, event or xp_event),
                query=message.content,
                force=True,
            )
            return

        if wants_status(message.content):
            await self.send_text_reply_with_gif(message, self.render_bot_status(), query=message.content, force=True)
            return

        natural_answer = self.natural_interactions.maybe_handle_lore_confirmation(
            context=context,
            text=message.content,
            memory_service=self.memory_service,
        )
        if natural_answer:
            await self.send_text_reply_with_gif(message, natural_answer, query=message.content, force=True)
            return

        natural_answer = self.memory_service.handle_natural_memory_command(
            context=context,
            text=message.content,
        )
        if natural_answer:
            await self.send_text_reply_with_gif(message, natural_answer, query=message.content, force=True)
            return

        natural_answer = self.natural_interactions.handle_preference_signal(
            context=context,
            text=message.content,
            memory_service=self.memory_service,
        )
        if natural_answer:
            await self.send_text_reply_with_gif(message, natural_answer, query=message.content, force=True)
            return

        bot_id = self.user.id if self.user else None
        was_mentioned = bool(self.user and self.user in message.mentions)
        triggered = detect_trigger(message.content)
        local_reply = self.local_replies.generate(
            clean_user_prompt(message.content, bot_id) if (was_mentioned or triggered) else message.content,
            direct=was_mentioned or triggered,
        )
        if local_reply and (was_mentioned or triggered):
            event = self.xp_service.award(
                user_id=context.user_id,
                guild_id=context.guild_id,
                reason=local_reply.xp_reason,
            )
            await self.send_text_reply_with_gif(
                message,
                append_xp_message(local_reply.text, event or xp_event),
                query=message.content,
                force=True,
            )
            return

        if not (was_mentioned or triggered):
            decision = self.natural_interactions.should_interact_naturally(
                message=message,
                context=context,
                was_mentioned=was_mentioned,
                triggered=triggered,
                is_command=False,
                memory_service=self.memory_service,
            )
            if decision.should_reply:
                reply = self.natural_interactions.generate_natural_interaction(
                    message=message,
                    context=context,
                    memory_service=self.memory_service,
                )
                if reply:
                    await self.send_text_reply_with_gif(message, reply, query=message.content, force=True)
                    self.natural_interactions.record_reply(context.channel_id)
            return

        prompt = clean_user_prompt(message.content, bot_id)
        if not prompt:
            prompt = "Me chamaram. Puxe assunto com naturalidade."
        if needs_teacher_mode(prompt):
            prompt = (
                "Modo professor de treino: explique passo a passo, com linguagem simples, exemplo curto, "
                "sem pular etapas e com humor leve de parceiro de treino.\n\n"
                f"Pedido do usuario: {prompt}"
            )

        async with message.channel.typing():
            answer = await self.ask_deepseek(message, prompt, attachment_analyses=attachment_analyses)

        await self.send_ai_reply(message, answer)

        if xp_event and xp_event.message:
            await self.send_text_reply_with_gif(message, xp_event.message, query=message.content, force=True)

    async def ask_deepseek(
        self,
        message: discord.Message,
        prompt: str,
        *,
        attachment_analyses: list[AttachmentAnalysis] | None = None,
    ) -> str:
        author_name = message.author.display_name
        messages = self._build_messages(
            message,
            message.channel.id,
            message.author.id,
            author_name,
            prompt,
            attachment_analyses=attachment_analyses or [],
        )

        try:
            answer = await self.call_deepseek(messages)
        except DeepSeekNotConfigured:
            return (
                "Estou no Discord, mas falta configurar `DEEPSEEK_API_KEY` no arquivo `.env` para eu responder pela DeepSeek."
            )
        except PromptTooLargeError:
            return "A mensagem ficou grande demais para enviar com seguranca. Tente mandar em partes menores."
        except DeepSeekRequestError as exc:
            LOGGER.warning("Falha na DeepSeek: %s", exc)
            return f"A DeepSeek travou no caminho: {exc}"
        except Exception:
            LOGGER.exception("Erro inesperado ao responder")
            return "Deu um erro inesperado aqui. Olha o terminal para ver o log completo."

        if self.settings.auto_memory_enabled:
            self.memory_service.save_from_user_message(
                context=self.memory_service.context_from_message(message),
                text=merge_prompt_with_attachments(prompt, attachment_analyses or []),
            )
        self._remember_exchange(
            message.channel.id,
            message.author.id,
            author_name,
            merge_prompt_with_attachments(prompt, attachment_analyses or []),
            strip_gif_marker(answer)[0],
        )
        return answer

    def _build_messages(
        self,
        message: discord.Message,
        channel_id: int,
        user_id: int,
        author_name: str,
        prompt: str,
        *,
        attachment_analyses: list[AttachmentAnalysis],
    ) -> list[dict[str, str]]:
        emotion_mode = detect_emotional_mode(prompt)
        messages = [
            {"role": "system", "content": build_system_prompt()},
            {"role": "system", "content": build_emotion_prompt(emotion_mode)},
        ]

        memories = self.user_memories.get(user_id)
        if memories:
            joined_memories = "\n".join(f"- {memory}" for memory in memories[-8:])
            messages.append(
                {
                    "role": "system",
                    "content": (
                        f"Lembrancas temporarias sobre {author_name} "
                        f"(discord_id={user_id}):\n{joined_memories}"
                    ),
                }
            )

        memory_context, _ = self.memory_service.get_prompt_context(
            context=self.memory_service.context_from_message(message),
            current_message=merge_prompt_with_attachments(prompt, attachment_analyses),
        )
        if memory_context:
            messages.append({"role": "system", "content": memory_context})

        attachment_context = format_attachment_context(attachment_analyses)
        if attachment_context:
            messages.append(
                {
                    "role": "system",
                    "content": (
                        "Use estes anexos apenas quando forem relevantes para o pedido do usuario. "
                        "Se um anexo nao tiver texto extraido, nao invente conteudo visual; diga o limite com naturalidade.\n"
                        f"{attachment_context}"
                    ),
                }
            )

        recent_limit = max(0, self.settings.memory.recent_context_limit)
        messages.extend(list(self.channel_history[channel_id])[-recent_limit:])
        messages.append({"role": "user", "content": f"{author_name} (discord_id={user_id}): {prompt}"})
        return messages

    async def call_deepseek(self, messages: list[dict[str, str]]) -> str:
        limited_messages = self.prompt_budget.enforce(messages)
        return await self.deepseek.chat(limited_messages)

    def _remember_exchange(self, channel_id: int, user_id: int, author_name: str, prompt: str, answer: str) -> None:
        self.channel_history[channel_id].append(
            {"role": "user", "content": f"{author_name} (discord_id={user_id}): {prompt}"}
        )
        self.channel_history[channel_id].append({"role": "assistant", "content": answer})

    def render_bot_status(self) -> str:
        memory_ok = True
        memory_error = None
        try:
            self.memory_service.store.count_all()
        except Exception as exc:
            memory_ok = False
            memory_error = str(exc)[:120]

        return render_status(
            BotStatusInfo(
                deepseek_enabled=self.deepseek.enabled,
                memory_ok=memory_ok,
                memory_error=memory_error,
                sqlite_path=str(self.settings.memory.sqlite_path),
                started_at=self.started_at,
            )
        )

    async def generate_channel_resenha(self, message: discord.Message) -> str:
        try:
            transcript = await self._collect_channel_transcript(message)
        except discord.Forbidden:
            return "Nao consigo averiguar a resenha porque nao tenho permissao para ver o historico desse canal."
        except discord.HTTPException as exc:
            LOGGER.warning("Falha lendo historico para resenha: %s", exc)
            return f"Nao consegui puxar o historico do canal agora: {exc}"

        if not transcript:
            return "Nao achei mensagem suficiente nesse canal para fazer resenha."

        prompt = (
            "Faca uma resenha curta e realista do historico abaixo. Foque em coisas constrangedoras, "
            "exageradas, contraditorias, dramaticas ou engracadas que os usuarios disseram. "
            "Nao invente nada. Nao exponha dado sensivel. Nao use odio, slur, ameaca ou humilhacao pesada. "
            "Pode ser provocante, memeiro e dramatico se combinar, mas sem humilhacao pesada. Responda em portugues do Brasil, "
            "com no maximo 6 bullets curtos e uma frase final no estilo Goku.\n\n"
            f"Historico do canal #{getattr(message.channel, 'name', 'DM')}:\n{transcript}"
        )
        messages = [
            {"role": "system", "content": build_system_prompt()},
            {"role": "system", "content": build_emotion_prompt("alegria")},
            {"role": "user", "content": prompt},
        ]

        try:
            return await self.call_deepseek(messages)
        except DeepSeekNotConfigured:
            return "Falta configurar `DEEPSEEK_API_KEY` no `.env` para eu gerar a resenha."
        except PromptTooLargeError:
            return "O historico ficou grande demais. Reduzi, mas ainda passou do limite seguro."
        except DeepSeekRequestError as exc:
            return f"Tentei gerar a resenha, mas a DeepSeek reclamou: {exc}"

    async def _collect_channel_transcript(self, message: discord.Message) -> str:
        lines: list[str] = []
        limit = max(20, min(self.settings.resenha_history_limit, 1000))
        async for item in message.channel.history(limit=limit, oldest_first=True):
            if item.id == message.id or item.author.bot:
                continue
            content = " ".join((item.content or "").split())
            if not content:
                continue
            if len(content) > 420:
                content = f"{content[:417].rstrip()}..."
            timestamp = item.created_at.strftime("%Y-%m-%d %H:%M")
            lines.append(f"[{timestamp}] {item.author.display_name} (discord_id={item.author.id}): {content}")

        transcript = "\n".join(lines[-limit:])
        if len(transcript) > 14000:
            transcript = transcript[-14000:]
        return transcript

    async def generate_user_starter(
        self,
        message: discord.Message,
        target: discord.abc.User,
        subject: str,
    ) -> str:
        author_name = message.author.display_name
        target_name = getattr(target, "display_name", target.name)
        subject = subject.strip() or "puxe um assunto leve com essa pessoa"
        prompt = (
            f"{author_name} (discord_id={message.author.id}) pediu para voce chamar "
            f"{target_name} (discord_id={target.id}) no chat. "
            f"Assunto/contexto: {subject}\n\n"
            "Crie uma mensagem curta, natural e com personalidade para puxar assunto com essa pessoa. "
            "Use no maximo 2 frases, com o tom animado, competitivo e amigavel do Goku quando combinar. "
            "Nao diga que recebeu uma ordem; apenas chame a pessoa de forma natural."
        )
        messages = [
            {"role": "system", "content": build_system_prompt()},
            {"role": "system", "content": build_emotion_prompt(detect_emotional_mode(subject))},
            {"role": "user", "content": prompt},
        ]
        try:
            answer = await self.call_deepseek(messages)
        except DeepSeekNotConfigured:
            return "Falta configurar `DEEPSEEK_API_KEY` para eu puxar assunto direito."
        except PromptTooLargeError:
            return f"{target.mention} vem ca um instante."
        except DeepSeekRequestError as exc:
            return f"Tentei chamar, mas a DeepSeek deu ruim: {exc}"

        clean_answer = " ".join(answer.split())
        return f"{target.mention} {clean_answer}"

    async def collect_attachment_analyses(self, message: discord.Message) -> list[AttachmentAnalysis]:
        attachments = list(message.attachments)
        if message.reference and message.reference.resolved:
            resolved = message.reference.resolved
            if isinstance(resolved, discord.Message):
                attachments.extend(resolved.attachments)
        elif message.reference and message.reference.message_id:
            try:
                referenced = await message.channel.fetch_message(message.reference.message_id)
                attachments.extend(referenced.attachments)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                LOGGER.debug("Nao consegui buscar mensagem referenciada para anexos", exc_info=True)

        analyses: list[AttachmentAnalysis] = []
        seen_urls: set[str] = set()
        for attachment in attachments:
            if attachment.url in seen_urls:
                continue
            seen_urls.add(attachment.url)
            try:
                analyses.append(
                    await analyze_attachment(attachment, max_bytes=self.settings.attachment_max_bytes)
                )
            except discord.HTTPException as exc:
                LOGGER.warning("Falha baixando anexo %s: %s", attachment.filename, exc)
            except Exception:
                LOGGER.exception("Erro inesperado analisando anexo %s", attachment.filename)
        return analyses

    def save_attachment_memory(self, message: discord.Message, analyses: list[AttachmentAnalysis]) -> None:
        memory_text = format_attachment_memory(analyses)
        if not memory_text:
            return

        try:
            context = self.memory_service.context_from_message(message)
            self.memory_service.save_attachment_memory(
                context=context,
                text=memory_text,
                tags=attachment_branches(analyses),
            )
        except Exception:
            LOGGER.exception("Erro salvando memoria de anexo")

    def observe_message_memory(self, message: discord.Message) -> None:
        if not self.settings.observe_all_messages:
            return

        content = " ".join((message.content or "").split())
        if not content:
            return

        try:
            self.memory_service.save_observed_message(context=self.memory_service.context_from_message(message), text=content)
        except Exception:
            LOGGER.exception("Erro salvando mensagem observada")

    async def send_ai_reply(self, message: discord.Message, answer: str) -> None:
        clean_answer, gif_theme = strip_gif_marker(answer)
        await send_long_reply(message, clean_answer)
        theme = gif_theme or infer_gif_theme(f"{message.content} {clean_answer}")
        await self.maybe_send_gif(
            message.channel,
            theme,
            query=f"{message.content} {clean_answer}",
            force=True,
        )

    async def send_text_reply_with_gif(
        self,
        message: discord.Message,
        text: str,
        *,
        query: str = "",
        force: bool = True,
    ) -> None:
        await send_long_reply(message, text)
        await self.maybe_send_gif(
            message.channel,
            infer_gif_theme(f"{query} {text}"),
            query=f"{query} {text}",
            force=force,
        )

    async def maybe_send_gif(
        self,
        channel: discord.abc.Messageable,
        theme: str | None,
        *,
        query: str = "",
        force: bool = False,
    ) -> None:
        if not theme or not self.settings.gifs_enabled:
            return

        normalized_theme = normalize_gif_theme(theme)
        if not normalized_theme:
            return

        channel_id = getattr(channel, "id", 0)
        last_url = self.last_gif_url_by_channel.get(channel_id)
        search_query = build_gif_search_query(normalized_theme, query)
        try:
            url = await search_free_gif(
                search_query,
                self.settings.gif_search,
                exclude_url=last_url,
            )
        except Exception:
            LOGGER.exception("Falha buscando GIF gratuito na internet")
            url = None
        if not is_direct_gif_url(url):
            url = None
        if not url:
            url = choose_fallback_gif_url(normalized_theme, last_url)
        if not url:
            return

        await self.maybe_send_gif_url(channel, url, force=force)

    async def maybe_send_gif_url(self, channel: discord.abc.Messageable, url: str, *, force: bool = False) -> None:
        if not self.settings.gifs_enabled:
            return
        if not is_direct_gif_url(url):
            LOGGER.debug("GIF ignorado porque nao e URL direta .gif: %s", url)
            return

        channel_id = getattr(channel, "id", 0)
        now = time.monotonic()
        last_sent = self.last_gif_by_channel.get(channel_id, 0)
        cooldown = 0 if force else self.settings.gif_cooldown_seconds
        if cooldown and now - last_sent < cooldown:
            return

        self.last_gif_by_channel[channel_id] = now
        self.last_gif_url_by_channel[channel_id] = url
        await channel.send(url)


class ReiCommands(commands.Cog):
    def __init__(self, bot: ReiSuzukawaBot) -> None:
        self.bot = bot

    @commands.command(name="ajuda", aliases=["help", "comandos"])
    async def ajuda(self, ctx: commands.Context[ReiSuzukawaBot]) -> None:
        prefix = self.bot.settings.prefix
        text = (
            "Eu sou o Goku.\n"
            "Eu respondo quando voce fala `goku`, `kakaroto`, `rei`, `suzukawa` ou quando me menciona.\n\n"
            f"`{prefix}ping` - testa se estou vivo.\n"
            f"`{prefix}status` - mostra meu estado.\n"
            f"`{prefix}perguntar texto` - pergunta direto para a DeepSeek.\n"
            f"`{prefix}resumo` - resumo da conversa recente comigo.\n"
            f"`{prefix}resenha` - averigua a resenha do canal.\n"
            f"`{prefix}anexos` - explica quais fotos, PDFs e arquivos eu consigo ler.\n"
            f"`{prefix}codigo` - le meu proprio codigo em modo seguro, sem editar nada.\n"
            f"`{prefix}chamar @usuario assunto` - marca alguem e puxa assunto.\n"
            f"`{prefix}lembrar texto` - salva uma memoria local no SQLite.\n"
            f"`{prefix}memorias` - lista suas memorias locais recentes.\n"
            f"`{prefix}perfil` - mostra sua memoria de usuario.\n"
            f"`{prefix}memoria status` - status do novo cerebro segmentado.\n"
            f"`{prefix}memoria minha` - mostra o que lembro de voce.\n"
            f"`{prefix}memoria canal` - mostra memoria do canal.\n"
            f"`{prefix}memoria exportar` - exporta suas memorias.\n"
            f"`{prefix}cerebro` - atalho legado para o cerebro SQLite.\n"
            f"`{prefix}cerebro buscar termo` - procura memorias salvas.\n"
            f"`{prefix}cerebro ramos` - lista os ramos do cerebro.\n"
            f"`{prefix}cerebro segmentos` - lista os segmentos da memoria.\n"
            f"`{prefix}cerebro usuarios` - lista usuarios que ja conversaram comigo.\n"
            f"`{prefix}esquecer` - limpa apenas as lembrancas temporarias da sessao.\n"
            f"`{prefix}limpar` - limpa a memoria temporaria deste canal.\n\n"
            "Tambem entendo frases naturais como `me chama de...`, `sem zoeira`, "
            "`pode zoar`, `o que voce lembra de mim?` e `esquece isso`."
        )
        await ctx.reply(text, mention_author=False)

    @commands.command(name="ping")
    async def ping(self, ctx: commands.Context[ReiSuzukawaBot]) -> None:
        latency_ms = round(self.bot.latency * 1000)
        await ctx.reply(f"pong. Latencia: `{latency_ms}ms`.", mention_author=False)

    @commands.command(name="status")
    async def status(self, ctx: commands.Context[ReiSuzukawaBot]) -> None:
        deepseek_state = "ativa" if self.bot.deepseek.enabled else "sem API key"
        history_size = len(self.bot.channel_history[ctx.channel.id])
        memory_status = self.bot.memory_service.status(self.bot.memory_service.context_from_message(ctx.message))
        text = (
            f"status da {BOT_NAME}:\n"
            f"- DeepSeek: `{deepseek_state}`\n"
            f"- Modelo: `{self.bot.settings.deepseek.model}`\n"
            f"- Prefixo: `{self.bot.settings.prefix}`\n"
            f"- Memoria do canal: `{history_size}/{self.bot.settings.max_history}` mensagens\n"
            f"- SQLite: `{memory_status['total']}` memorias em `{memory_status['sqlite_path']}`\n"
            f"- FTS5: `{memory_status['fts5']}`\n"
            f"- Memorias deste usuario: `{memory_status['user']}`\n"
            f"- Memorias deste canal: `{memory_status['channel']}`\n"
            f"- Auto-memoria importante: `{self.bot.settings.auto_memory_enabled}`\n"
            f"- Observa todos os chats: `{self.bot.settings.observe_all_messages}`\n"
            f"- Interacoes naturais: `{self.bot.settings.natural_interactions.enabled}` "
            f"chance `{self.bot.settings.natural_interactions.spontaneous_reply_chance}` "
            f"cooldown `{self.bot.settings.natural_interactions.spontaneous_cooldown_seconds}s`\n"
            f"- Limite resenha: `{self.bot.settings.resenha_history_limit}` mensagens\n"
            f"- Anexos: ate `{self.bot.settings.attachment_max_bytes}` bytes por arquivo\n"
            f"- GIFs: `{self.bot.settings.gifs_enabled}` com cooldown `{self.bot.settings.gif_cooldown_seconds}s`"
        )
        await ctx.reply(text, mention_author=False)

    @commands.command(name="limpar", aliases=["resetar"])
    async def limpar(self, ctx: commands.Context[ReiSuzukawaBot]) -> None:
        self.bot.channel_history[ctx.channel.id].clear()
        await ctx.reply("limpei a memoria temporaria deste canal.", mention_author=False)

    @commands.command(name="lembrar")
    async def lembrar(self, ctx: commands.Context[ReiSuzukawaBot], *, text: str = "") -> None:
        await self._save_sqlite_memory(ctx, text)

    async def _save_sqlite_memory(self, ctx: commands.Context[ReiSuzukawaBot], text: str) -> None:
        memory = text.strip()
        if not memory:
            await ctx.reply("me diga o que e para lembrar.", mention_author=False)
            return

        record = self.bot.memory_service.save_manual_memory(
            context=self.bot.memory_service.context_from_message(ctx.message),
            text=memory,
        )
        if record is None:
            await ctx.reply("nao salvei isso porque parece sensivel ou vazio.", mention_author=False)
            return
        memories = self.bot.user_memories[ctx.author.id]
        memories.append(memory)
        del memories[:-10]
        await ctx.reply(
            f"anotado no SQLite.\nEscopo: `{record.scope_type}`\nTipo: `{record.memory_type}`\nID: `{record.id}`",
            mention_author=False,
        )

    @commands.command(name="memorias", aliases=["lembrancas"])
    async def memorias(self, ctx: commands.Context[ReiSuzukawaBot]) -> None:
        await ctx.reply(
            self.bot.memory_service.render_user_memories(self.bot.memory_service.context_from_message(ctx.message)),
            mention_author=False,
        )

    @commands.command(name="perfil", aliases=["profile", "usuario"])
    async def perfil(self, ctx: commands.Context[ReiSuzukawaBot]) -> None:
        context = self.bot.memory_service.context_from_message(ctx.message)
        await ctx.reply(self.bot.memory_service.render_user_memories(context), mention_author=False)

    @commands.command(name="esquecer")
    async def esquecer(self, ctx: commands.Context[ReiSuzukawaBot]) -> None:
        self.bot.user_memories.pop(ctx.author.id, None)
        removed = self.bot.memory_service.forget_user(self.bot.memory_service.context_from_message(ctx.message))
        await ctx.reply(
            f"limpei suas lembrancas temporarias e desativei {removed} memoria(s) locais suas.",
            mention_author=False,
        )

    @commands.command(name="perguntar", aliases=["ask"])
    async def perguntar(self, ctx: commands.Context[ReiSuzukawaBot], *, prompt: str = "") -> None:
        prompt = prompt.strip()
        if not prompt:
            await ctx.reply("manda a pergunta depois do comando.", mention_author=False)
            return

        cached_attachments = self.bot.attachment_cache.get(ctx.message.id)
        attachment_analyses = cached_attachments
        if attachment_analyses is None:
            attachment_analyses = await self.bot.collect_attachment_analyses(ctx.message)

        if attachment_analyses and cached_attachments is None:
            self.bot.save_attachment_memory(ctx.message, attachment_analyses)

        async with ctx.typing():
            answer = await self.bot.ask_deepseek(ctx.message, prompt, attachment_analyses=attachment_analyses)
        await self.bot.send_ai_reply(ctx.message, answer)

    @commands.command(name="resenha", aliases=["averiguar", "averigar"])
    async def resenha(self, ctx: commands.Context[ReiSuzukawaBot]) -> None:
        async with ctx.typing():
            answer = await self.bot.generate_channel_resenha(ctx.message)
        await self.bot.send_ai_reply(ctx.message, answer)

    @commands.command(name="anexos", aliases=["arquivos", "foto", "pdf"])
    async def anexos(self, ctx: commands.Context[ReiSuzukawaBot]) -> None:
        text = (
            "Eu leio PDF com texto, TXT, CSV, JSON, logs e tento OCR em imagens quando o sistema tiver Tesseract. "
            "Se a foto nao tiver texto legivel, eu guardo o link e os metadados, mas nao invento o que tem nela."
        )
        await ctx.reply(text, mention_author=False)

    @commands.group(name="codigo", aliases=["code", "fonte"], invoke_without_command=True)
    async def codigo(self, ctx: commands.Context[ReiSuzukawaBot]) -> None:
        prefix = self.bot.settings.prefix
        text = (
            f"{summarize_codebase(project_root())}\n\n"
            f"Use `{prefix}codigo listar` para ver arquivos ou "
            f"`{prefix}codigo arquivo rei_suzukawa/bot.py` para eu ler um arquivo seguro."
        )
        await ctx.reply(text[:1900], mention_author=False)

    @codigo.command(name="listar", aliases=["lista", "ls"])
    async def codigo_listar(self, ctx: commands.Context[ReiSuzukawaBot]) -> None:
        files = list_code_files(project_root(), limit=80)
        if not files:
            await ctx.reply("Nao achei arquivos de codigo seguros para listar.", mention_author=False)
            return
        text = "Arquivos que eu posso ler com seguranca:\n" + "\n".join(f"- `{path}`" for path in files)
        await send_long_reply(ctx.message, text)

    @codigo.command(name="arquivo", aliases=["ler", "cat", "ver"])
    async def codigo_arquivo(self, ctx: commands.Context[ReiSuzukawaBot], *, path: str = "") -> None:
        result = read_code_file(project_root(), path)
        if not result.ok:
            await ctx.reply(result.content, mention_author=False)
            return

        header = f"Arquivo `{result.path}` lido em modo somente leitura:"
        await send_long_reply(ctx.message, f"{header}\n```text\n{result.content[:1800]}\n```")
        remaining = result.content[1800:]
        while remaining:
            chunk = remaining[:1800]
            remaining = remaining[1800:]
            await ctx.channel.send(f"```text\n{chunk}\n```")

    @commands.command(name="chamar", aliases=["puxar", "marcar", "conversar"])
    async def chamar(self, ctx: commands.Context[ReiSuzukawaBot], *, text: str = "") -> None:
        targets = [user for user in ctx.message.mentions if self.bot.user is None or user.id != self.bot.user.id]
        if not targets:
            await ctx.reply("marca alguem para eu chamar. Exemplo: `!chamar @usuario fala do jogo`.", mention_author=False)
            return

        target = targets[0]
        subject = text
        for mentioned in ctx.message.mentions:
            subject = subject.replace(mentioned.mention, " ")
            subject = subject.replace(f"<@!{mentioned.id}>", " ")
        subject = " ".join(subject.split())

        async with ctx.typing():
            answer = await self.bot.generate_user_starter(ctx.message, target, subject)
        answer, gif_theme = strip_gif_marker(answer)
        await ctx.send(answer, allowed_mentions=discord.AllowedMentions(users=True, roles=False, everyone=False))
        await self.bot.maybe_send_gif(ctx.channel, gif_theme, query=subject, force=detect_gif_request(subject))

    @commands.group(name="cerebro", aliases=["brain"], invoke_without_command=True)
    async def cerebro(self, ctx: commands.Context[ReiSuzukawaBot]) -> None:
        stats = self.bot.memory_service.status(self.bot.memory_service.context_from_message(ctx.message))
        prefix = self.bot.settings.prefix
        text = (
            "meu cerebro persistente esta no SQLite local.\n"
            f"- Arquivo: `{stats['sqlite_path']}`\n"
            f"- Memorias: `{stats['total']}`\n"
            f"- FTS5: `{stats['fts5']}`\n\n"
            f"`{prefix}lembrar texto` salva memoria.\n"
            f"`{prefix}cerebro buscar termo` procura memoria.\n"
            f"`{prefix}memoria status` mostra status detalhado.\n"
            f"`{prefix}memoria minha` mostra suas memorias.\n"
            f"`{prefix}memoria canal` mostra memorias do canal.\n"
            f"`{prefix}memoria exportar` exporta suas memorias."
        )
        await ctx.reply(text, mention_author=False)

    @cerebro.command(name="salvar", aliases=["lembrar"])
    async def cerebro_salvar(self, ctx: commands.Context[ReiSuzukawaBot], *, text: str = "") -> None:
        await self._save_sqlite_memory(ctx, text)

    @cerebro.command(name="buscar", aliases=["procurar", "search"])
    async def cerebro_buscar(self, ctx: commands.Context[ReiSuzukawaBot], *, query: str = "") -> None:
        if not query.strip():
            await ctx.reply("me diga o termo para buscar no cerebro.", mention_author=False)
            return

        context = self.bot.memory_service.context_from_message(ctx.message)
        records = self.bot.memory_service.retriever.get_relevant_memories(
            guild_id=context.guild_id,
            channel_id=context.channel_id,
            user_id=context.user_id,
            current_message=query,
            limit=8,
        )
        if not records:
            await ctx.reply("nao achei nada no cerebro para essa busca.", mention_author=False)
            return

        lines = []
        for index, record in enumerate(records, start=1):
            snippet = record.content[:170]
            if len(record.content) > 170:
                snippet = f"{snippet}..."
            lines.append(f"{index}. {snippet} (`{record.scope_type}`, `{record.memory_type}`)")

        await ctx.reply("encontrei isso no SQLite:\n" + "\n".join(lines), mention_author=False)

    @cerebro.command(name="ramos", aliases=["ramificacoes"])
    async def cerebro_ramos(self, ctx: commands.Context[ReiSuzukawaBot]) -> None:
        await ctx.reply("os ramos antigos foram substituidos por escopos SQLite: global, servidor, canal, usuario e usuario+canal.", mention_author=False)

    @cerebro.command(name="segmentos", aliases=["segmento", "segments"])
    async def cerebro_segmentos(self, ctx: commands.Context[ReiSuzukawaBot]) -> None:
        stats = self.bot.memory_service.status(self.bot.memory_service.context_from_message(ctx.message))
        text = (
            "segmentos por escopo:\n"
            f"- global: `{stats['global']}`\n"
            f"- servidor: `{stats['guild']}`\n"
            f"- canal: `{stats['channel']}`\n"
            f"- usuario: `{stats['user']}`\n"
            f"- usuario+canal: `{stats['user_channel']}`"
        )
        await ctx.reply(text, mention_author=False)

    @cerebro.command(name="usuarios", aliases=["users", "pessoas"])
    async def cerebro_usuarios(self, ctx: commands.Context[ReiSuzukawaBot]) -> None:
        await ctx.reply("use `!memoria status` e `!memoria minha`; perfis agora sao separados por `user_id` no SQLite.", mention_author=False)

    @cerebro.command(name="mapa")
    async def cerebro_mapa(self, ctx: commands.Context[ReiSuzukawaBot]) -> None:
        await ctx.reply(f"mapa atual: SQLite local em `{self.bot.settings.memory.sqlite_path}`.", mention_author=False)

    @commands.command(name="resumo", aliases=["resumir"])
    async def resumo(self, ctx: commands.Context[ReiSuzukawaBot]) -> None:
        history = list(self.bot.channel_history[ctx.channel.id])
        if not history:
            await ctx.reply("ainda nao tenho conversa recente para resumir.", mention_author=False)
            return

        messages = [
            {"role": "system", "content": build_system_prompt()},
            {
                "role": "user",
                "content": (
                    "Resuma em topicos curtos a conversa recente abaixo. "
                    "Destaque decisoes, pendencias e proximos passos.\n\n"
                    f"{history}"
                ),
            },
        ]

        try:
            async with ctx.typing():
                answer = await self.bot.call_deepseek(messages)
        except DeepSeekNotConfigured:
            answer = "Falta configurar `DEEPSEEK_API_KEY` no `.env` para eu resumir com DeepSeek."
        except PromptTooLargeError:
            answer = "A conversa recente ficou grande demais para resumir com seguranca."
        except DeepSeekRequestError as exc:
            answer = f"Nao consegui resumir agora: {exc}"

        await self.bot.send_ai_reply(ctx.message, answer)


async def send_long_reply(message: discord.Message, text: str) -> None:
    chunks = chunk_text(text)
    if not chunks:
        return

    await message.reply(chunks[0], mention_author=False)
    for chunk in chunks[1:]:
        await message.channel.send(chunk)


def strip_gif_marker(text: str) -> tuple[str, str | None]:
    marker: str | None = None

    def remember(match: re.Match[str]) -> str:
        nonlocal marker
        normalized = normalize_gif_theme(match.group(1))
        if normalized:
            marker = normalized
        return " "

    clean = GIF_MARKER_PATTERN.sub(remember, text or "")
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean, marker


def normalize_gif_theme(value: str | None) -> str | None:
    if not value:
        return None
    normalized = unicodedata.normalize("NFKD", value)
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    normalized = re.sub(r"[^a-zA-Z0-9]+", "", normalized).lower()
    return GIF_THEME_ALIASES.get(normalized)


def choose_fallback_gif_url(theme: str, last_url: str | None = None) -> str | None:
    urls = GIF_URLS.get(theme)
    if not urls:
        return None
    direct_urls = [url for url in urls if is_direct_gif_url(url)]
    candidates = [url for url in direct_urls if url != last_url] or direct_urls
    if not candidates:
        return None
    return random.choice(candidates)


def infer_gif_theme(text: str) -> str:
    mode = detect_emotional_mode(text)
    if mode == "raiva":
        return "raiva"
    if mode == "conforto":
        return "conforto"
    if mode == "alegria":
        return "comemoracao"
    lowered = (text or "").lower()
    if re.search(r"\b(erro|bug|confuso|duvida|dúvida|nao entendi|não entendi|estranho|wtf)\b", lowered):
        return "confuso"
    if re.search(r"\b(consegui|vitoria|vitória|ganhei|deu certo|boa|brabo|treino|forte|forca|força)\b", lowered):
        return "comemoracao"
    if re.search(r"\b(luta|raiva|bravo|irritado|desafio|impossivel|impossível)\b", lowered):
        return "raiva"
    return "risada"


def build_gif_search_query(theme: str, user_text: str = "") -> str:
    theme_terms = {
        "risada": "funny smile reaction",
        "raiva": "power up angry fight aura super saiyan",
        "confuso": "confused reaction surprised",
        "comemoracao": "power up victory celebration kamehameha",
        "conforto": "smile friends wholesome",
    }
    goku_terms = extract_goku_gif_terms(user_text)
    goku_base = "dragon ball z goku"
    if goku_terms:
        return f"{goku_base} {theme_terms.get(theme, 'reaction')} {goku_terms}"
    return f"{goku_base} {theme_terms.get(theme, 'reaction')}"


def extract_goku_gif_terms(text: str) -> str:
    clean = (text or "").lower()
    allowed_terms = {
        "goku",
        "kakaroto",
        "kakarot",
        "super saiyan",
        "saiyan",
        "kamehameha",
        "dragon ball",
        "dragon ball z",
        "dbz",
    }
    found = [term for term in allowed_terms if re.search(rf"(?<!\w){re.escape(term)}(?!\w)", clean)]
    return " ".join(sorted(found))[:80]


def is_direct_gif_url(url: str | None) -> bool:
    if not url:
        return False
    clean = url.split("?", 1)[0].lower()
    return clean.startswith("https://") and clean.endswith(".gif")


def extract_requested_gif_url(text: str) -> str | None:
    match = GIF_LINK_PATTERN.search(text or "")
    if not match:
        return None
    return match.group(0).rstrip(".,!?)]}>")


def detect_gif_request(text: str) -> bool:
    return bool(GIF_REQUEST_PATTERN.search(text or ""))


def merge_prompt_with_attachments(prompt: str, analyses: list[AttachmentAnalysis]) -> str:
    attachment_context = format_attachment_context(analyses)
    if not attachment_context:
        return prompt
    return f"{prompt}\n\n{attachment_context}"


def append_xp_message(text: str, event: object | None) -> str:
    message = getattr(event, "message", None)
    if not message:
        return text
    return f"{text}\n\n{message}"


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _as_int(env_name: str, default: int) -> int:
    raw = os.getenv(env_name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        LOGGER.warning("%s invalido: %r. Usando %s.", env_name, raw, default)
        return default


def _as_float(env_name: str, default: float) -> float:
    raw = os.getenv(env_name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        LOGGER.warning("%s invalido: %r. Usando %s.", env_name, raw, default)
        return default


def _as_bool(env_name: str, default: bool) -> bool:
    raw = os.getenv(env_name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "sim", "yes", "on"}


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    settings = BotSettings.from_env()
    if not settings.discord_token:
        raise SystemExit("DISCORD_TOKEN nao foi configurado. Copie .env.example para .env e preencha o token.")

    bot = ReiSuzukawaBot(settings)
    async with bot:
        try:
            await bot.start(settings.discord_token)
        except discord.errors.PrivilegedIntentsRequired as exc:
            raise SystemExit(
                "O Discord recusou o bot porque o Message Content Intent nao esta ativado.\n"
                "Abra https://discord.com/developers/applications/ > sua aplicacao > Bot > "
                "Privileged Gateway Intents > ative Message Content Intent > Save Changes.\n"
                "Depois rode o bot de novo."
            ) from exc


if __name__ == "__main__":
    asyncio.run(main())
