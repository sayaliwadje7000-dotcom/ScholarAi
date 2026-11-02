from uuid import UUID

from sqlalchemy import CheckConstraint

from app.database.base import Base
from app.models.study_resource import StudyResource


def test_study_resource_inherits_base():
    assert issubclass(StudyResource, Base)


def test_table_name():
    assert StudyResource.__tablename__ == "study_resources"


def test_primary_key():
    assert StudyResource.id.primary_key is True


def test_uuid_generation():
    resource = StudyResource(
        title="Python Tutorial",
        resource_type="tutorial",
        url="https://example.com/python",
    )

    assert isinstance(resource.id, UUID)


def test_title_column():
    assert StudyResource.title.property.columns[0].type.length == 255


def test_description_column():
    assert StudyResource.description.property.columns[0].nullable is True


def test_resource_type_column():
    assert StudyResource.resource_type.property.columns[0].type.length == 50


def test_url_column():
    assert StudyResource.url.property.columns[0].type.length == 2048


def test_provider_column():
    assert StudyResource.provider.property.columns[0].nullable is True


def test_subject_column():
    assert StudyResource.subject.property.columns[0].nullable is True


def test_language_column():
    assert StudyResource.language.property.columns[0].nullable is True


def test_difficulty_column():
    assert StudyResource.difficulty_level.property.columns[0].nullable is True


def test_duration_column():
    assert StudyResource.estimated_duration_minutes.property.columns[0].nullable is True


def test_quality_score_column():
    assert StudyResource.quality_score.property.columns[0].nullable is True


def test_metadata_column():
    column = StudyResource.__table__.c["metadata"]

    assert column.nullable is False


def test_active_default():
    resource = StudyResource(
        title="Python Tutorial",
        resource_type="tutorial",
        url="https://example.com/python",
    )

    assert resource.is_active is True


def test_resource_metadata_default():
    resource = StudyResource(
        title="Python Tutorial",
        resource_type="tutorial",
        url="https://example.com/python",
    )

    assert resource.resource_metadata == {}


def test_created_at_column():
    assert StudyResource.created_at.property.columns[0].nullable is False


def test_updated_at_column():
    assert StudyResource.updated_at.property.columns[0].nullable is False


def test_model_constraints():
    constraint_names = {
        constraint.name
        for constraint in StudyResource.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }

    expected = {
        "ck_study_resources_title_nonempty",
        "ck_study_resources_url_nonempty",
        "ck_study_resources_valid_type",
        "ck_study_resources_valid_difficulty",
        "ck_study_resources_valid_duration",
        "ck_study_resources_valid_quality",
        "ck_study_resources_metadata_object",
    }

    assert expected.issubset(constraint_names)


def test_model_indexes():
    index_names = {
        index.name
        for index in StudyResource.__table__.indexes
    }

    expected = {
        "ix_study_resources_resource_type",
        "ix_study_resources_subject",
        "ix_study_resources_language",
        "ix_study_resources_difficulty",
        "ix_study_resources_is_active",
        "ix_study_resources_quality_score",
        "ix_study_resources_created_at",
        "ix_study_resources_subject_type_active",
    }

    assert expected.issubset(index_names)


def test_instance_creation():
    resource = StudyResource(
        title="Introduction to Data Structures",
        description="A beginner-friendly educational resource.",
        resource_type="video",
        url="https://example.com/data-structures",
        provider="Example Academy",
        subject="Data Structures",
        language="English",
        difficulty_level="beginner",
        estimated_duration_minutes=30,
        quality_score=4.50,
    )

    assert resource.title == "Introduction to Data Structures"
    assert resource.resource_type == "video"
    assert resource.subject == "Data Structures"
    assert resource.quality_score == 4.50


def test_repr():
    resource = StudyResource(
        title="Python Tutorial",
        resource_type="tutorial",
        url="https://example.com/python",
    )

    assert "StudyResource" in repr(resource)
    assert "Python Tutorial" in repr(resource)