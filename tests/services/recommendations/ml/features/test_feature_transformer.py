import pytest

from app.services.recommendations.ml.features.feature_transformer import (
    RecommendationFeatureTransformer,
)


def make_records():

    return [
        {
            "preferred_language": "english",
            "education_level": "undergraduate",
            "resource_type": "video",
            "subject": "computer science",
            "language": "english",
            "difficulty_level": "beginner",
            "provider": "youtube",

            "quality_score": 4.5,
            "estimated_duration_minutes": 30,
            "resource_age_days": 20,
            "historical_view_count": 3,
            "historical_click_count": 2,
            "historical_save_count": 1,
            "historical_completion_count": 0,
            "historical_rating_count": 1,
            "historical_average_rating": 4.0,

            "preferred_subjects": ["computer science"],
            "learning_goals": ["exam preparation"],
            "categories": ["machine-learning"],
            "title": "Machine Learning Introduction",
            "description": "Introduction to machine learning",
            "topics": ["supervised learning"],
            "keywords": ["classification"],
            "learning_objectives": ["understand algorithms"],
            "prerequisites": ["basic mathematics"],
        },
        {
            "preferred_language": "hindi",
            "education_level": "undergraduate",
            "resource_type": "article",
            "subject": "mathematics",
            "language": "hindi",
            "difficulty_level": "intermediate",
            "provider": "openalex",

            "quality_score": 4.0,
            "estimated_duration_minutes": 45,
            "resource_age_days": 60,
            "historical_view_count": 1,
            "historical_click_count": 1,
            "historical_save_count": 2,
            "historical_completion_count": 1,
            "historical_rating_count": 0,
            "historical_average_rating": None,

            "preferred_subjects": ["mathematics"],
            "learning_goals": ["concept understanding"],
            "categories": ["algebra"],
            "title": "Linear Algebra",
            "description": "Introduction to matrices",
            "topics": ["matrices"],
            "keywords": ["vectors"],
            "learning_objectives": ["understand matrices"],
            "prerequisites": [],
        },
    ]


def test_fit_transform_creates_feature_matrix():

    transformer = RecommendationFeatureTransformer()

    result = transformer.fit_transform(
        make_records()
    )

    assert result.row_count == 2
    assert result.feature_count > 0
    assert result.matrix.shape[0] == 2


def test_transform_requires_fit():

    transformer = RecommendationFeatureTransformer()

    with pytest.raises(RuntimeError):

        transformer.transform(
            make_records()
        )


def test_transform_uses_same_feature_dimensions():

    transformer = RecommendationFeatureTransformer()

    training = transformer.fit_transform(
        make_records()
    )

    new_records = [
        {
            **make_records()[0],
            "resource_type": "unknown_new_type",
        }
    ]

    result = transformer.transform(
        new_records
    )

    assert result.feature_count == training.feature_count


def test_empty_dataset_is_rejected():

    transformer = RecommendationFeatureTransformer()

    with pytest.raises(ValueError):

        transformer.fit_transform([])


def test_text_features_are_generated():

    transformer = RecommendationFeatureTransformer()

    result = transformer.fit_transform(
        make_records()
    )

    assert any(
        name.startswith("text__")
        for name in result.feature_names
    )