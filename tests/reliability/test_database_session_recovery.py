import pytest

import app.database.session as database_session


class RollbackFailingSession:
    def __init__(self):
        self.rollback_called = False
        self.close_called = False

    def rollback(self):
        self.rollback_called = True
        raise RuntimeError("Simulated rollback failure")

    def close(self):
        self.close_called = True


def test_database_session_closes_when_rollback_fails(monkeypatch):
    fake_session = RollbackFailingSession()

    monkeypatch.setattr(
        database_session,
        "SessionLocal",
        lambda: fake_session,
    )

    generator = database_session.get_db()

    next(generator)

    with pytest.raises(
        RuntimeError,
        match="Simulated rollback failure",
    ):
        generator.throw(
            RuntimeError("Simulated database operation failure")
        )

    assert fake_session.rollback_called is True
    assert fake_session.close_called is True


def test_database_session_closes_after_normal_completion(monkeypatch):
    class FakeSession:
        def __init__(self):
            self.close_called = False

        def close(self):
            self.close_called = True

        def rollback(self):
            pass

    fake_session = FakeSession()

    monkeypatch.setattr(
        database_session,
        "SessionLocal",
        lambda: fake_session,
    )

    generator = database_session.get_db()

    yielded_session = next(generator)

    assert yielded_session is fake_session

    with pytest.raises(StopIteration):
        next(generator)

    assert fake_session.close_called is True
