import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_get_all_languages(client):
    response = client.get("/languages/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    if response.json():
        language = response.json()[0]
        assert "id" in language
        assert "name" in language
        assert "version" in language
        assert "source_file" in language

def test_get_language_by_id(client):
    language_id = 1
    response = client.get(f"/languages/{language_id}")
    assert response.status_code == 200
    language = response.json()
    assert "id" in language
    assert language["id"] == language_id

def test_get_nonexistent_language(client):
    response = client.get("/languages/0")
    assert response.status_code == 404
    assert response.json()["detail"] == "Language not found."

def test_get_all_statuses(client):
    response = client.get("/statuses/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    if response.json():
        status = response.json()[0]
        assert "id" in status
        assert "status_code" in status
        assert "status_full" in status
