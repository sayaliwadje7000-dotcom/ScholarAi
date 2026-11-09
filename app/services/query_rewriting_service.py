from __future__ import annotations

import re

from app.schemas.query_classification import (
    AcademicTaskType,
    QueryClassification,
    QueryIntent,
)

from app.schemas.query_rewriting import (
    QueryRewriteRequest,
    QueryRewriteResult,
    RewriteStrategy,
)

from app.services.query_classification_service import (
    query_classification_service,
)


class QueryRewritingService:
    """
    Deterministic intelligent query rewriting service.

    Responsibilities:
    1. Normalize incoming queries.
    2. Resolve context-dependent follow-up queries.
    3. Preserve document-grounded queries.
    4. Enrich academic retrieval queries.
    5. Generate bounded, deduplicated search queries.
    """

    VERSION = "1.0.0"

    MAX_SEARCH_QUERIES = 3

    TASK_EXPANSIONS = {
        AcademicTaskType.EXPLANATION:
            "concepts working mechanism examples",

        AcademicTaskType.COMPARISON:
            "similarities differences",

        AcademicTaskType.PROBLEM_SOLVING:
            "step-by-step solution",

        AcademicTaskType.SUMMARIZATION:
            "key points summary",

        AcademicTaskType.DEFINITION:
            "definition",

        AcademicTaskType.QUESTION_GENERATION:
            "practice questions",
    }

    DOCUMENT_REFERENCE_PATTERNS = (
        r"\bfrom\s+(?:my\s+)?(?:pdf|document|notes|file)\b",
        r"\bin\s+(?:my\s+)?(?:pdf|document|uploaded\s+file)\b",
        r"\bbased\s+on\s+(?:my\s+)?(?:pdf|document|notes)\b",
        r"\baccording\s+to\s+(?:my\s+)?(?:pdf|document)\b",
        r"\buploaded\s+(?:pdf|document|file)\b",
        r"\bthis\s+(?:pdf|document|file)\b",
    )

    FOLLOW_UP_PATTERNS = (
        r"^explain\s+(?:more|that|this)\.?$",
        r"^elaborate\s+(?:more|that|this)\.?$",
        r"^give\s+(?:me\s+)?another\s+example\.?$",
        r"^show\s+(?:me\s+)?another\s+example\.?$",
        r"^(?:what|how)\s+about\s+(?:that|this|it)\??$",
        r"^continue\.?$",
        r"^go\s+on\.?$",
        r"^tell\s+me\s+more\.?$",
        r"^simplify\s+(?:it|this|that)\.?$",
        r"^make\s+it\s+simpler\.?$",
        r"^in\s+simple\s+words\.?$",
        r"^(?:why|how|what|when|where)\??$",
    )

    def __init__(self):
        self.classifier = query_classification_service

    @staticmethod
    def normalize_query(query: str) -> str:

        if not isinstance(query, str):
            raise ValueError("Query must be a string.")

        normalized = re.sub(
            r"\s+",
            " ",
            query.strip(),
        )

        if not normalized:
            raise ValueError("Query cannot be empty.")

        if len(normalized) > 5000:
            raise ValueError(
                "Query exceeds the maximum allowed length."
            )

        return normalized

    @staticmethod
    def _matches_any(
        query: str,
        patterns: tuple[str, ...],
    ) -> bool:

        return any(
            re.search(
                pattern,
                query,
                flags=re.IGNORECASE,
            )
            is not None
            for pattern in patterns
        )

    @classmethod
    def _is_document_grounded(
        cls,
        query: str,
        classification: QueryClassification,
    ) -> bool:

        return (
            classification.intent == QueryIntent.DOCUMENT_GROUNDED
            or cls._matches_any(
                query,
                cls.DOCUMENT_REFERENCE_PATTERNS,
            )
        )

    @classmethod
    def _is_follow_up(cls, query: str) -> bool:

        return cls._matches_any(
            query,
            cls.FOLLOW_UP_PATTERNS,
        )

    @staticmethod
    def _resolve_contextual_query(
        query: str,
        context: str,
    ) -> str | None:

        normalized_query = query.strip().lower().rstrip(".!?")
        normalized_context = context.strip()

        if not normalized_context:
            return None

        # Simplification requests
        if normalized_query in {
            "simplify it",
            "simplify this",
            "simplify that",
            "make it simpler",
            "in simple words",
        }:
            return (
                f"Explain {normalized_context} "
                "in simpler terms"
            )

        # Explanation requests
        if normalized_query in {
            "explain more",
            "explain this",
            "explain that",
            "elaborate more",
            "elaborate this",
            "elaborate that",
            "tell me more",
        }:
            return f"Explain {normalized_context}"

        # Example requests
        if normalized_query in {
            "give another example",
            "give me another example",
            "show another example",
            "show me another example",
        }:
            return f"Give another example of {normalized_context}"

        # Continuation requests
        if normalized_query in {
            "continue",
            "go on",
        }:
            return f"Continue explaining {normalized_context}"

        # Topic-reference requests
        if normalized_query in {
            "what about this",
            "what about that",
            "what about it",
            "how about this",
            "how about that",
            "how about it",
        }:
            return f"Explain {normalized_context}"

        # Short follow-up questions
        if normalized_query in {
           "why",
           "how",
           "what",
           "when",
           "where",
}:
           original_follow_up = query.strip().rstrip(".!?")

           return (
        f"Answer the follow-up question '{original_follow_up}?' "
        f"about {normalized_context}"
    )

    @classmethod
    def _build_retrieval_query(
        cls,
        standalone_query: str,
        task_type: AcademicTaskType,
    ) -> str:

        expansion = cls.TASK_EXPANSIONS.get(task_type)

        if not expansion:
            return standalone_query

        existing_words = set(
            re.findall(
                r"\b\w+\b",
                standalone_query.lower(),
            )
        )

        expansion_words = set(
            re.findall(
                r"\b\w+\b",
                expansion.lower(),
            )
        )

        if expansion_words.issubset(existing_words):
            return standalone_query

        return f"{standalone_query} {expansion}"

    @staticmethod
    def _deduplicate_queries(
        queries: list[str],
        limit: int = 3,
    ) -> list[str]:

        results = []
        seen = set()

        for query in queries:

            cleaned = query.strip()

            if not cleaned:
                continue

            normalized = cleaned.casefold()

            if normalized in seen:
                continue

            seen.add(normalized)
            results.append(cleaned)

            if len(results) >= limit:
                break

        return results

    def rewrite(
        self,
        query: str | QueryRewriteRequest,
        conversation_context: str | None = None,
        classification: QueryClassification | None = None,
    ) -> QueryRewriteResult:

        # --------------------------------------------------
        # STEP 1: VALIDATE INPUT
        # --------------------------------------------------

        if isinstance(query, QueryRewriteRequest):

            request = query

            original_query = request.query

            conversation_context = (
                request.conversation_context
            )

            if classification is None:
                classification = request.classification

        elif isinstance(query, str):

            original_query = query

        else:

            raise ValueError(
                "Query must be a string or QueryRewriteRequest."
            )

        normalized_query = self.normalize_query(
            original_query
        )

        normalized_context = None

        if conversation_context is not None:

            if not isinstance(conversation_context, str):
                raise ValueError(
                    "Conversation context must be a string."
                )

            normalized_context = conversation_context.strip()

            if len(normalized_context) > 3000:
                raise ValueError(
                    "Conversation context exceeds "
                    "the maximum allowed length."
                )

            if not normalized_context:
                normalized_context = None

        # --------------------------------------------------
        # STEP 2: CLASSIFY QUERY
        # --------------------------------------------------

        if classification is None:

            classification = self.classifier.classify(
                query=normalized_query,
                has_conversation_context=(
                    normalized_context is not None
                ),
                has_document_context=False,
            )

        if not isinstance(
            classification,
            QueryClassification,
        ):
            raise ValueError(
                "Invalid query classification."
            )

        # --------------------------------------------------
        # STEP 3: INITIALIZE REWRITE STATE
        # --------------------------------------------------

        standalone_query = normalized_query
        retrieval_query = normalized_query

        strategy = RewriteStrategy.UNCHANGED

        context_used = False

        reason = "No rewriting was required."

        is_document_query = self._is_document_grounded(
            normalized_query,
            classification,
        )

        # --------------------------------------------------
        # STEP 4: DOCUMENT QUERY PRESERVATION
        # --------------------------------------------------

        if is_document_query:

            strategy = RewriteStrategy.UNCHANGED

            reason = (
                "Explicit document-grounded query preserved "
                "for document retrieval."
            )

        # --------------------------------------------------
        # STEP 5: CONTEXTUAL QUERY RESOLUTION
        # --------------------------------------------------

        elif (
            normalized_context is not None
            and self._is_follow_up(normalized_query)
        ):

            resolved_query = self._resolve_contextual_query(
                query=normalized_query,
                context=normalized_context,
            )

            if resolved_query:

                standalone_query = resolved_query

                retrieval_query = resolved_query

                strategy = RewriteStrategy.CONTEXT_RESOLVED

                context_used = True

                reason = (
                    "Resolved a context-dependent follow-up "
                    "using conversation context."
                )

        # --------------------------------------------------
        # STEP 6: NORMALIZATION
        # --------------------------------------------------

        elif normalized_query != original_query:

            strategy = RewriteStrategy.NORMALIZED

            reason = (
                "Normalized query whitespace without "
                "changing its meaning."
            )

        # --------------------------------------------------
        # STEP 7: TASK-SPECIFIC ENRICHMENT
        # --------------------------------------------------

        if (
            not is_document_query
            and strategy != RewriteStrategy.CONTEXT_RESOLVED
        ):

            enriched_query = self._build_retrieval_query(
                standalone_query=standalone_query,
                task_type=classification.task_type,
            )

            if enriched_query != standalone_query:

                retrieval_query = enriched_query

                strategy = RewriteStrategy.TASK_ENRICHED

                reason = (
                    "Added task-specific retrieval terms "
                    "to improve academic search relevance."
                )

        # --------------------------------------------------
        # STEP 8: BUILD SEARCH QUERIES
        # --------------------------------------------------

        search_queries = self._deduplicate_queries(
            [
                standalone_query,
                retrieval_query,
            ],
            limit=self.MAX_SEARCH_QUERIES,
        )

        # --------------------------------------------------
        # STEP 9: BUILD RESULT
        # --------------------------------------------------

        rewritten = (
            standalone_query != original_query
            or retrieval_query != original_query
        )

        return QueryRewriteResult(
            original_query=original_query,
            normalized_query=normalized_query,
            standalone_query=standalone_query,
            retrieval_query=retrieval_query,
            search_queries=search_queries,
            strategy=strategy,
            rewritten=rewritten,
            context_used=context_used,
            reason=reason,
            classifier_version=classification.classifier_version,
        )


query_rewriting_service = QueryRewritingService()