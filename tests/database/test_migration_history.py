from pathlib import Path

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_CONFIG_PATH = PROJECT_ROOT / "alembic.ini"


@pytest.fixture(scope="module")
def migration_script():
    assert ALEMBIC_CONFIG_PATH.exists(), (
        f"Alembic configuration not found: {ALEMBIC_CONFIG_PATH}"
    )

    config = Config(str(ALEMBIC_CONFIG_PATH))

    script = ScriptDirectory.from_config(config)

    return script


def test_alembic_migration_directory_is_configured(migration_script):
    assert migration_script.dir is not None

    migration_directory = Path(migration_script.dir)

    assert migration_directory.exists()
    assert migration_directory.is_dir()


def test_alembic_has_migration_heads(migration_script):
    heads = migration_script.get_heads()

    assert heads, "No Alembic migration heads were found."


def test_migration_revision_identifiers_are_unique(migration_script):
    revisions = list(migration_script.walk_revisions())

    revision_ids = [
        revision.revision
        for revision in revisions
    ]

    assert len(revision_ids) == len(set(revision_ids)), (
        "Duplicate Alembic revision identifiers detected."
    )


def test_migration_parent_references_exist(migration_script):
    revisions = list(migration_script.walk_revisions())

    known_revision_ids = {
        revision.revision
        for revision in revisions
    }

    missing_parents = []

    for revision in revisions:
        parents = revision.down_revision

        if parents is None:
            continue

        if isinstance(parents, str):
            parents = (parents,)

        for parent in parents:
            if parent not in known_revision_ids:
                missing_parents.append(
                    {
                        "revision": revision.revision,
                        "missing_parent": parent,
                    }
                )

    assert not missing_parents, (
        f"Migration parents not found: {missing_parents}"
    )


def test_migration_heads_exist_in_revision_history(migration_script):
    revisions = {
        revision.revision
        for revision in migration_script.walk_revisions()
    }

    for head in migration_script.get_heads():
        assert head in revisions


def test_migration_graph_can_be_traversed(migration_script):
    revisions = list(migration_script.walk_revisions())

    assert revisions, "Migration graph is empty."

    for revision in revisions:
        assert revision.revision
        assert isinstance(revision.revision, str)
