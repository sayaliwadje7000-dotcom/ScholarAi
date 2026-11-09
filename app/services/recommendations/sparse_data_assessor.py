from __future__ import annotations

from app.schemas.sparse_data import (
    ColdStartPolicy,
    ColdStartStrategy,
    SparseDataAssessment,
    SparseDataLevel,
    SparseDataReason,
    SparseEvidenceSummary,
)


class SparseDataAssessor:
    """
    Evaluates personalization evidence and selects a safe
    cold-start or sparse-data strategy.

    The assessor distinguishes:

    - Explicit profile information
    - Behavioral interaction evidence
    - Explicit recommendation feedback

    Missing evidence is never treated as negative evidence.
    """

    MIN_BEHAVIORAL_SIGNALS = 5
    MIN_FEEDBACK_EVENTS = 3
    MIN_TOTAL_EVIDENCE = 8

    MIN_PROFILE_CONFIDENCE = 0.40
    MIN_BEHAVIORAL_CONFIDENCE = 0.45
    MIN_FEEDBACK_CONFIDENCE = 0.50
    MIN_OVERALL_CONFIDENCE = 0.50

    def assess(self, context) -> SparseDataAssessment:
        if context is None:
            raise ValueError(
                "personalized learning context is required"
            )

        evidence = self._build_evidence_summary(context)

        data_level = self._classify_data_level(evidence)

        policy = self._build_policy(
            evidence=evidence,
            data_level=data_level,
        )

        warnings = self._build_warnings(
            evidence=evidence,
            data_level=data_level,
        )

        return SparseDataAssessment(
            data_level=data_level,
            evidence=evidence,
            policy=policy,
            is_cold_start=data_level in {
                SparseDataLevel.NO_DATA,
                SparseDataLevel.COLD_START,
            },
            is_sparse=data_level in {
                SparseDataLevel.NO_DATA,
                SparseDataLevel.COLD_START,
                SparseDataLevel.LIMITED_DATA,
            },
            warnings=tuple(warnings),
        )

    def _build_evidence_summary(self, context):
        learning_context = (
            context.recommendation_context.learning_context
        )

        behavioral = context.behavioral_evidence
        feedback = context.feedback_evidence
        confidence = context.confidence

        subjects = self._safe_sequence(
            learning_context.preferred_subjects
        )

        goals = self._safe_sequence(
            context.goals
        )

        behavioral_count = self._safe_count(
            behavioral.total_signals
        )

        positive_signals = self._safe_count(
            behavioral.positive_signals
        )

        negative_signals = self._safe_count(
            behavioral.negative_signals
        )

        neutral_signals = self._safe_count(
            behavioral.neutral_signals
        )

        feedback_count = self._safe_count(
            feedback.total_feedback
        )

        positive_feedback = self._safe_count(
            feedback.positive_feedback
        )

        negative_feedback = self._safe_count(
            feedback.negative_feedback
        )

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

        has_language = bool(
            learning_context.preferred_language
        )

        has_education_level = bool(
            learning_context.education_level
        )

        profile_available = bool(
            subjects
            or goals
            or has_language
            or has_education_level
        )

        # Evidence is counted by source category rather than by
        # duplicating confidence scores or inferred preferences.
        evidence_count = (
            behavioral_count
            + feedback_count
            + len(subjects)
            + len(goals)
        )

        return SparseEvidenceSummary(
            profile_available=profile_available,
            preferred_subject_count=len(subjects),
            learning_goal_count=len(goals),
            behavioral_signal_count=behavioral_count,
            positive_signal_count=positive_signals,
            negative_signal_count=negative_signals,
            neutral_signal_count=neutral_signals,
            feedback_count=feedback_count,
            positive_feedback_count=positive_feedback,
            negative_feedback_count=negative_feedback,
            evidence_count=evidence_count,
            profile_confidence=profile_confidence,
            behavioral_confidence=behavioral_confidence,
            feedback_confidence=feedback_confidence,
            overall_confidence=overall_confidence,
        )

    def _classify_data_level(self, evidence):
        has_profile = evidence.profile_available

        has_reliable_behavior = (
            evidence.behavioral_signal_count
            >= self.MIN_BEHAVIORAL_SIGNALS
            and evidence.behavioral_confidence
            >= self.MIN_BEHAVIORAL_CONFIDENCE
        )

        has_reliable_feedback = (
            evidence.feedback_count
            >= self.MIN_FEEDBACK_EVENTS
            and evidence.feedback_confidence
            >= self.MIN_FEEDBACK_CONFIDENCE
        )

        if (
            not has_profile
            and evidence.behavioral_signal_count == 0
            and evidence.feedback_count == 0
        ):
            return SparseDataLevel.NO_DATA

        if (
            evidence.evidence_count < 3
            and not has_profile
        ):
            return SparseDataLevel.COLD_START

        if (
            has_reliable_behavior
            and has_reliable_feedback
            and evidence.overall_confidence
            >= self.MIN_OVERALL_CONFIDENCE
            and evidence.evidence_count
            >= self.MIN_TOTAL_EVIDENCE
        ):
            return SparseDataLevel.SUFFICIENT_DATA

        if (
            has_reliable_behavior
            or has_reliable_feedback
            or (
                has_profile
                and evidence.profile_confidence
                >= self.MIN_PROFILE_CONFIDENCE
                and evidence.evidence_count >= 5
            )
        ):
            return SparseDataLevel.MODERATE_DATA

        return SparseDataLevel.LIMITED_DATA

    def _build_policy(self, evidence, data_level):
        reasons = []

        if not evidence.profile_available:
            reasons.append(SparseDataReason.NO_PROFILE)
        else:
            reasons.append(SparseDataReason.PROFILE_AVAILABLE)

        if evidence.behavioral_signal_count == 0:
            reasons.append(
                SparseDataReason.NO_BEHAVIORAL_HISTORY
            )
        else:
            reasons.append(
                SparseDataReason.BEHAVIORAL_HISTORY_AVAILABLE
            )

        if evidence.feedback_count == 0:
            reasons.append(
                SparseDataReason.NO_EXPLICIT_FEEDBACK
            )
        else:
            reasons.append(
                SparseDataReason.FEEDBACK_AVAILABLE
            )

        if evidence.evidence_count < self.MIN_TOTAL_EVIDENCE:
            reasons.append(
                SparseDataReason.LOW_EVIDENCE_COUNT
            )

        if (
            evidence.overall_confidence
            < self.MIN_OVERALL_CONFIDENCE
        ):
            reasons.append(
                SparseDataReason.LOW_CONFIDENCE
            )

        if data_level == SparseDataLevel.NO_DATA:
            strategy = ColdStartStrategy.GENERAL_DISCOVERY
            exploration_ratio = 0.80
            personalization_strength = 0.0

        elif data_level == SparseDataLevel.COLD_START:
            strategy = ColdStartStrategy.GENERAL_DISCOVERY
            exploration_ratio = 0.75
            personalization_strength = 0.10

        elif data_level == SparseDataLevel.LIMITED_DATA:
            strategy = ColdStartStrategy.PROFILE_GUIDED_DISCOVERY

            exploration_ratio = 0.65

            personalization_strength = min(
                0.30,
                evidence.profile_confidence * 0.30,
            )

        elif data_level == SparseDataLevel.MODERATE_DATA:
            strategy = (
                ColdStartStrategy.LIMITED_PERSONALIZATION
            )

            exploration_ratio = 0.40

            personalization_strength = min(
                0.70,
                max(
                    evidence.profile_confidence,
                    evidence.behavioral_confidence,
                    evidence.feedback_confidence,
                ),
            )

        else:
            strategy = (
                ColdStartStrategy.FULL_PERSONALIZATION
            )

            exploration_ratio = 0.20
            personalization_strength = min(
                1.0,
                evidence.overall_confidence,
            )

            reasons.append(
                SparseDataReason.SUFFICIENT_EVIDENCE
            )

        use_behavior = (
            evidence.behavioral_signal_count
            >= self.MIN_BEHAVIORAL_SIGNALS
            and evidence.behavioral_confidence
            >= self.MIN_BEHAVIORAL_CONFIDENCE
        )

        use_feedback = (
            evidence.feedback_count
            >= self.MIN_FEEDBACK_EVENTS
            and evidence.feedback_confidence
            >= self.MIN_FEEDBACK_CONFIDENCE
        )

        return ColdStartPolicy(
            strategy=strategy,
            exploration_ratio=exploration_ratio,
            personalization_strength=personalization_strength,
            use_explicit_preferences=evidence.profile_available,
            use_behavioral_signals=use_behavior,
            use_explicit_feedback=use_feedback,
            use_general_fallback=(
                data_level != SparseDataLevel.SUFFICIENT_DATA
            ),
            preserve_hard_constraints=True,
            treat_missing_evidence_as_neutral=True,
            reasons=tuple(dict.fromkeys(reasons)),
        )

    def _build_warnings(self, evidence, data_level):
        warnings = []

        if data_level == SparseDataLevel.NO_DATA:
            warnings.append(
                "No personalization evidence is available. "
                "Use general educational discovery."
            )

        if evidence.behavioral_signal_count == 0:
            warnings.append(
                "No behavioral history is available. "
                "Behavioral preferences must not be inferred."
            )

        if evidence.feedback_count == 0:
            warnings.append(
                "No explicit recommendation feedback is available."
            )

        if data_level in {
            SparseDataLevel.COLD_START,
            SparseDataLevel.LIMITED_DATA,
        }:
            warnings.append(
                "Personalization confidence is insufficient "
                "for strong behavioral adaptation."
            )

        return warnings

    @staticmethod
    def _safe_count(value):
        if isinstance(value, bool):
            return 0

        try:
            result = int(value)
        except (TypeError, ValueError, OverflowError):
            return 0

        return max(0, result)

    @staticmethod
    def _safe_sequence(value):
        if value is None:
            return []

        if isinstance(value, str):
            return [value] if value.strip() else []

        if isinstance(value, (list, tuple, set)):
            return [
                item
                for item in value
                if item is not None and str(item).strip()
            ]

        return []

    @staticmethod
    def _bounded(value):
        try:
            number = float(value)
        except (TypeError, ValueError, OverflowError):
            return 0.0

        if number != number:
            return 0.0

        return max(0.0, min(1.0, number))