from threading import RLock


class MetricRegistry:

    def __init__(self):
        self._metrics = {}
        self._lock = RLock()

    def register(self, name, metric):
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Metric name cannot be empty.")

        if not callable(metric):
            raise ValueError("Metric must be callable.")

        with self._lock:
            if name in self._metrics:
                raise ValueError(
                    f"Metric '{name}' is already registered."
                )

            self._metrics[name] = metric

    def get(self, name):
        with self._lock:
            return self._metrics.get(name)

    def list_metrics(self):
        with self._lock:
            return sorted(self._metrics.keys())

    def unregister(self, name):
        with self._lock:
            return self._metrics.pop(name, None)