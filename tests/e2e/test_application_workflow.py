def test_application_root_is_available(e2e_client):
    response = e2e_client.get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")


def test_application_health_endpoint_is_available(e2e_client):
    response = e2e_client.get("/health")

    assert response.status_code == 200


def test_application_returns_valid_json(e2e_client):
    response = e2e_client.get("/")

    assert response.status_code == 200
    assert isinstance(response.json(), dict)
