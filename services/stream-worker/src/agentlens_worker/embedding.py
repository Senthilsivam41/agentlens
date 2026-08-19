"""Metered OpenAI embedding adapter."""

from __future__ import annotations

from openai import AsyncOpenAI


class OpenAIEmbeddingClient:
    def __init__(
        self,
        *,
        api_key: str,
        model: str = "text-embedding-3-small",
        base_url: str | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("OpenAI API key is required for semantic scoring")
        if base_url:
            self._client = AsyncOpenAI(
                api_key=api_key,
                base_url=base_url,
                max_retries=3,
                timeout=20,
            )
        else:
            self._client = AsyncOpenAI(api_key=api_key, max_retries=3, timeout=20)
        self._model = model

    async def embed(self, values: list[str]) -> list[list[float]]:
        if not values:
            return []
        response = await self._client.embeddings.create(model=self._model, input=values)
        ordered = sorted(response.data, key=lambda item: item.index)
        return [item.embedding for item in ordered]
