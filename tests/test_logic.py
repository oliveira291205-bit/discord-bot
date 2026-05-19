import unittest

from rei_suzukawa.logic import (
    build_system_prompt,
    chunk_text,
    clean_user_prompt,
    detect_emotional_mode,
    detect_resenha_trigger,
    detect_trigger,
    is_friend_bot_name,
)


class TriggerTests(unittest.TestCase):
    def test_detects_wake_words(self) -> None:
        self.assertTrue(detect_trigger("fala goku"))
        self.assertTrue(detect_trigger("kakaroto resolve isso"))
        self.assertTrue(detect_trigger("fala rei"))
        self.assertTrue(detect_trigger("Suzukawa resolve isso"))

    def test_does_not_detect_inside_other_words(self) -> None:
        self.assertFalse(detect_trigger("reinado"))
        self.assertFalse(detect_trigger("suzukawada"))
        self.assertFalse(detect_trigger("gokuzinho"))

    def test_clean_user_prompt_removes_trigger_and_mention(self) -> None:
        self.assertEqual(clean_user_prompt("<@123> rei me ajuda", 123), "me ajuda")
        self.assertEqual(clean_user_prompt("<@!123> goku ping", 123), "ping")

    def test_detects_resenha_trigger(self) -> None:
        self.assertTrue(detect_resenha_trigger("averigar resenha"))
        self.assertTrue(detect_resenha_trigger("pode averiguar resenha aqui?"))
        self.assertFalse(detect_resenha_trigger("resenha normal"))

    def test_detects_friend_bot_name(self) -> None:
        self.assertTrue(is_friend_bot_name("Yui"))
        self.assertTrue(is_friend_bot_name(" yui "))
        self.assertTrue(is_friend_bot_name("Yui Bot"))
        self.assertFalse(is_friend_bot_name("outro bot"))

    def test_prompt_uses_goku_persona(self) -> None:
        prompt = build_system_prompt()
        self.assertIn("Voce e Goku", prompt)
        self.assertIn("heroi guerreiro adulto de anime shounen", prompt)
        self.assertIn("sem copiar falas exatas", prompt)
        self.assertIn("bot chamada Yui", prompt)
        self.assertIn("conversar com qualquer usuario", prompt)
        self.assertIn("Nao diga que e IA", prompt)
        self.assertIn("conversa casual deve ter 1 frase curta", prompt)
        self.assertIn("Respostas normais devem ter no maximo 2 frases", prompt)
        self.assertIn("Regra de organizacao", prompt)
        self.assertIn("Nao misture varios assuntos na mesma frase", prompt)
        self.assertIn("nao encerre a resposta com palavra pela metade", prompt)


class ChunkTextTests(unittest.TestCase):
    def test_chunks_are_under_limit(self) -> None:
        chunks = chunk_text("x" * 50, limit=10)
        self.assertTrue(chunks)
        self.assertTrue(all(len(chunk) <= 10 for chunk in chunks))
        self.assertEqual("".join(chunks), "x" * 50)

    def test_empty_text_returns_empty_list(self) -> None:
        self.assertEqual(chunk_text("   "), [])


class EmotionTests(unittest.TestCase):
    def test_detects_comfort_before_other_modes(self) -> None:
        self.assertEqual(detect_emotional_mode("to triste kkk"), "conforto")

    def test_detects_anger(self) -> None:
        self.assertEqual(detect_emotional_mode("que bug irritante"), "raiva")

    def test_detects_joy(self) -> None:
        self.assertEqual(detect_emotional_mode("boa kkk deu certo"), "alegria")


if __name__ == "__main__":
    unittest.main()
