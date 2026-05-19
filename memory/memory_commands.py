from __future__ import annotations

import discord
from discord.ext import commands

from .memory_service import MemoryService


class MemoryCommands(commands.Cog):
    def __init__(self, bot: commands.Bot, service: MemoryService) -> None:
        self.bot = bot
        self.service = service

    @commands.group(name="memoria", aliases=["memória", "memory"], invoke_without_command=True)
    async def memoria(self, ctx: commands.Context) -> None:
        await self.status(ctx)

    @memoria.command(name="status")
    async def status(self, ctx: commands.Context) -> None:
        memory_context = self.service.context_from_message(ctx.message)
        status = self.service.status(memory_context)
        text = (
            "memoria SQLite:\n"
            f"- ativa: `{status['enabled']}`\n"
            f"- arquivo: `{status['sqlite_path']}`\n"
            f"- FTS5: `{status['fts5']}`\n"
            f"- total: `{status['total']}`\n"
            f"- global: `{status['global']}`\n"
            f"- servidor: `{status['guild']}`\n"
            f"- canal: `{status['channel']}`\n"
            f"- usuario: `{status['user']}`\n"
            f"- usuario+canal: `{status['user_channel']}`"
        )
        await ctx.reply(text, mention_author=False)

    @memoria.command(name="minha")
    async def minha(self, ctx: commands.Context) -> None:
        await ctx.reply(self.service.render_user_memories(self.service.context_from_message(ctx.message)), mention_author=False)

    @memoria.command(name="canal")
    async def canal(self, ctx: commands.Context) -> None:
        if not has_manage_messages(ctx):
            await ctx.reply("esse comando de canal e para moderador/admin.", mention_author=False)
            return
        await ctx.reply(self.service.render_channel_memories(self.service.context_from_message(ctx.message)), mention_author=False)

    @memoria.command(name="servidor")
    async def servidor(self, ctx: commands.Context) -> None:
        if not has_admin(ctx):
            await ctx.reply("esse comando de servidor e para admin.", mention_author=False)
            return
        await ctx.reply(self.service.render_guild_memories(self.service.context_from_message(ctx.message)), mention_author=False)

    @memoria.command(name="esquecer_minha")
    async def esquecer_minha(self, ctx: commands.Context) -> None:
        removed = self.service.forget_user(self.service.context_from_message(ctx.message))
        await ctx.reply(f"desativei {removed} memoria(s) suas.", mention_author=False)

    @memoria.command(name="esquecer_canal")
    async def esquecer_canal(self, ctx: commands.Context) -> None:
        if not has_manage_messages(ctx):
            await ctx.reply("so moderador/admin pode limpar memoria de canal.", mention_author=False)
            return
        removed = self.service.forget_channel(self.service.context_from_message(ctx.message))
        await ctx.reply(f"desativei {removed} memoria(s) deste canal.", mention_author=False)

    @memoria.command(name="esquecer_servidor")
    async def esquecer_servidor(self, ctx: commands.Context) -> None:
        if not has_admin(ctx):
            await ctx.reply("so admin pode limpar memoria do servidor.", mention_author=False)
            return
        removed = self.service.forget_guild(self.service.context_from_message(ctx.message))
        await ctx.reply(f"desativei {removed} memoria(s) deste servidor.", mention_author=False)

    @memoria.command(name="exportar")
    async def exportar(self, ctx: commands.Context) -> None:
        data = self.service.export_user_memories(self.service.context_from_message(ctx.message))
        if len(data) <= 1800:
            await ctx.reply(f"```json\n{data}\n```", mention_author=False)
            return
        file = discord.File(fp=to_bytes_file(data), filename="minhas_memorias.json")
        await ctx.reply("exportei suas memorias em JSON.", file=file, mention_author=False)

    @memoria.command(name="debug")
    async def debug(self, ctx: commands.Context, *, text: str = "") -> None:
        if not has_admin(ctx):
            await ctx.reply("debug de memoria e restrito.", mention_author=False)
            return
        context = self.service.context_from_message(ctx.message)
        await ctx.reply(self.service.debug_memories(context, text or ctx.message.content), mention_author=False)


def has_admin(ctx: commands.Context) -> bool:
    permissions = getattr(getattr(ctx, "author", None), "guild_permissions", None)
    return bool(getattr(permissions, "administrator", False))


def has_manage_messages(ctx: commands.Context) -> bool:
    permissions = getattr(getattr(ctx, "author", None), "guild_permissions", None)
    return bool(getattr(permissions, "administrator", False) or getattr(permissions, "manage_messages", False))


def to_bytes_file(text: str):
    import io

    return io.BytesIO(text.encode("utf-8"))
