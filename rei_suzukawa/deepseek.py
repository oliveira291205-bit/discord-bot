from __future__ import annotations

from dataclasses import dataclass

import httpx


class DeepSeekNotConfigured(RuntimeError):
    """Raised when the DeepSeek API key is missing."""


class DeepSeekRequestError(RuntimeError):
    """Raised when DeepSeek rejects or fails a request."""


@dataclass(frozen=True)
class DeepSeekSettings:
    api_key: str
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-v4-flash"
    temperature: float = 0.8
    timeout: float = 45.0


class DeepSeekClient:
    def __init__(self, settings: DeepSeekSettings) -> None:
        self.settings = settings

    @property
    def enabled(self) -> bool:
        return bool(self.settings.api_key)

    async def chat(self, messages: list[dict[str, str]]) -> str:
        if not self.settings.api_key:
            raise DeepSeekNotConfigured("DEEPSEEK_API_KEY nao foi configurada.")

        url = self.settings.base_url.rstrip("/") + "/chat/completions"
        payload = {
            "model": self.settings.model,
            "messages": messages,
            "temperature": self.settings.temperature,
        }
        headers = {
            "Authorization": f"Bearer {self.settings.api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self.settings.timeout) as client:
                response = await client.post(url, json=payload, headers=headers)
        except httpx.TimeoutException as exc:
            raise DeepSeekRequestError("A DeepSeek demorou demais para responder.") from exc
        except httpx.TransportError as exc:
            raise DeepSeekRequestError("Nao consegui conectar na DeepSeek.") from exc

        if response.status_code == 429:
            raise DeepSeekRequestError("A DeepSeek limitou as requisicoes agora. Tente de novo em instantes.")
        if response.status_code >= 400:
            detail = response.text[:300].strip()
            raise DeepSeekRequestError(f"A DeepSeek retornou HTTP {response.status_code}: {detail}") from None

        try:
            data = response.json()
        except ValueError as exc:
            raise DeepSeekRequestError("A DeepSeek retornou uma resposta que nao e JSON.") from exc

        choices = data.get("choices") or []
        if not choices:
            raise DeepSeekRequestError("A DeepSeek nao retornou nenhuma resposta.")

        message = choices[0].get("message") or {}
        content = message.get("content")
        if not content:
            raise DeepSeekRequestError("A DeepSeek retornou uma resposta vazia.")
        return str(content).strip()
