"""Evaluator contract shared by all ScholarAI evaluation domains."""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any


class EvaluatorType(str, Enum):
    LLM = "llm"
    RAG = "rag"
    RETRIEVAL = "retrieval"
    RECOMMENDATION = "recommendation"
    PERSONALIZATION = "personalization"
    DISCOVERY = "discovery"
    OPPORTUNITIES = "opportunities"
    CUSTOM = "custom"


class Evaluator(ABC):
    evaluator_id: str
    evaluator_type: EvaluatorType
    version: str = "1.0"

    @abstractmethod
    async def evaluate(self, payload: Any, context: Any) -> Any:
        """Evaluate supplied, explicitly labelled input without side effects."""

    def validate_input(self, payload: Any) -> None:
        """Override for domain-specific validation; reject invalid payloads."""

        if payload is None:
            raise ValueError("Evaluation payload cannot be None.")