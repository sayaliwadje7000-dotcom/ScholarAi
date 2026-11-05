import asyncio
import math
import random

from google import genai
from google.genai import errors, types

from app.core.embedding_config import EmbeddingSettings
from app.schemas.embeddings import (
    EmbeddingRequest,
    EmbeddingResult,
    EmbeddingTask,
)
from app.services.embeddings.base import BaseEmbeddingProvider
from app.services.embeddings.exceptions import (
    EmbeddingAuthenticationError,
    EmbeddingInputTooLargeError,
    EmbeddingProviderError,
    EmbeddingRateLimitError,
    EmbeddingTimeoutError,
    EmbeddingValidationError,
)


class GeminiEmbeddingProvider(BaseEmbeddingProvider):
    """Gemini Embedding 2 provider."""

    def __init__(
        self,
        settings: EmbeddingSettings,
        client=None,
    ):
        self.settings = settings

        if client is None:
            if not settings.api_key:
                raise EmbeddingAuthenticationError(
                    "GEMINI_API_KEY is not configured."
                )

            self.client = genai.Client(
                api_key=settings.api_key,
                http_options=types.HttpOptions(
                    timeout=int(
                        settings.request_timeout_seconds * 1000
                    ),
                    retry_options=types.HttpRetryOptions(
                        attempts=1,
                    ),
                ),
            )
        else:
            self.client = client

        self._semaphore = asyncio.Semaphore(
            settings.max_concurrent_requests
        )

    @staticmethod
    def _prepare_input(request: EmbeddingRequest) -> str:
        """Prepare model-specific retrieval instructions."""

        if request.task == EmbeddingTask.DOCUMENT:
            return f"title: none | text: {request.text}"

        if request.task == EmbeddingTask.QUERY:
            return (
                "task: search result | query: "
                f"{request.text}"
            )

        raise EmbeddingValidationError(
            "Unsupported embedding task."
        )

    @staticmethod
    def _classify_exception(exc: Exception):
        """Map SDK failures to application exceptions."""

        if isinstance(exc, (TimeoutError, asyncio.TimeoutError)):
            return EmbeddingTimeoutError

        if isinstance(exc, errors.APIError):
            status_code = exc.code
            message = (exc.message or "").lower()
            status = (exc.status or "").upper()

            if status_code in (401, 403):
                return EmbeddingAuthenticationError

            if status_code == 429:
                return EmbeddingRateLimitError

            if status_code in (408, 504):
                return EmbeddingTimeoutError

            if (
                status_code in (413,)
                or "token limit" in message
                or "input too long" in message
                or "too many tokens" in message
            ):
                return EmbeddingInputTooLargeError

            if status_code is not None and 500 <= status_code <= 599:
                return EmbeddingProviderError

            if status_code is not None and 400 <= status_code <= 499:
                return EmbeddingProviderError

            if status in ("RESOURCE_EXHAUSTED",):
                return EmbeddingRateLimitError

            if status in ("UNAUTHENTICATED", "PERMISSION_DENIED"):
                return EmbeddingAuthenticationError

        return EmbeddingProviderError

    @staticmethod
    def _is_retryable(
        error: Exception,
        original_exception: Exception,
    ) -> bool:
        """Only retry transient failures."""

        if isinstance(
            error,
            (
                EmbeddingRateLimitError,
                EmbeddingTimeoutError,
            ),
        ):
            return True

        if isinstance(original_exception, errors.ServerError):
            return True

        return False

    def _validate_vector(self, values) -> tuple[float, ...]:
        """Validate embedding dimensions and numerical integrity."""

        if values is None:
            raise EmbeddingValidationError(
                "Provider returned an empty vector."
            )

        try:
            vector = tuple(
                float(value) for value in values
            )
        except (TypeError, ValueError, OverflowError) as exc:
            raise EmbeddingValidationError(
                "Provider returned invalid vector values."
            ) from exc

        if len(vector) != self.settings.dimensions:
            raise EmbeddingValidationError(
                f"Expected {self.settings.dimensions} dimensions, "
                f"received {len(vector)}."
            )

        if not all(math.isfinite(value) for value in vector):
            raise EmbeddingValidationError(
                "Vector contains non-finite values."
            )

        return vector

    async def embed(
        self,
        request: EmbeddingRequest,
    ) -> EmbeddingResult:
        """Generate one embedding with bounded retries."""

        if len(request.text) > self.settings.max_input_characters:
            raise EmbeddingInputTooLargeError(
                "Input exceeds configured character limit."
            )

        prepared_text = self._prepare_input(request)

        async with self._semaphore:

            for attempt in range(
                self.settings.max_retries + 1
            ):
                try:
                    response = (
                        await self.client.aio.models.embed_content(
                            model=self.settings.model,
                            contents=prepared_text,
                            config=types.EmbedContentConfig(
                                output_dimensionality=(
                                    self.settings.dimensions
                                )
                            ),
                        )
                    )

                    embeddings = getattr(
                        response,
                        "embeddings",
                        None,
                    )

                    if (
                        not embeddings
                        or len(embeddings) != 1
                    ):
                        raise EmbeddingValidationError(
                            "Unexpected embedding response count."
                        )

                    vector = self._validate_vector(
                        embeddings[0].values
                    )

                    return EmbeddingResult(
                        vector=vector,
                        model=self.settings.model,
                        provider="gemini",
                        dimensions=len(vector),
                    )

                except asyncio.CancelledError:
                    raise

                except EmbeddingValidationError:
                    raise

                except Exception as exc:
                    error_type = self._classify_exception(exc)

                    error = error_type(
                        "Gemini embedding request failed."
                    )

                    if (
                        not self._is_retryable(error, exc)
                        or attempt >= self.settings.max_retries
                    ):
                        raise error from exc

                    delay = min(
                        self.settings.retry_max_delay_seconds,
                        self.settings.retry_base_delay_seconds
                        * (2 ** attempt),
                    )

                    delay *= random.uniform(0.75, 1.25)

                    await asyncio.sleep(delay)

        raise EmbeddingProviderError(
            "Embedding generation failed."
        )

    async def close(self) -> None:
        """Close the asynchronous SDK client."""

        aio_client = getattr(
            self.client,
            "aio",
            None,
        )

        if aio_client is None:
            return

        close = getattr(
            aio_client,
            "aclose",
            None,
        )

        if close is not None:
            result = close()

            if hasattr(result, "__await__"):
                await result