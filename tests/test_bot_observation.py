import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from ai.deepseek_prompt_limiter import PromptBudgetConfig
from features.config import FunConfig, LocalReplyConfig, XPConfig
from memory.memory_config import MemoryConfig, NaturalInteractionConfig
from rei_suzukawa.bot import BotSettings, ReiSuzukawaBot
from rei_suzukawa.deepseek import DeepSeekSettings


class ObserveAllMessagesTests(unittest.TestCase):
    def test_observe_message_memory_saves_passive_chat_message(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = BotSettings(
                discord_token="dummy",
                prefix="!",
                max_history=14,
                memory=MemoryConfig(sqlite_path=Path(tmp) / "memory.sqlite3"),
                natural_interactions=NaturalInteractionConfig(),
                fun=FunConfig(),
                xp=XPConfig(),
                local_replies=LocalReplyConfig(),
                prompt_budget=PromptBudgetConfig(),
                auto_memory_enabled=True,
                observe_all_messages=True,
                resenha_history_limit=250,
                attachment_max_bytes=1024,
                gifs_enabled=False,
                gif_cooldown_seconds=600,
                gif_search=SimpleNamespace(limit=12),
                deepseek=DeepSeekSettings(
                    api_key="",
                    base_url="https://api.deepseek.com",
                    model="deepseek-v4-flash",
                    temperature=0.55,
                ),
            )
            bot = ReiSuzukawaBot(settings)
            message = SimpleNamespace(
                id=1,
                content="Eu gosto de explicacoes passo a passo neste canal",
                author=SimpleNamespace(id=123, display_name="Alek"),
                guild=SimpleNamespace(id=456, name="Servidor"),
                channel=SimpleNamespace(id=789, name="geral"),
                jump_url="https://discord.com/channels/456/789/1",
                created_at=datetime(2026, 5, 18, 12, 0, tzinfo=timezone.utc),
            )

            bot.observe_message_memory(message)

            context = bot.memory_service.context_from_message(message)
            records = bot.memory_service.retriever.get_relevant_memories(
                guild_id=context.guild_id,
                channel_id=context.channel_id,
                user_id=context.user_id,
                current_message="passo a passo",
                limit=5,
            )
            self.assertTrue(records)
            self.assertTrue(any("passo a passo" in record.content for record in records))
            self.assertTrue(all(record.user_id == "123" for record in records))


if __name__ == "__main__":
    unittest.main()
