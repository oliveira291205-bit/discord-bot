from __future__ import annotations

import html
import random
import re
from dataclasses import dataclass
from urllib.parse import quote

import httpx


GIPHY_SEARCH_URL = "https://giphy.com/search/{query}"
GIPHY_MEDIA_PATTERN = re.compile(
    r"https://media\d*\.giphy\.com/media/[^\"'\\<>\s]+?/(?:giphy|200)\.gif(?:\?[^\"'\\<>\s]*)?",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class GifSearchSettings:
    limit: int = 12


async def search_free_gif(
    query: str,
    settings: GifSearchSettings,
    *,
    exclude_url: str | None = None,
) -> str | None:
    clean_query = normalize_gif_query(query)
    if not clean_query:
        return None

    urls = await scrape_giphy_web(clean_query, limit=settings.limit)
    candidates = [url for url in urls if url != exclude_url] or urls
    if not candidates:
        return None
    return random.choice(candidates)


async def scrape_giphy_web(query: str, *, limit: int) -> list[str]:
    url = GIPHY_SEARCH_URL.format(query=quote(query.replace(" ", "-")))
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/125 Safari/537.36"
        )
    }
    async with httpx.AsyncClient(timeout=10, follow_redirects=True, headers=headers) as client:
        response = await client.get(url)
        response.raise_for_status()
        body = html.unescape(response.text)

    urls = [to_direct_gif_url(url) for url in GIPHY_MEDIA_PATTERN.findall(body)]
    urls = [url for url in urls if url.endswith(".gif") and not url.endswith("/giphy_s.gif")]
    return dedupe_urls(urls)[:limit]


def normalize_gif_query(query: str) -> str:
    clean = re.sub(r"https?://\S+", " ", query or "")
    clean = re.sub(r"<@!?\d+>", " ", clean)
    clean = re.sub(
        r"\b(rei|suzukawa|manda|mandar|envia|enviar|gif|gifs|outro|diferente|por favor)\b",
        " ",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(r"\s+", " ", clean).strip()
    if not re.search(r"\bgoku|kakaroto|kakarot\b", clean, flags=re.IGNORECASE):
        clean = f"dragon ball z goku {clean}".strip()
    else:
        clean = f"dragon ball z goku {clean}".strip()
    return clean[:120] or "dragon ball z goku reaction"


def to_direct_gif_url(url: str) -> str:
    return (url or "").split("?", 1)[0].strip()


def dedupe_urls(urls: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for url in urls:
        clean = url.strip()
        if not clean or clean in seen:
            continue
        seen.add(clean)
        unique.append(clean)
    return unique
