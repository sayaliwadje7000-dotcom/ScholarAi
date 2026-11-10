from threading import RLock

from app.scoring.exceptions import ScoringConfigurationError


class ScorerRegistry:

    def __init__(self):
        self._scorers = {}
        self._lock = RLock()

    def register(self, scorer):
        name = getattr(scorer, "name", None)

        if not name:
            raise ScoringConfigurationError(
                "Scorer must have a name."
            )

        with self._lock:
            if name in self._scorers:
                raise ScoringConfigurationError(
                    f"Scorer '{name}' is already registered."
                )

            self._scorers[name] = scorer

    def get(self, name):
        with self._lock:
            return self._scorers.get(name)

    def list_scorers(self):
        with self._lock:
            return sorted(self._scorers.keys())