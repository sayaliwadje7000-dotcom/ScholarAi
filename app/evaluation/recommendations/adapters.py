import inspect


class RecommendationAdapterError(RuntimeError):
    pass


class CallableRecommendationAdapter:
    def __init__(self, pipeline):
        if not callable(pipeline):
            raise TypeError("pipeline must be callable")
        self.pipeline = pipeline

    async def recommend(self, case):
        try:
            output = self.pipeline(
                user_id=case.user_id,
                query=case.query,
            )

            if inspect.isawaitable(output):
                output = await output

            if isinstance(output, dict):
                output = output.get("recommendations", [])

            if not isinstance(output, (list, tuple)):
                raise RecommendationAdapterError(
                    "Pipeline must return a list or recommendations object"
                )

            normalized = []

            for item in output:
                if isinstance(item, str):
                    normalized.append({"item_id": item})
                elif isinstance(item, dict):
                    item_id = item.get("item_id") or item.get("id")
                    if not item_id:
                        raise RecommendationAdapterError(
                            "Recommendation requires item_id or id"
                        )
                    normalized.append({
                        **item,
                        "item_id": str(item_id),
                    })
                else:
                    raise RecommendationAdapterError(
                        "Unsupported recommendation item type"
                    )

            return normalized

        except RecommendationAdapterError:
            raise
        except Exception as exc:
            raise RecommendationAdapterError(
                f"Recommendation pipeline failed: {exc}"
            ) from exc
