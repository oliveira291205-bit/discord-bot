from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from features.activation import should_respond_to_message
from features.config import GifConfig, WakeWordConfig
from features.gif_reactions import GifReactionManager
from features.member_index import MemberDirectory, clean_member_query, extract_member_request


class ActivationTests(unittest.TestCase):
    def test_wake_words_activate(self) -> None:
        bot = SimpleNamespace(id=99)
        channel = SimpleNamespace(id=1)
        author = SimpleNamespace(id=2)
        for text in ("Goku, oi", "Cacaroto ajuda", "Kakaroto resolve"):
            message = SimpleNamespace(content=text, mentions=[], channel=channel, author=author, reference=None)
            self.assertTrue(
                should_respond_to_message(message, bot_user=bot, config=WakeWordConfig()).should_respond,
                text,
            )

    def test_stays_quiet_without_wake_word(self) -> None:
        message = SimpleNamespace(
            content="fala serio",
            mentions=[],
            channel=SimpleNamespace(id=1),
            author=SimpleNamespace(id=2),
            reference=None,
        )
        decision = should_respond_to_message(message, bot_user=SimpleNamespace(id=99), config=WakeWordConfig())
        self.assertFalse(decision.should_respond)

    def test_direct_mention_activates(self) -> None:
        bot = SimpleNamespace(id=99)
        message = SimpleNamespace(
            content="<@99> fala serio",
            mentions=[bot],
            channel=SimpleNamespace(id=1),
            author=SimpleNamespace(id=2),
            reference=None,
        )
        self.assertTrue(should_respond_to_message(message, bot_user=bot, config=WakeWordConfig()).should_respond)

    def test_reply_to_bot_activates(self) -> None:
        bot = SimpleNamespace(id=99)
        replied = SimpleNamespace(author=bot)
        message = SimpleNamespace(
            content="continua",
            mentions=[],
            channel=SimpleNamespace(id=1),
            author=SimpleNamespace(id=2),
            reference=SimpleNamespace(resolved=replied),
        )
        self.assertTrue(should_respond_to_message(message, bot_user=bot, config=WakeWordConfig()).should_respond)


class MemberDirectoryTests(unittest.TestCase):
    def test_normalizes_names_without_accent(self) -> None:
        self.assertEqual(clean_member_query("@Cauã"), "caua")

    def test_resolves_member_by_username_display_name_and_nick(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = MemberDirectory(Path(tmp) / "memory.sqlite3")
            guild_id = "10"
            member = SimpleNamespace(
                id=123,
                name="caua_dev",
                global_name="Caua Global",
                display_name="Cauã Silva",
                nick="Caua",
                discriminator="0",
                mention="<@123>",
                bot=False,
                joined_at=None,
            )
            directory.upsert_member(guild_id, member)

            self.assertEqual(directory.resolve_member(guild_id, "caua").member.user_id, "123")
            self.assertEqual(directory.resolve_member(guild_id, "Cauã Silva").member.user_id, "123")
            self.assertEqual(directory.resolve_member(guild_id, "caua_dev").member.user_id, "123")
            directory.close()

    def test_detects_ambiguous_members(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = MemberDirectory(Path(tmp) / "memory.sqlite3")
            guild_id = "10"
            for user_id, display_name in (("1", "Caua Silva"), ("2", "Caua Dev")):
                directory.upsert_member(
                    guild_id,
                    SimpleNamespace(
                        id=int(user_id),
                        name=display_name.lower().replace(" ", "_"),
                        global_name=display_name,
                        display_name=display_name,
                        nick=None,
                        discriminator="0",
                        mention=f"<@{user_id}>",
                        bot=False,
                        joined_at=None,
                    ),
                )

            self.assertEqual(directory.resolve_member(guild_id, "caua").status, "ambiguous")
            directory.close()

    def test_extract_member_request_and_blocks_everyone(self) -> None:
        self.assertEqual(extract_member_request("marca o Cauã")[0], "caua")
        self.assertEqual(extract_member_request("marca todo mundo")[1], "blocked")


class GifReactionTests(unittest.TestCase):
    def test_gif_chance_and_cooldown(self) -> None:
        manager = GifReactionManager(GifConfig(gif_reply_chance=1.0, cooldown_seconds=300))
        self.assertTrue(manager.should_send_gif(channel_id=1, user_id=2, text="Goku consegui", now=1000))
        manager.record(channel_id=1, user_id=2, url="https://example.com/a.gif", now=1000)
        self.assertFalse(manager.should_send_gif(channel_id=1, user_id=2, text="Goku consegui", now=1100))

    def test_no_gif_in_serious_mode(self) -> None:
        manager = GifReactionManager(GifConfig(gif_reply_chance=1.0))
        self.assertFalse(manager.should_send_gif(channel_id=1, user_id=2, text="Goku sem zoeira, assunto serio", now=1))


if __name__ == "__main__":
    unittest.main()
