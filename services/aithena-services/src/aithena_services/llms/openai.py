# mypy: disable-error-code="import-untyped"
"""OpenAI Implementation based on LlamaIndex."""

# pylint: disable=too-many-ancestors, W1203
from typing import Any, Sequence

from aithena_services.config import OPENAI_KEY, TIMEOUT
from aithena_services.llms.types import Message
from aithena_services.llms.types.base import AithenaLLM, chataithena, streamchataithena
from aithena_services.llms.types.response import (
    ChatResponse,
    ChatResponseAsyncGen,
    ChatResponseGen,
)
from aithena_services.llms.utils import check_and_cast_messages
from llama_index.llms.openai import OpenAI as LlamaIndexOpenAI  # type: ignore
from openai import OpenAI as OpenAIClient
from polus.aithena.common.logger import get_logger

logger = get_logger("aithena_services.llms.openai")


def custom_sort_for_openai_models(name: str) -> tuple[int, str]:
    """Custom sort function for OpenAI models."""
    return int(name.split("-")[1].split(".")[0][0]), name  # gpt-3.5 -> (3, "gpt-3.5")


def list_openai_models() -> list:
    """List available OpenAI models."""
    if OPENAI_KEY is None:
        logger.debug(
            "OPENAI_KEY not set. listing OpenAI models, returning empty list.")
        return []
    return sorted(
        [
            x.id
            for x in OpenAIClient().models.list().data
            if "gpt" in x.id and "instruct" not in x.id
        ],
        key=custom_sort_for_openai_models,
        reverse=True,
    )


OPENAI_MODELS = list_openai_models()


class OpenAI(LlamaIndexOpenAI, AithenaLLM):
    """OpenAI models."""

    def __init__(self, timeout=TIMEOUT, **kwargs: Any):
        if "model" not in kwargs:
            raise ValueError(
                f"Model not specified. Available models: {OPENAI_MODELS}")
        if kwargs["model"] not in OPENAI_MODELS:
            raise ValueError(
                f"Model {kwargs['model']} not available. Available models: {OPENAI_MODELS}"
            )
        logger.debug(f"Initializing OpenAI chat with kwargs: {kwargs}")
        super().__init__(timeout=timeout, **kwargs)

    @staticmethod
    def list_models() -> list:
        """List available OpenAI chat models."""
        logger.debug(f"Listing OpenAI chat models")
        return list_openai_models()

    @chataithena
    def chat(self, messages: Sequence[dict | Message], **kwargs: Any) -> ChatResponse:
        """Chat with a model in OpenAI.

        Args:
            messages: entire list of message history, where last
                message is the one to be responded to
        """
        return super().chat(messages, **kwargs)  # type: ignore

    @streamchataithena
    def stream_chat(
        self, messages: Sequence[dict | Message], **kwargs: Any
    ) -> ChatResponseGen:
        """Stream chat with a model in OpenAI.

        Each response is a `ChatResponse` and has a `.delta`
        attribute useful for incremental updates.

        Args:
            messages: entire list of message history, where last
                message is the one to be responded to
        """
        return super().stream_chat(messages, **kwargs)  # type: ignore

    async def achat(
        self, messages: Sequence[dict | Message], **kwargs: Any
    ) -> ChatResponse:
        """Async chat with a model in OpenAI.

        Args:
            messages: entire list of message history, where last
                message is the one to be responded to
        """
        messages_ = check_and_cast_messages(messages)
        llama_index_response = await super().achat(messages_, **kwargs)
        return ChatResponse.from_llamaindex(llama_index_response)

    async def astream_chat(
        self, messages: Sequence[dict | Message], **kwargs: Any
    ) -> ChatResponseAsyncGen:
        """Async stream chat with a model in Azure OpenAI.

        Each response is a `ChatResponse` and has a `.delta`
        attribute useful for incremental updates.

        Args:
            messages: entire list of message history, where last
                message is the one to be responded to
        """
        messages = check_and_cast_messages(messages)
        llama_stream = super().astream_chat(messages, **kwargs)

        async def gen() -> ChatResponseAsyncGen:
            async for response in await llama_stream:
                yield ChatResponse.from_llamaindex(response)

        return gen()
