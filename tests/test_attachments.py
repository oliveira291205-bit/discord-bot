import unittest
from dataclasses import dataclass

from rei_suzukawa.attachments import (
    analyze_attachment,
    attachment_branches,
    classify_attachment,
    format_attachment_context,
)
from rei_suzukawa.bot import (
    GIF_URLS,
    build_gif_search_query,
    detect_gif_request,
    extract_requested_gif_url,
    is_direct_gif_url,
    strip_gif_marker,
)
from rei_suzukawa.gif_search import dedupe_urls, normalize_gif_query, to_direct_gif_url


@dataclass
class FakeAttachment:
    filename: str
    content_type: str | None
    size: int
    url: str
    data: bytes

    async def read(self) -> bytes:
        return self.data


class AttachmentTests(unittest.IsolatedAsyncioTestCase):
    async def test_reads_text_attachment(self) -> None:
        attachment = FakeAttachment(
            filename="cardapio.txt",
            content_type="text/plain",
            size=24,
            url="https://cdn.example/cardapio.txt",
            data="Pizza\nSuco\nBatata".encode("utf-8"),
        )

        analysis = await analyze_attachment(attachment, max_bytes=1000)

        self.assertEqual(analysis.kind, "texto")
        self.assertIn("Pizza", analysis.extracted_text)
        self.assertIn("cardapios", attachment_branches([analysis]))
        self.assertIn("Conteudo extraido", format_attachment_context([analysis]))

    async def test_skips_large_attachment(self) -> None:
        attachment = FakeAttachment(
            filename="grande.pdf",
            content_type="application/pdf",
            size=2000,
            url="https://cdn.example/grande.pdf",
            data=b"",
        )

        analysis = await analyze_attachment(attachment, max_bytes=100)

        self.assertEqual(analysis.kind, "pdf")
        self.assertFalse(analysis.has_content)
        self.assertIn("passa do limite", analysis.note)

    def test_classifies_common_files(self) -> None:
        self.assertEqual(classify_attachment("foto.png", "image/png"), "imagem")
        self.assertEqual(classify_attachment("arquivo.pdf", None), "pdf")
        self.assertEqual(classify_attachment("lista.csv", None), "texto")

    def test_strips_gif_marker(self) -> None:
        clean, theme = strip_gif_marker("boa demais [gif:risada]")
        self.assertEqual(clean, "boa demais")
        self.assertEqual(theme, "risada")

    def test_strips_accented_gif_marker(self) -> None:
        clean, theme = strip_gif_marker("se liga nesse [gif:confusão]")
        self.assertEqual(clean, "se liga nesse")
        self.assertEqual(theme, "confuso")

    def test_extracts_requested_gif_url(self) -> None:
        url = extract_requested_gif_url("manda esse https://giphy.com/gifs/wash-5OwdXgHOhm3jW ?")
        self.assertEqual(url, "https://giphy.com/gifs/wash-5OwdXgHOhm3jW")

    def test_detects_explicit_gif_request(self) -> None:
        self.assertTrue(detect_gif_request("manda outro gif diferente"))

    def test_builds_free_gif_query(self) -> None:
        query = build_gif_search_query("confuso", "manda outro gif diferente rei")
        self.assertIn("dragon ball z goku", query)
        self.assertIn("confused reaction", query)
        self.assertNotIn("rei", query)

    def test_normalizes_free_gif_query(self) -> None:
        self.assertEqual(normalize_gif_query("manda gif bob esponja"), "dragon ball z goku bob esponja")
        self.assertEqual(normalize_gif_query("manda gif vegeta"), "dragon ball z goku vegeta")

    def test_dedupes_gif_urls(self) -> None:
        self.assertEqual(
            dedupe_urls(["https://media.giphy.com/media/a/giphy.gif", "https://media.giphy.com/media/a/giphy.gif"]),
            ["https://media.giphy.com/media/a/giphy.gif"],
        )

    def test_accepts_only_direct_gif_urls(self) -> None:
        self.assertTrue(is_direct_gif_url("https://media.giphy.com/media/a/giphy.gif"))
        self.assertFalse(is_direct_gif_url("https://giphy.com/gifs/a"))
        self.assertFalse(is_direct_gif_url("https://example.com/a.mp4"))

    def test_strips_gif_query_params(self) -> None:
        self.assertEqual(
            to_direct_gif_url("https://media.giphy.com/media/a/giphy.gif?cid=abc"),
            "https://media.giphy.com/media/a/giphy.gif",
        )

    def test_goku_fallback_gifs_are_direct(self) -> None:
        all_urls = [url for urls in GIF_URLS.values() for url in urls]
        self.assertTrue(all_urls)
        self.assertTrue(all(is_direct_gif_url(url) for url in all_urls))
        blocked_ids = {"cB7Ea7Y0Soe55gCbDd", "qs2YFQtK2IeRmUVZiG", "b5VSLKppK5VywF8SNQ", "UhcFP76fWEeGLJjEdo"}
        self.assertFalse(any(any(blocked_id in url for blocked_id in blocked_ids) for url in all_urls))


if __name__ == "__main__":
    unittest.main()
