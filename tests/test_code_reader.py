from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from features.code_reader import list_code_files, read_code_file, summarize_codebase


class CodeReaderTests(unittest.TestCase):
    def test_lists_safe_project_files(self) -> None:
        root = Path(__file__).resolve().parent.parent
        files = list_code_files(root)
        self.assertIn("rei_suzukawa/bot.py", files)
        self.assertNotIn(".env", files)

    def test_summarizes_codebase(self) -> None:
        root = Path(__file__).resolve().parent.parent
        summary = summarize_codebase(root)
        self.assertIn("modo seguro", summary)
        self.assertIn("nao altero arquivo nenhum", summary)

    def test_reads_safe_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "demo.py").write_text("print('ok')\n", encoding="utf-8")

            result = read_code_file(root, "demo.py")

            self.assertTrue(result.ok)
            self.assertEqual(result.path, "demo.py")
            self.assertIn("print", result.content)

    def test_rejects_env_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".env").write_text("TOKEN=secret\n", encoding="utf-8")

            result = read_code_file(root, ".env")

            self.assertFalse(result.ok)
            self.assertIn("seguranca", result.content)

    def test_rejects_path_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            result = read_code_file(root, "../fora.py")

            self.assertFalse(result.ok)
            self.assertIn("sair da pasta", result.content)


if __name__ == "__main__":
    unittest.main()
