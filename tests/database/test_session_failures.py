from unittest.mock import MagicMock

import pytest

import app.database.session as database_session


def test_session_creation_failure_propagates(monkeypatch):
    def failing_session_factory():
        raise RuntimeError("Unable to create database session")

    monkeypatch.setattr(
        database_session,
        "SessionLocal",
        failing_session_factory,
    )

    with pytest.raises(
        RuntimeError,
        match="Unable to create database session",
    ):
        next(database_session.get_db())


def test_rollback_occurs_before_session_close(monkeypatch):
    execution_order = []

    mock_db = MagicMock()

    mock_db.rollback.side_effect = (
        lambda: execution_order.append("rollback")
    )

    mock_db.close.side_effect = (
        lambda: execution_order.append("close")
    )

    monkeypatch.setattr(
        database_session,
        "SessionLocal",
        lambda: mock_db,
    )

    generator = database_session.get_db()

    next(generator)

    with pytest.raises(RuntimeError):
        generator.throw(RuntimeError("Simulated failure"))

    assert execution_order == ["rollback", "close"]


def test_session_is_closed_if_rollback_fails(monkeypatch):
    mock_db = MagicMock()

    mock_db.rollback.side_effect = RuntimeError(
        "Rollback failed"
    )

    monkeypatch.setattr(
        database_session,
        "SessionLocal",
        lambda: mock_db,
    )

    generator = database_session.get_db()

    next(generator)

    with pytest.raises(RuntimeError, match="Rollback failed"):
        generator.throw(RuntimeError("Original failure"))

    mock_db.rollback.assert_called_once()
    mock_db.close.assert_called_once()
