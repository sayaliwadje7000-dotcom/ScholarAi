from __future__ import annotations

from app.schemas.adaptive_recommendations import (
    AdaptationMode,
    AdaptationReason,
    AdaptiveRecommendationPolicy,
)


class AdaptivePolicyEngine:
    """
    Selects a personalization mode from the confidence and evidence
    summaries produced by PersonalizedContextEngine.

    This is a policy-selection component, not a recommendation scorer.
    """

    PROFILE_CONFIDENCE_THRESHOLD = 0.40
    BEHAVIOR_CONFIDENCE_THRESHOLD = 0.45
    FEEDBACK_CONFIDENCE_THRESHOLD = 0.50

    def build_policy(self, context) -> AdaptiveRecommendationPolicy:
        confidence = context.confidence
        behavioral = context.behavioral_evidence
        feedback = context.feedback_evidence
        learning_context = context.recommendation_context.learning_context

        profile_confidence = self._bounded(
            confidence.profile_confidence
        )
        behavioral_confidence = self._bounded(
            confidence.behavioral_confidence
        )
        feedback_confidence = self._bounded(
            confidence.feedback_confidence
        )
        overall_confidence = self._bounded(
            confidence.overall_confidence
        )

        has_profile = bool(
            learning_context.preferred_subjects
            or learning_context.learning_goals
            or learning_context.preferred_language
            or learning_context.education_level
        )

        has_behavior = behavioral.total_signals > 0
        has_feedback = feedback.total_feedback > 0

        reasons: list[AdaptationReason] = []

        if context.goals:
            reasons.append(AdaptationReason.ACTIVE_LEARNING_GOALS)

        if learning_context.preferred_subjects:
            reasons.append(
                AdaptationReason.EXPLICIT_SUBJECT_PREFERENCES
            )

        if has_behavior:
            reasons.append(AdaptationReason.BEHAVIORAL_EVIDENCE)

        if has_feedback:
            reasons.append(AdaptationReason.EXPLICIT_FEEDBACK)

        if confidence.is_sparse:
            reasons.append(AdaptationReason.SPARSE_EVIDENCE)

        if not has_profile and not has_behavior and not has_feedback:
            reasons.append(
                AdaptationReason.INSUFFICIENT_PERSONALIZATION_DATA
            )

        if (
            has_profile
            and has_behavior
            and has_feedback
            and behavioral_confidence
            >= self.BEHAVIOR_CONFIDENCE_THRESHOLD
            and feedback_confidence
            >= self.FEEDBACK_CONFIDENCE_THRESHOLD
        ):
            mode = AdaptationMode.FULL_PERSONALIZATION

        elif (
            has_feedback
            and feedback_confidence
            >= self.FEEDBACK_CONFIDENCE_THRESHOLD
        ):
            mode = AdaptationMode.FEEDBACK_GUIDED

        elif (
            has_behavior
            and behavioral_confidence
            >= self.BEHAVIOR_CONFIDENCE_THRESHOLD
        ):
            mode = AdaptationMode.BEHAVIOR_GUIDED

        elif (
            has_profile
            and profile_confidence
            >= self.PROFILE_CONFIDENCE_THRESHOLD
        ):
            mode = AdaptationMode.PROFILE_GUIDED

        else:
            mode = AdaptationMode.COLD_START

        # Explicit profile information remains available even when
        # behavioral and feedback evidence are sparse.
        raw_weights = {
            "profile": profile_confidence if has_profile else 0.0,
            "behavior": (
                behavioral_confidence if has_behavior else 0.0
            ),
            "feedback": (
                feedback_confidence if has_feedback else 0.0
            ),
        }

        total = sum(raw_weights.values())

        if total > 0:
            normalized = {
                key: value / total
                for key, value in raw_weights.items()
            }
        else:
            normalized = {
                "profile": 0.0,
                "behavior": 0.0,
                "feedback": 0.0,
            }

        return AdaptiveRecommendationPolicy(
            mode=mode,
            profile_weight=normalized["profile"],
            behavioral_weight=normalized["behavior"],
            feedback_weight=normalized["feedback"],
            evidence_confidence=overall_confidence,
            reasons=tuple(dict.fromkeys(reasons)),
        )

    @staticmethod
    def _bounded(value) -> float:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return 0.0

        if number != number:
            return 0.0

        return max(0.0, min(1.0, number))