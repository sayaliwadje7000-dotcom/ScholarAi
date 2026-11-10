from pathlib import Path

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_CONFIG_PATH = PROJECT_ROOT / "alembic.ini"


@pytest.fixture(scope="module")
def migration_script():
    assert ALEMBIC_CONFIG_PATH.exists(), (
        "alembic.ini must exist in the project root."
    )

    config = Config(str(ALEMBIC_CONFIG_PATH))

    return ScriptDirectory.from_config(config)


def test_migration_scripts_have_valid_source_files(migration_script):
    revisions = list(migration_script.walk_revisions())

    for revision in revisions:
        source_file = Path(revision.path)

        assert source_file.exists(), (
            f"Migration source file is missing: {revision.path}"
        )


def test_migration_revisions_do_not_reference_themselves(
    migration_script,
):
    revisions = list(migration_script.walk_revisions())

    for revision in revisions:
        parents = revision.down_revision

        if parents is None:
            continue

        if isinstance(parents, str):
            parents = (parents,)

        assert revision.revision not in parents, (
            f"Migration {revision.revision} references itself."
        )


def test_migration_graph_contains_no_duplicate_parent_links(
    migration_script,
):
    revisions = list(migration_script.walk_revisions())

    for revision in revisions:
        parents = revision.down_revision

        if parents is None or isinstance(parents, str):
            continue

        assert len(parents) == len(set(parents)), (
            f"Migration {revision.revision} contains duplicate parents."
        )


def test_each_migration_has_a_revision_identifier(migration_script):
    revisions = list(migration_script.walk_revisions())

    for revision in revisions:
        assert revision.revision is not None
        assert revision.revision.strip()


def test_migration_script_directory_is_not_empty(migration_script):
    revisions = list(migration_script.walk_revisions())

    assert len(revisions) > 0
