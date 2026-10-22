from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_home_endpoint():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["application"] == "ScholarAI"


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_chat_endpoint():
    response = client.post(
        "/api/v1/chat",
        json={
            "message": "Explain machine learning.",
            "conversation_id": None,
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "machine learning" in response.json()["answer"].lower()


def test_chat_rejects_empty_message():
    response = client.post(
        "/api/v1/chat",
        json={
            "message": "",
            "conversation_id": None,
        },
    )

    assert response.status_code == 422


def test_chat_rejects_invalid_message_type():
    response = client.post(
        "/api/v1/chat",
        json={
            "message": 123,
            "conversation_id": None,
        },
    )

    assert response.status_code == 422
    
def test_chat_rejects_whitespace_only_message():
    response = client.post(
        "/api/v1/chat",
        json={
            "message": "     ",
            "conversation_id": None,
        },
    )

    assert response.status_code == 422


def test_chat_strips_message_whitespace():
    response = client.post(
        "/api/v1/chat",
        json={
            "message": "   Explain machine learning.   ",
            "conversation_id": None,
        },
    )

    assert response.status_code == 200
    assert "received your question: Explain machine learning." in (
        response.json()["answer"]
    )
    
def test_chat_rejects_message_exceeding_max_length():
    response = client.post(
        "/api/v1/chat",
        json={
            "message": "a" * 5001,
            "conversation_id": None,
        },
    )

    assert response.status_code == 422


def test_chat_rejects_whitespace_only_conversation_id():
    response = client.post(
        "/api/v1/chat",
        json={
            "message": "Explain machine learning.",
            "conversation_id": "     ",
        },
    )

    assert response.status_code == 422

def test_chat_validation_error_response_structure():
    response = client.post(
        "/api/v1/chat",
        json={
            "message": "",
            "conversation_id": None,
        },
    )

    assert response.status_code == 422

    data = response.json()

    assert "detail" in data
    assert isinstance(data["detail"], list)
    assert len(data["detail"]) > 0

    error = data["detail"][0]

    assert error["loc"] == ["body", "message"]
    assert error["type"] == "string_too_short"
def test_cors_allows_local_frontend_origin():
    response = client.options(
        "/api/v1/chat",
        headers={
            "Origin": "http://127.0.0.1:5500",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert (
        response.headers["access-control-allow-origin"]
        == "http://127.0.0.1:5500"
    )


def test_cors_allows_localhost_frontend_origin():
    response = client.options(
        "/api/v1/chat",
        headers={
            "Origin": "http://localhost:5500",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert (
        response.headers["access-control-allow-origin"]
        == "http://localhost:5500"
    )


def test_cors_rejects_unconfigured_origin():
    response = client.options(
        "/api/v1/chat",
        headers={
            "Origin": "http://example.com",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert (
        "access-control-allow-origin"
        not in response.headers
    )


