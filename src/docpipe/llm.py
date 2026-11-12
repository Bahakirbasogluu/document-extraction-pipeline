"""The one LLM capability the pipeline needs: fill a schema from text."""

from __future__ import annotations

import os
from typing import Protocol, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class StructuredModel(Protocol):
    def parse(self, system: str, user: str, schema: type[T]) -> T: ...


class AzureOpenAIModel:
    """Structured outputs on an Azure OpenAI chat deployment."""

    def __init__(self, deployment: str | None = None):
        from openai import AzureOpenAI

        self._client = AzureOpenAI(
            azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
            api_key=os.environ["AZURE_OPENAI_API_KEY"],
            api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-10-21"),
        )
        self._deployment = deployment or os.environ["AZURE_OPENAI_DEPLOYMENT"]

    def parse(self, system: str, user: str, schema: type[T]) -> T:
        completion = self._client.beta.chat.completions.parse(
            model=self._deployment,
            temperature=0,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            response_format=schema,
        )
        message = completion.choices[0].message
        if message.parsed is None:
            raise ValueError(f"model returned no structured output: {message.refusal}")
        return message.parsed
