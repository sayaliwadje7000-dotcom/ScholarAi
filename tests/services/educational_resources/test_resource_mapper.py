from datetime import datetime, timezone

import pytest

from app.models.study_resource import StudyResource

from app.schemas.external_resources import (
    ExternalAccessType,
    ExternalResource,
    ExternalResourceType,
)

from app.services.educational_resources.resource_mapper import (
    ExternalResourceMapper,
    ResourceMappingError,
)


@pytest.fixture
def external_resource():

    return ExternalResource(
        provider="openalex",
        external_id="W123456789",
        title="Introduction to Machine Learning",
        canonical_url="https://example.com/machine-learning",
        resource_type=ExternalResourceType.ARTICLE,
        description="An introduction to machine learning.",
        authors=("Author One", "Author Two"),
        subject="Computer Science",
        language="en",
        published_at=datetime(
            2025,
            1,
            1,
            tzinfo=timezone.utc,
        ),
        retrieved_at=datetime.now(timezone.utc),
        license="CC BY 4.0",
        access_type=ExternalAccessType.OPEN_ACCESS,
        metadata={
            "topics": [
                "machine learning",
                "artificial intelligence",
            ],
            "keywords": [
                "classification",
                "regression",
            ],
        },
    )


def test_mapper_returns_dictionary(external_resource):

    result = (
        ExternalResourceMapper.to_study_resource_values(
            external_resource
        )
    )

    assert isinstance(result, dict)


def test_mapper_preserves_title(external_resource):

    result = (
        ExternalResourceMapper.to_study_resource_values(
            external_resource
        )
    )

    assert result["title"] == external_resource.title


def test_mapper_preserves_url(external_resource):

    result = (
        ExternalResourceMapper.to_study_resource_values(
            external_resource
        )
    )

    assert result["url"] == external_resource.canonical_url


def test_mapper_preserves_provider(external_resource):

    result = (
        ExternalResourceMapper.to_study_resource_values(
            external_resource
        )
    )

    assert result["provider"] == "openalex"


def test_mapper_preserves_resource_type(external_resource):

    result = (
        ExternalResourceMapper.to_study_resource_values(
            external_resource
        )
    )

    assert result["resource_type"] == "article"


def test_mapper_preserves_subject_and_language(
    external_resource,
):

    result = (
        ExternalResourceMapper.to_study_resource_values(
            external_resource
        )
    )

    assert result["subject"] == "Computer Science"

    assert result["language"] == "en"


def test_mapper_preserves_published_at(external_resource):

    result = (
        ExternalResourceMapper.to_study_resource_values(
            external_resource
        )
    )

    assert result["published_at"] == external_resource.published_at


def test_mapper_preserves_provider_metadata(
    external_resource,
):

    result = (
        ExternalResourceMapper.to_study_resource_values(
            external_resource
        )
    )

    metadata = result["resource_metadata"]

    assert "machine learning" in metadata["topics"]

    assert "classification" in metadata["keywords"]


def test_mapper_preserves_external_provenance(
    external_resource,
):

    result = (
        ExternalResourceMapper.to_study_resource_values(
            external_resource
        )
    )

    provenance = (
        result["resource_metadata"]["external_source"]
    )

    assert provenance["provider"] == "openalex"

    assert provenance["external_id"] == "W123456789"

    assert provenance["license"] == "CC BY 4.0"

    assert provenance["access_type"] == "open_access"

    assert provenance["authors"] == [
        "Author One",
        "Author Two",
    ]


def test_mapper_sets_unknown_learning_fields_to_none(
    external_resource,
):

    result = (
        ExternalResourceMapper.to_study_resource_values(
            external_resource
        )
    )

    assert result["difficulty_level"] is None

    assert result["estimated_duration_minutes"] is None

    assert result["quality_score"] is None


def test_mapper_marks_resource_active(external_resource):

    result = (
        ExternalResourceMapper.to_study_resource_values(
            external_resource
        )
    )

    assert result["is_active"] is True


def test_mapper_creates_study_resource(external_resource):

    resource = ExternalResourceMapper.to_study_resource(
        external_resource
    )

    assert isinstance(resource, StudyResource)

    assert resource.title == external_resource.title

    assert resource.provider == "openalex"


def test_mapper_does_not_persist_resource(
    external_resource,
):

    resource = ExternalResourceMapper.to_study_resource(
        external_resource
    )

    # An unsaved SQLAlchemy instance has no database identity.
    assert isinstance(resource, StudyResource)

    assert resource.id is not None

    assert resource.title == external_resource.title
def test_mapper_rejects_invalid_resource_object():

    with pytest.raises(TypeError):

        ExternalResourceMapper.to_study_resource_values(
            {"title": "Invalid"}
        )


def test_mapper_rejects_non_json_metadata(
    external_resource,
):

    external_resource.metadata["invalid"] = object()

    with pytest.raises(ResourceMappingError):

        ExternalResourceMapper.to_study_resource_values(
            external_resource
        )