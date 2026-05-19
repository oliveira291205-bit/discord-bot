from __future__ import annotations

from dataclasses import dataclass

from openai import APIConnectionError, APIError, APITimeoutError, AsyncOpenAI, RateLimitError


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
        self._client: AsyncOpenAI | None = None
        if settings.api_key:
            self._client = AsyncOpenAI(
                api_key=settings.api_key,
                base_url=settings.base_url,
                timeout=settings.timeout,
            )

    @property
    def enabled(self) -> bool:
        return self._client is not None

    async def chat(self, messages: list[dict[str, str]]) -> str:
        if self._client is None:
            raise DeepSeekNotConfigured("DEEPSEEK_API_KEY nao foi configurada.")

        try:
            response = await self._client.chat.completions.create(
                model=self.settings.model,
                messages=messages,
                temperature=self.settings.temperature,
            )
        except RateLimitError as exc:
            raise DeepSeekRequestError("A DeepSeek limitou as requisicoes agora. Tente de novo em instantes.") from exc
        except APITimeoutError as exc:
            raise DeepSeekRequestError("A DeepSeek demorou demais para responder.") from exc
        except APIConnectionError as exc:
            raise DeepSeekRequestError("Nao consegui conectar na DeepSeek.") from exc
        except APIError as exc:
            raise DeepSeekRequestError(f"A DeepSeek retornou erro: {exc}") from exc

        if not response.choices:
            raise DeepSeekRequestError("A DeepSeek nao retornou nenhuma resposta.")

        content = response.choices[0].message.content
        if not content:
            raise DeepSeekRequestError("A DeepSeek retornou uma resposta vazia.")
        return content.strip()
