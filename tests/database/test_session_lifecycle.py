from unittest.mock import MagicMock

import pytest

import app.database.session as database_session


def test_get_db_yields_database_session(monkeypatch):
    mock_db = MagicMock()

    monkeypatch.setattr(
        database_session,
        "SessionLocal",
        lambda: mock_db,
    )

    generator = database_session.get_db()

    yielded_db = next(generator)

    assert yielded_db is mock_db

    with pytest.raises(StopIteration):
        next(generator)

    mock_db.close.assert_called_once()
    mock_db.rollback.assert_not_called()


def test_get_db_closes_session_after_normal_execution(monkeypatch):
    mock_db = MagicMock()

    monkeypatch.setattr(
        database_session,
        "SessionLocal",
        lambda: mock_db,
    )

    generator = database_session.get_db()

    next(generator)

    with pytest.raises(StopIteration):
        next(generator)

    mock_db.close.assert_called_once()


def test_get_db_rolls_back_after_exception(monkeypatch):
    mock_db = MagicMock()

    monkeypatch.setattr(
        database_session,
        "SessionLocal",
        lambda: mock_db,
    )

    generator = database_session.get_db()

    next(generator)

    with pytest.raises(RuntimeError, match="Database operation failed"):
        generator.throw(
            RuntimeError("Database operation failed")
        )

    mock_db.rollback.assert_called_once()
    mock_db.close.assert_called_once()


def test_get_db_closes_session_after_exception(monkeypatch):
    mock_db = MagicMock()

    monkeypatch.setattr(
        database_session,
        "SessionLocal",
        lambda: mock_db,
    )

    generator = database_session.get_db()

    next(generator)

    with pytest.raises(ValueError):
        generator.throw(ValueError("Simulated failure"))

    mock_db.close.assert_called_once()


def test_get_db_does_not_commit_automatically(monkeypatch):
    mock_db = MagicMock()

    monkeypatch.setattr(
        database_session,
        "SessionLocal",
        lambda: mock_db,
    )

    generator = database_session.get_db()

    next(generator)

    with pytest.raises(StopIteration):
        next(generator)

    mock_db.commit.assert_not_called()
