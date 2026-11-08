"""Machine-learning recommendation dataset contracts and label policies."""

from app.services.recommendations.ml.dataset_schema import (
    DatasetLabel,
    LabelSource,
    RecommendationTrainingExample,
)

from app.services.recommendations.ml.labeling import (
    InteractionSignal,
    LabelPolicy,
    RecommendationFeedbackSignal,
    build_training_examples,
    label_interaction,
    label_recommendation_feedback,
)


__all__ = [
    "DatasetLabel",
    "LabelSource",
    "RecommendationTrainingExample",
    "InteractionSignal",
    "LabelPolicy",
    "RecommendationFeedbackSignal",
    "build_training_examples",
    "label_interaction",
    "label_recommendation_feedback",
]