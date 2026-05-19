import tempfile
import unittest
from pathlib import Path

from features.config import XPConfig
from features.error_detector import detect_error_reply
from features.local_replies import LocalReplyEngine, needs_teacher_mode
from features.status import BotStatusInfo, render_status, wants_status
from features.xp import XPService


class FeatureTests(unittest.TestCase):
    def test_detects_simple_programming_error(self) -> None:
        hint = detect_error_reply("ModuleNotFoundError: No module named 'discord'")
        self.assertIsNotNone(hint)
        self.assertIn("pip install discord.py", hint.reply)

    def test_local_reply_handles_greeting_without_ai(self) -> None:
        reply = LocalReplyEngine(enabled=True).generate("bom dia", direct=True)
        self.assertIsNotNone(reply)
        self.assertFalse(reply.needs_ai)

    def test_teacher_mode_detects_study_question(self) -> None:
        self.assertTrue(needs_teacher_mode("como faco derivada em calculo?"))

    def test_status_render_hides_secrets(self) -> None:
        text = render_status(
            BotStatusInfo(
                deepseek_enabled=True,
                memory_ok=True,
                memory_error=None,
                sqlite_path="data/memory.sqlite3",
                started_at=0,
            )
        )
        self.assertIn("DeepSeek: configurado", text)
        self.assertNotIn("sk-", text)
        self.assertTrue(wants_status("goku status"))

    def test_xp_awards_and_unlocks_achievement(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            service = XPService(Path(tmp) / "memory.sqlite3", XPConfig(cooldown_seconds=0))
            try:
                event = service.award(user_id="123", guild_id="1", reason="termux")
                self.assertIsNotNone(event)
                self.assertEqual(event.xp_added, 30)
                self.assertIn("Sobrevivente do Termux", event.achievements)
                self.assertIn("XP:", service.profile("123"))
            finally:
                service.close()


if __name__ == "__main__":
    unittest.main()
