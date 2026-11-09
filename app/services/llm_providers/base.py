from abc import ABC, abstractmethod


class BaseLLMProvider(ABC):

    name: str

    @abstractmethod
    async def generate(
        self,
        prompt: str,
    ) -> str:
        """
        Generate a text response.

        Every provider must return a non-empty string.

        Provider-specific SDK details must remain inside
        the provider implementation.
        """

        raise NotImplementedError