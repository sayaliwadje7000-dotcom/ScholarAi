"""
Shared LLM generation adapter.

Provides a string-based interface to the provider router
for chat and RAG services.
"""

from app.services.llm_providers.provider_router import (
    llm_provider_router,
)


async def generate_with_provider_router(
    prompt: str,
) -> str:
    """
    Generate a response using the configured provider router.

    Returns:
        str: Generated response text.

    Raises:
        ValueError: If the prompt is invalid.
        LLMProviderError: If provider generation fails.
    """

    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("Prompt cannot be empty.")

    result = await llm_provider_router.generate(
        prompt=prompt.strip()
    )

    if not result.response or not result.response.strip():
        raise RuntimeError(
            "The configured LLM provider returned an empty response."
        )

    return result.response.strip()