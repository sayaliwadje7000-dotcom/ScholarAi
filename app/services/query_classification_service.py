
from __future__ import annotations

import re

from dataclasses import dataclass

from app.schemas.query_classification import (
    AcademicTaskType,
    ClassificationEvidence,
    QueryClassification,
    QueryIntent,
)


@dataclass(frozen=True)
class IntentRule:
    """
    Defines a deterministic intent detection rule.
    """

    name: str
    patterns: tuple[str, ...]
    keywords: tuple[str, ...]
    weight: float


class QueryClassificationService:
    """
    Advanced deterministic query classification engine.

    Responsibilities:

    1. Normalize incoming queries.
    2. Detect the student's primary intent.
    3. Identify academic task type.
    4. Identify required context.
    5. Produce transparent classification evidence.
    6. Provide a suggested downstream workflow.

    This service does not execute workflows.
    """

    VERSION = "1.0.0"

    MIN_CONFIDENCE = 0.35

    INTENT_RULES = {
        QueryIntent.DOCUMENT_GROUNDED: IntentRule(
            name="document_grounded",
            patterns=(
                r"\bfrom\s+(?:my\s+)?(?:pdf|document|notes|file)\b",
                r"\bin\s+(?:my\s+)?(?:pdf|document|uploaded\s+file)\b",
                r"\bbased\s+on\s+(?:my\s+)?(?:pdf|document|notes)\b",
                r"\baccording\s+to\s+(?:my\s+)?(?:pdf|document)\b",
                r"\buploaded\s+(?:pdf|document|file)\b",
                r"\bthis\s+(?:pdf|document|file)\b",
            ),
            keywords=(
                "uploaded document",
                "uploaded pdf",
                "my pdf",
                "my notes",
                "document content",
                "document",
                "pdf",
            ),
            weight=1.0,
        ),

        QueryIntent.RESOURCE_DISCOVERY: IntentRule(
            name="resource_discovery",
            patterns=(
                r"\bfind\s+(?:me\s+)?(?:videos|tutorials|websites|courses|resources)\b",
                r"\bsearch\s+for\s+(?:videos|tutorials|courses|resources)\b",
                r"\bwhere\s+can\s+i\s+learn\b",
                r"\bfree\s+(?:courses|tutorials|learning\s+resources)\b",
                r"\beducational\s+(?:videos|websites|resources)\b",
            ),
            keywords=(
                "youtube videos",
                "learning resources",
                "educational resources",
                "tutorials",
                "courses",
                "videos",
                "websites",
            ),
            weight=0.95,
        ),

        QueryIntent.RECOMMENDATION: IntentRule(
            name="recommendation",
            patterns=(
                r"\brecommend\s+(?:me\s+)?(?:some\s+)?",
                r"\bsuggest\s+(?:me\s+)?(?:some\s+)?",
                r"\bwhat\s+should\s+i\s+(?:read|watch|learn|study)\b",
                r"\bwhich\s+(?:resource|course|book|video)\s+is\s+best\b",
                r"\bbest\s+(?:resources|courses|books|videos)\s+for\b",
            ),
            keywords=(
                "recommend",
                "recommendation",
                "suggest",
                "best resource",
                "best course",
                "personalized resources",
            ),
            weight=0.90,
        ),

        QueryIntent.STUDY_MATERIAL_GENERATION: IntentRule(
            name="study_material_generation",
            patterns=(
                r"\bgenerate\s+(?:some\s+)?(?:mcqs|questions|quiz|flashcards)\b",
                r"\bcreate\s+(?:some\s+)?(?:mcqs|questions|quiz|flashcards)\b",
                r"\bmake\s+(?:a\s+)?(?:quiz|test|practice\s+test)\b",
                r"\bprepare\s+(?:a\s+)?(?:question\s+bank|practice\s+questions)\b",
                r"\btest\s+my\s+knowledge\b",
            ),
            keywords=(
                "mcq",
                "mcqs",
                "multiple choice questions",
                "flashcards",
                "question bank",
                "practice questions",
                "quiz",
            ),
            weight=0.95,
        ),

        QueryIntent.CONVERSATION_FOLLOW_UP: IntentRule(
            name="conversation_follow_up",
            patterns=(
                r"^(?:why|how|what|when|where)\??$",
                r"^(?:explain|elaborate)\s+(?:more|that|this)\b",
                r"^(?:give|show)\s+(?:me\s+)?another\s+example\b",
                r"^(?:what|how)\s+about\s+(?:that|this|it)\b",
                r"^(?:continue|go\s+on|tell\s+me\s+more)\b",
                r"^(?:simplify|simpler|in\s+simple\s+words)\b",
            ),
            keywords=(
                "explain more",
                "another example",
                "continue",
                "tell me more",
                "what about that",
                "simplify it",
            ),
            weight=1.0,
        ),
    }

    TASK_RULES = {
        AcademicTaskType.COMPARISON: (
            r"\bcompare\b",
            r"\bdifference\s+between\b",
            r"\bdifferentiate\b",
            r"\bversus\b",
            r"\bvs\.?\b",
            r"\bsimilarities\s+and\s+differences\b",
        ),

        AcademicTaskType.PROBLEM_SOLVING: (
            r"\bsolve\b",
            r"\bcalculate\b",
            r"\bfind\s+the\s+value\b",
            r"\bderive\b",
            r"\bprove\b",
            r"\bcompute\b",
            r"\bconvert\b",
            r"\bdetermine\b",
        ),

        AcademicTaskType.SUMMARIZATION: (
            r"\bsummarize\b",
            r"\bsummarise\b",
            r"\bsummary\b",
            r"\bkey\s+points\b",
            r"\bimportant\s+points\b",
            r"\bshort\s+notes\b",
            r"\bbrief\s+notes\b",
        ),

        AcademicTaskType.QUESTION_GENERATION: (
            r"\bgenerate\s+questions\b",
            r"\bcreate\s+questions\b",
            r"\bpractice\s+questions\b",
            r"\bmcqs?\b",
            r"\bquiz\b",
            r"\bflashcards\b",
        ),

        AcademicTaskType.DEFINITION: (
            r"^\s*(?:define|what\s+is|what\s+are)\b",
            r"\bdefinition\s+of\b",
            r"\bmeaning\s+of\b",
        ),

        AcademicTaskType.EXPLANATION: (
            r"\bexplain\b",
            r"\bdescribe\b",
            r"\bhow\s+does\b",
            r"\bhow\s+do\b",
            r"\bhow\s+it\s+works\b",
            r"\bworking\s+of\b",
        ),
    }

    WORKFLOW_MAPPING = {
        QueryIntent.ACADEMIC_LEARNING:
            "academic_response",

        QueryIntent.DOCUMENT_GROUNDED:
            "document_rag",

        QueryIntent.RESOURCE_DISCOVERY:
            "resource_discovery",

        QueryIntent.RECOMMENDATION:
            "recommendation",

        QueryIntent.STUDY_MATERIAL_GENERATION:
            "study_material_generation",

        QueryIntent.CONVERSATION_FOLLOW_UP:
            "conversation_aware_response",

        QueryIntent.UNKNOWN:
            "general_chat_fallback",
    }

    def __init__(
        self,
        minimum_confidence: float = MIN_CONFIDENCE,
    ):
        if not 0.0 <= minimum_confidence <= 1.0:
            raise ValueError(
                "minimum_confidence must be between 0 and 1."
            )

        self.minimum_confidence = minimum_confidence

    @staticmethod
    def normalize_query(query: str) -> str:
        """
        Normalize query text without changing its meaning.
        """

        if not isinstance(query, str):
            raise ValueError("Query must be a string.")

        normalized = query.strip().lower()

        normalized = re.sub(
            r"\s+",
            " ",
            normalized,
        )

        if not normalized:
            raise ValueError("Query cannot be empty.")

        if len(normalized) > 5000:
            raise ValueError(
                "Query exceeds the maximum allowed length."
            )

        return normalized

    @staticmethod
    def _matches_pattern(
        query: str,
        pattern: str,
    ) -> bool:
        return re.search(
            pattern,
            query,
            flags=re.IGNORECASE,
        ) is not None

    def _score_intent(
        self,
        query: str,
        intent: QueryIntent,
    ) -> tuple[float, list[str], list[str]]:
        """
        Calculate a deterministic intent score.

        Pattern matches carry more weight than keyword matches.
        """

        rule = self.INTENT_RULES[intent]

        matched_patterns = [
            pattern
            for pattern in rule.patterns
            if self._matches_pattern(query, pattern)
        ]

        matched_keywords = [
            keyword
            for keyword in rule.keywords
            if keyword in query
        ]

        pattern_score = min(
            len(matched_patterns) * 0.55,
            1.0,
        )

        keyword_score = min(
            len(matched_keywords) * 0.25,
            0.75,
        )

        if matched_patterns:
            score = min(
                1.0,
                (
                    pattern_score * 0.75
                    + keyword_score * 0.25
                ) * rule.weight,
            )

        elif matched_keywords:
            score = min(
                0.65,
                keyword_score * rule.weight,
            )

        else:
            score = 0.0

        return (
            score,
            matched_patterns,
            matched_keywords,
        )

    def _detect_task_type(
        self,
        query: str,
    ) -> AcademicTaskType:
        """
        Detect the academic operation requested by the student.
        """

        for task_type, patterns in self.TASK_RULES.items():
            if any(
                self._matches_pattern(query, pattern)
                for pattern in patterns
            ):
                return task_type

        return AcademicTaskType.GENERAL

    def _get_task_evidence(
        self,
        query: str,
        task_type: AcademicTaskType,
    ) -> tuple[list[str], list[str]]:
        """
        Return matched task patterns and relevant query terms.
        """

        if task_type == AcademicTaskType.GENERAL:
            return [], []

        patterns = self.TASK_RULES[task_type]

        matched_patterns = [
            pattern
            for pattern in patterns
            if self._matches_pattern(query, pattern)
        ]

        matched_keywords = [
            word
            for word in query.split()
            if word.isalpha() and len(word) > 2
        ]

        return matched_patterns, matched_keywords

    def _is_follow_up_query(
        self,
        query: str,
    ) -> bool:
        """
        Determine whether the query matches a follow-up pattern.
        """

        rule = self.INTENT_RULES[
            QueryIntent.CONVERSATION_FOLLOW_UP
        ]

        return any(
            self._matches_pattern(query, pattern)
            for pattern in rule.patterns
        )

    def _detect_intent(
        self,
        query: str,
        has_conversation_context: bool,
        has_document_context: bool,
    ) -> tuple[
        QueryIntent,
        float,
        ClassificationEvidence,
        bool,
    ]:
        """
        Determine primary intent using explicit precedence.

        Precedence:
        1. Explicit document-grounded request.
        2. Context-dependent follow-up with conversation.
        3. Other recognized intents.
        4. Recognized academic task fallback.
        5. Unknown.
        """

        scores = {}

        for intent in self.INTENT_RULES:
            score, patterns, keywords = self._score_intent(
                query,
                intent,
            )

            scores[intent] = {
                "score": score,
                "patterns": patterns,
                "keywords": keywords,
            }

        # Explicit document references take priority over
        # generic follow-up phrases such as "explain this".
        if scores[QueryIntent.DOCUMENT_GROUNDED]["score"] > 0:
            selected_intent = QueryIntent.DOCUMENT_GROUNDED

        # A follow-up requires actual conversation context.
        elif self._is_follow_up_query(query):
            if not has_conversation_context:
                evidence = ClassificationEvidence(
                    matched_patterns=scores[
                        QueryIntent.CONVERSATION_FOLLOW_UP
                    ]["patterns"],
                    matched_keywords=scores[
                        QueryIntent.CONVERSATION_FOLLOW_UP
                    ]["keywords"],
                    rules_applied=[
                        "follow_up_without_conversation_context",
                        "selected_intent:unknown",
                    ],
                )

                return (
                    QueryIntent.UNKNOWN,
                    0.25,
                    evidence,
                    False,
                )

            selected_intent = (
                QueryIntent.CONVERSATION_FOLLOW_UP
            )

        else:
            # Evaluate the remaining recognized intents.
            candidates = [
                intent
                for intent in self.INTENT_RULES
                if intent not in (
                    QueryIntent.DOCUMENT_GROUNDED,
                    QueryIntent.CONVERSATION_FOLLOW_UP,
                )
                and scores[intent]["score"] > 0
            ]

            candidates.sort(
                key=lambda intent: scores[intent]["score"],
                reverse=True,
            )

            if candidates:
                selected_intent = candidates[0]

            else:
                # Recognized academic tasks must not fall through
                # to UNKNOWN merely because no primary intent
                # pattern matched.
                task_type = self._detect_task_type(query)

                if task_type != AcademicTaskType.GENERAL:
                    matched_patterns, matched_keywords = (
                        self._get_task_evidence(
                            query,
                            task_type,
                        )
                    )

                    evidence = ClassificationEvidence(
                        matched_patterns=matched_patterns,
                        matched_keywords=matched_keywords,
                        rules_applied=[
                            "academic_task_fallback",
                            "selected_intent:academic_learning",
                        ],
                    )

                    if has_conversation_context:
                        evidence.rules_applied.append(
                            "conversation_context_available"
                        )

                    if has_document_context:
                        evidence.rules_applied.append(
                            "document_context_available"
                        )

                    return (
                        QueryIntent.ACADEMIC_LEARNING,
                        0.55,
                        evidence,
                        False,
                    )

                selected_intent = QueryIntent.UNKNOWN

        selected = scores.get(
            selected_intent,
            {
                "score": 0.25,
                "patterns": [],
                "keywords": [],
            },
        )

        confidence = (
            selected["score"]
            if selected_intent != QueryIntent.UNKNOWN
            else 0.25
        )

        rules_applied = [
            f"selected_intent:{selected_intent.value}"
        ]

        if has_conversation_context:
            rules_applied.append(
                "conversation_context_available"
            )

        if has_document_context:
            rules_applied.append(
                "document_context_available"
            )

        evidence = ClassificationEvidence(
            matched_patterns=selected["patterns"],
            matched_keywords=selected["keywords"],
            rules_applied=rules_applied,
        )

        competing_scores = [
            item["score"]
            for intent, item in scores.items()
            if intent != selected_intent
            and item["score"] > 0
            and (
                intent != QueryIntent.CONVERSATION_FOLLOW_UP
                or has_conversation_context
            )
        ]

        ambiguous = (
            bool(competing_scores)
            and abs(
                confidence - max(competing_scores)
            ) < 0.10
        )

        if confidence < self.minimum_confidence:
            selected_intent = QueryIntent.UNKNOWN
            confidence = 0.25

            evidence.rules_applied.append(
                "confidence_below_minimum"
            )

        return (
            selected_intent,
            confidence,
            evidence,
            ambiguous,
        )

    def classify(
        self,
        query: str,
        has_conversation_context: bool = False,
        has_document_context: bool = False,
    ) -> QueryClassification:
        """
        Classify a student query.

        The result is metadata only. It does not execute
        the selected workflow.
        """

        normalized_query = self.normalize_query(query)

        (
            intent,
            confidence,
            evidence,
            ambiguous,
        ) = self._detect_intent(
            query=normalized_query,
            has_conversation_context=has_conversation_context,
            has_document_context=has_document_context,
        )

        task_type = self._detect_task_type(
            normalized_query
        )

        requires_conversation = (
            intent == QueryIntent.CONVERSATION_FOLLOW_UP
        )

        requires_document = (
            intent == QueryIntent.DOCUMENT_GROUNDED
            or (
                has_document_context
                and task_type == AcademicTaskType.SUMMARIZATION
            )
        )

        requires_external_resources = (
            intent == QueryIntent.RESOURCE_DISCOVERY
        )

        requires_personalization = (
            intent == QueryIntent.RECOMMENDATION
        )

        return QueryClassification(
            intent=intent,
            task_type=task_type,
            confidence=confidence,
            suggested_workflow=self.WORKFLOW_MAPPING[intent],
            requires_conversation_context=requires_conversation,
            requires_document_context=requires_document,
            requires_external_resources=requires_external_resources,
            requires_personalization=requires_personalization,
            ambiguous=ambiguous,
            evidence=evidence,
            classifier_version=self.VERSION,
        )


# Shared stateless classifier instance.
query_classification_service = QueryClassificationService()
