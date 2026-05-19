import tempfile
import unittest
from pathlib import Path

from ai.deepseek_prompt_limiter import PromptBudgetConfig, PromptBudgetManager
from memory.memory_config import MemoryConfig
from memory.memory_extractor import extract_memories_from_message
from memory.memory_privacy import is_sensitive_memory, wants_no_save
from memory.memory_service import MemoryService
from memory.memory_store import build_scope_id
from memory.memory_types import MemoryContext


class SQLiteMemoryTests(unittest.TestCase):
    def test_extracts_local_memories(self) -> None:
        candidates = extract_memories_from_message("Meu projeto atual é um bot de Discord em Python.")
        self.assertTrue(candidates)
        self.assertEqual(candidates[0].memory_type, "project")
        self.assertIn("Discord", candidates[0].content)

    def test_blocks_sensitive_memory(self) -> None:
        self.assertTrue(is_sensitive_memory("minha senha e 123456"))
        self.assertTrue(wants_no_save("nao guarda isso"))
        self.assertFalse(extract_memories_from_message("guarda isso: meu token sk-12345678901234567890"))

    def test_saves_and_retrieves_by_scope_without_mixing_channels(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            service = MemoryService(MemoryConfig(sqlite_path=Path(tmp) / "memory.sqlite3"))
            try:
                estudos = MemoryContext(guild_id="1", channel_id="10", user_id="123", message_id="1", channel_name="estudos")
                memes = MemoryContext(guild_id="1", channel_id="20", user_id="123", message_id="2", channel_name="memes")
                service.save_from_user_message(context=estudos, text="Neste canal eu estou estudando limites.")
                service.save_from_user_message(context=memes, text="Neste canal eu gosto de meme de gato.")

                estudo_memories = service.retriever.get_relevant_memories(
                    guild_id="1",
                    channel_id="10",
                    user_id="123",
                    current_message="limites",
                    limit=10,
                )
                self.assertTrue(any("limites" in memory.content for memory in estudo_memories))
                self.assertFalse(any("gato" in memory.content for memory in estudo_memories if memory.scope_type == "user_channel"))
            finally:
                service.close()

    def test_manual_memory_deduplicates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            service = MemoryService(MemoryConfig(sqlite_path=Path(tmp) / "memory.sqlite3"))
            try:
                context = MemoryContext(guild_id="1", channel_id="10", user_id="123")
                service.save_manual_memory(context=context, text="eu gosto de explicacoes simples")
                service.save_manual_memory(context=context, text="eu gosto de explicacoes simples e exemplos")
                memories = service.store.list_memories(scope_type="user", scope_id=build_scope_id("user", context))
                self.assertEqual(len(memories), 1)
            finally:
                service.close()

    def test_natural_save_command_acknowledges_without_prefix(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            service = MemoryService(MemoryConfig(sqlite_path=Path(tmp) / "memory.sqlite3"))
            try:
                context = MemoryContext(guild_id="1", channel_id="10", user_id="123")
                answer = service.handle_natural_memory_command(
                    context=context,
                    text="guarda isso: eu prefiro explicacoes curtas",
                )
                self.assertEqual(answer, "Guardei isso na memoria local.")
                self.assertTrue(service.store.list_memories(user_id="123"))
            finally:
                service.close()


class PromptBudgetTests(unittest.TestCase):
    def test_limiter_reduces_giant_prompt(self) -> None:
        manager = PromptBudgetManager(
            PromptBudgetConfig(
                max_total_prompt_chars=1200,
                max_total_estimated_tokens=300,
                hard_block_if_above_chars=2000,
                hard_block_if_above_estimated_tokens=500,
                max_system_prompt_chars=500,
                max_memory_context_chars=400,
                max_recent_context_chars=300,
                max_user_message_chars=300,
            )
        )
        messages = [
            {"role": "system", "content": "persona " * 500},
            {"role": "system", "content": "[MEMORIA DO USUARIO]\n" + "\n".join(f"- memoria {i} " + "x" * 200 for i in range(30))},
            *({"role": "user", "content": "historico " * 200} for _ in range(8)),
            {"role": "user", "content": "pergunta atual " * 200},
        ]

        limited = manager.enforce(messages)

        self.assertLessEqual(sum(len(item["content"]) for item in limited), 2000)
        self.assertEqual(limited[-1]["role"], "user")


if __name__ == "__main__":
    unittest.main()
