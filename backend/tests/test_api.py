import pytest


def test_health_and_root_routes(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["name"] == "LexProof API"
    assert response.json()["status"] == "running"


@pytest.mark.parametrize("endpoint,body", [
    ("/retrieval/search", {"query": "x"}),
    ("/retrieval/search", {"query": "personal data", "top_k": 0}),
    ("/retrieval/search", {"query": "personal data", "top_k": 11}),
    ("/verify", {"claim": "x"}),
    ("/verify", {"claim": "personal data", "retrieval_k": 2}),
    ("/verify", {"claim": "personal data", "retrieval_k": 16}),
])
def test_request_validation(client, endpoint, body):
    response = client.post(endpoint, json=body)
    assert response.status_code == 422, response.text
