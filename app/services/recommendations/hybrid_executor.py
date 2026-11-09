from __future__ import annotations


class HybridExecutor:
    """
    Thin adapter around the Phase 15 orchestrator.

    The orchestrator must expose:
        execute(context, limit=None)
    """

    def __init__(self, orchestrator) -> None:
        if orchestrator is None:
            raise ValueError("orchestrator is required")

        execute = getattr(orchestrator, "execute", None)

        if not callable(execute):
            raise TypeError(
                "orchestrator must expose execute(context, limit=None)"
            )

        self.orchestrator = orchestrator

    def __call__(self, hybrid_context, *, limit=None):
        return self.orchestrator.execute(
            hybrid_context,
            limit=limit,
        )