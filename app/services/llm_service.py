"""
LLM service module.

Provides a reusable, provider-agnostic service for generating structured LLM outputs.
Agents use this service to send prompts and receive parsed Pydantic model instances.
"""
import logging
import os

from typing import TypeVar, Type
from pydantic import BaseModel
from langchain_nvidia_ai_endpoints import ChatNVIDIA

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class LLMService:
    """
    Reusable LLM service for generating structured outputs.

    Reads configuration from environment variables and exposes a single
    public method for prompt-to-Pydantic-model generation.
    """

    def __init__(self) -> None:
        """
        Initialize the LLMService.

        Reads NVIDIA_API_KEY (or LLM_API_KEY as fallback), LLM_MODEL, and optionally 
        LLM_PROVIDER from environment variables to configure the underlying chat model.

        Raises:
            EnvironmentError: If neither NVIDIA_API_KEY nor LLM_API_KEY are set, or if LLM_MODEL is not set.
        """
        api_key = os.getenv("NVIDIA_API_KEY") or os.getenv("LLM_API_KEY")
        model = os.getenv("LLM_MODEL")
        provider = os.getenv("LLM_PROVIDER")

        if not api_key:
            raise EnvironmentError("NVIDIA_API_KEY or LLM_API_KEY environment variable is not set.")
        if not model:
            raise EnvironmentError("LLM_MODEL environment variable is not set.")

        self._model_name = model

        kwargs: dict = {
            "model": model,
            "api_key": api_key,
            "temperature": 0.2,
            "top_p": 0.7,
            "max_tokens": 1024,
            "timeout": 120,
        }

        if provider:
            kwargs["base_url"] = provider

        self._chat_model = ChatNVIDIA(**kwargs)

        logger.info("LLMService initialized with NVIDIA model: %s", self._model_name)

    def generate_structured_output(
        self,
        prompt: str,
        response_model: Type[T],
    ) -> T:
        """
        Send a prompt to the LLM and parse the response into a Pydantic model.

        Args:
            prompt: The formatted prompt string to send to the LLM.
            response_model: The Pydantic BaseModel class to parse the LLM response into.

        Returns:
            A populated instance of the supplied Pydantic model.

        Raises:
            ValueError: If the LLM response cannot be parsed into the expected model.
            Exception: Any underlying LangChain or network error propagates as-is.
        """
        logger.info(
            "Generating structured output using model '%s' for schema '%s'.",
            self._model_name,
            response_model.__name__,
        )

        try:
            structured_model = self._chat_model.with_structured_output(response_model)
            result = structured_model.invoke(prompt)
        except Exception as exc:
            logger.error(
                "Generation failed for schema '%s': %s",
                response_model.__name__,
                exc,
            )
            raise

        if not isinstance(result, response_model):
            raise ValueError(
                f"LLM response could not be parsed into '{response_model.__name__}'. "
                f"Received type: {type(result).__name__}."
            )

        logger.info(
            "Successfully generated structured output for schema '%s'.",
            response_model.__name__,
        )

        return result
