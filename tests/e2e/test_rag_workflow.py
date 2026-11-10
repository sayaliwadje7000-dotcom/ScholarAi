def get_rag_ask_path(client):
    response = client.get("/openapi.json")

    assert response.status_code == 200

    paths = response.json()["paths"]

    matching_paths = [
        path
        for path, operations in paths.items()
        if path.endswith("/ask") and "post" in operations
    ]

    assert matching_paths, "RAG POST /ask endpoint was not found."

    return matching_paths[0]


def test_rag_endpoint_rejects_unauthenticated_request(e2e_client):
    path = get_rag_ask_path(e2e_client)

    response = e2e_client.post(
        path,
        json={
            "query": "Explain machine learning",
            "limit": 5,
        },
    )

    assert response.status_code in {401, 403}


def test_rag_endpoint_rejects_invalid_request(e2e_client):
    path = get_rag_ask_path(e2e_client)

    response = e2e_client.post(
        path,
        json={
            "query": "",
            "limit": -1,
        },
    )

    assert response.status_code in {401, 403, 422}


def test_rag_endpoint_rejects_invalid_limit(e2e_client):
    path = get_rag_ask_path(e2e_client)

    response = e2e_client.post(
        path,
        json={
            "query": "Explain database indexing",
            "limit": -10,
        },
    )

    assert response.status_code in {401, 403, 422}
