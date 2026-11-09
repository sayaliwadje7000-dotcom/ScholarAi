from fastapi import FastAPI, Request

import pytest

from app.api.hybrid_recommendation_dependencies import (
    HybridRecommendationDependencyError,
    get_hybrid_recommendation_orchestrator,
)


def test_dependency_rejects_missing_orchestrator():
    app = FastAPI()
    request = Request(
        {
            "type": "http",
            "app": app,
            "method": "GET",
            "path": "/",
            "headers": [],
            "query_string": b"",
            "server": ("testserver", 80),
            "client": ("testclient", 50000),
            "scheme": "http",
        }
    )

    with pytest.raises(
        HybridRecommendationDependencyError
    ):
        get_hybrid_recommendation_orchestrator(request)


def test_dependency_rejects_invalid_orchestrator():
    app = FastAPI()
    app.state.hybrid_recommendation_orchestrator = object()

    request = Request(
        {
            "type": "http",
            "app": app,
            "method": "GET",
            "path": "/",
            "headers": [],
            "query_string": b"",
            "server": ("testserver", 80),
            "client": ("testclient", 50000),
            "scheme": "http",
        }
    )

    with pytest.raises(
        HybridRecommendationDependencyError
    ):
        get_hybrid_recommendation_orchestrator(request)