def test_core_application_routes_remain_registered(e2e_client):
    response = e2e_client.get("/openapi.json")

    assert response.status_code == 200

    paths = response.json()["paths"]

    expected_paths = {
        "/",
        "/health",
    }

    for expected_path in expected_paths:
        assert expected_path in paths


def test_rag_route_remains_registered(e2e_client):
    response = e2e_client.get("/openapi.json")

    assert response.status_code == 200

    paths = response.json()["paths"]

    rag_routes = [
        path
        for path, operations in paths.items()
        if path.endswith("/ask") and "post" in operations
    ]

    assert rag_routes


def test_openapi_contains_application_metadata(e2e_client):
    response = e2e_client.get("/openapi.json")

    assert response.status_code == 200

    schema = response.json()

    assert schema["info"].get("title")
    assert schema["info"].get("version")
