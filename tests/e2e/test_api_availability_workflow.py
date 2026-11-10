def test_openapi_schema_is_available(e2e_client):
    response = e2e_client.get("/openapi.json")

    assert response.status_code == 200

    schema = response.json()

    assert "openapi" in schema
    assert "info" in schema
    assert "paths" in schema


def test_api_documentation_is_available(e2e_client):
    response = e2e_client.get("/docs")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_application_has_registered_api_operations(e2e_client):
    response = e2e_client.get("/openapi.json")

    assert response.status_code == 200

    paths = response.json()["paths"]

    assert paths

    operations = [
        method
        for path_item in paths.values()
        for method in path_item
        if method.lower() in {"get", "post", "put", "patch", "delete"}
    ]

    assert operations
