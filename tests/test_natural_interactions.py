import tempfile
import unittest
from pathlib import Path

from memory.memory_config import MemoryConfig, NaturalInteractionConfig
from memory.memory_service import MemoryService
from memory.memory_types import MemoryContext
from memory.natural_interactions import NaturalInteractionManager


class ZeroRng:
    def random(self) -> float:
        return 0.0

    def choice(self, values):
        return values[0]


class FakeMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class NaturalInteractionTests(unittest.TestCase):
    def test_bug_message_can_trigger_local_reply(self) -> None:
        manager = NaturalInteractionManager(
            NaturalInteractionConfig(spontaneous_reply_chance=1.0, spontaneous_cooldown_seconds=0),
            rng=ZeroRng(),
        )
        context = MemoryContext(guild_id="1", channel_id="10", user_id="123", channel_name="programacao")
        decision = manager.should_interact_naturally(
            message=FakeMessage("meu codigo quebrou com um erro estranho"),
            context=context,
            was_mentioned=False,
            triggered=False,
            is_command=False,
        )

        self.assertTrue(decision.should_reply)
        self.assertEqual(decision.tone, "bug")

    def test_serious_channel_stays_quiet(self) -> None:
        manager = NaturalInteractionManager(
            NaturalInteractionConfig(spontaneous_reply_chance=1.0, spontaneous_cooldown_seconds=0),
            rng=ZeroRng(),
        )
        context = MemoryContext(guild_id="1", channel_id="10", user_id="123", channel_name="avisos")
        decision = manager.should_interact_naturally(
            message=FakeMessage("finalmente consegui terminar"),
            context=context,
            was_mentioned=False,
            triggered=False,
            is_command=False,
        )

        self.assertFalse(decision.should_reply)

    def test_nickname_memory_is_used_naturally(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            service = MemoryService(MemoryConfig(sqlite_path=Path(tmp) / "memory.sqlite3"))
            try:
                context = MemoryContext(guild_id="1", channel_id="10", user_id="123", channel_name="geral")
                service.save_from_user_message(context=context, text="me chama de Ale")
                manager = NaturalInteractionManager(
                    NaturalInteractionConfig(spontaneous_reply_chance=1.0, spontaneous_cooldown_seconds=0),
                    rng=ZeroRng(),
                )

                reply = manager.generate_natural_interaction(
                    message=FakeMessage("finalmente consegui resolver"),
                    context=context,
                    memory_service=service,
                )

                self.assertTrue(reply.startswith("Ale,"))
            finally:
                service.close()

    def test_preference_signal_saves_no_joke(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            service = MemoryService(MemoryConfig(sqlite_path=Path(tmp) / "memory.sqlite3"))
            try:
                context = MemoryContext(guild_id="1", channel_id="10", user_id="123")
                manager = NaturalInteractionManager(NaturalInteractionConfig(), rng=ZeroRng())
                reply = manager.handle_preference_signal(
                    context=context,
                    text="fala serio agora, sem zoeira",
                    memory_service=service,
                )

                self.assertEqual(reply, "Fechado. Sem zoeira agora.")
                memories = service.store.list_memories(user_id="123")
                self.assertTrue(any("sem zoeira" in memory.content for memory in memories))
                decision = manager.should_interact_naturally(
                    message=FakeMessage("meu codigo quebrou de novo"),
                    context=context,
                    was_mentioned=False,
                    triggered=False,
                    is_command=False,
                    memory_service=service,
                )
                self.assertFalse(decision.should_reply)
            finally:
                service.close()

    def test_natural_nickname_request_gets_ack(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            service = MemoryService(MemoryConfig(sqlite_path=Path(tmp) / "memory.sqlite3"))
            try:
                context = MemoryContext(guild_id="1", channel_id="10", user_id="123")
                manager = NaturalInteractionManager(NaturalInteractionConfig(), rng=ZeroRng())
                reply = manager.handle_preference_signal(
                    context=context,
                    text="me chama de Ale",
                    memory_service=service,
                )

                self.assertEqual(reply, "Fechado, Ale.")
                self.assertTrue(any("Ale" in memory.content for memory in service.store.list_memories(user_id="123")))
            finally:
                service.close()


if __name__ == "__main__":
    unittest.main()
