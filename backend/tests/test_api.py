import asyncio
import json
import os
import tempfile
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock

# Use a temp DB for tests
os.environ["TEST_DB_PATH"] = str(tempfile.mktemp(suffix=".db"))


pytestmark = pytest.mark.asyncio


@pytest.fixture(scope="module")
def client():
    """Test client with initialized DB."""
    import database
    database.DB_PATH = os.environ["TEST_DB_PATH"]

    # Run init_db synchronously
    loop = asyncio.new_event_loop()
    loop.run_until_complete(database.init_db())
    loop.close()

    from main import app
    with TestClient(app) as c:
        yield c


class TestHealthEndpoint:
    def test_health_returns_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data

    def test_ollama_status_included(self, client):
        resp = client.get("/health")
        data = resp.json()
        assert "ollama" in data


class TestProfilesEndpoints:
    def test_list_profiles_returns_builtin(self, client):
        resp = client.get("/profiles")
        assert resp.status_code == 200
        profiles = resp.json()
        assert isinstance(profiles, list)
        ids = [p["id"] for p in profiles]
        assert "bootcamp" in ids
        assert "production" in ids

    def test_create_custom_profile(self, client):
        body = {
            "name": "Test Profile",
            "description": "For unit tests",
            "agent_config": {"skip_agents": ["plagiarism"], "strictness": "moderate"},
            "scoring_weights": {},
            "llm_tone": "neutral",
        }
        resp = client.post("/profiles", json=body)
        assert resp.status_code == 200
        assert "id" in resp.json()
        created_id = resp.json()["id"]

        # Verify it appears in list
        list_resp = client.get("/profiles")
        ids = [p["id"] for p in list_resp.json()]
        assert created_id in ids

        return created_id

    def test_cannot_delete_builtin_profile(self, client):
        resp = client.delete("/profiles/bootcamp")
        assert resp.status_code == 403

    def test_get_profile_not_found(self, client):
        resp = client.get("/profiles/nonexistent-id-xyz")
        assert resp.status_code == 404


class TestRubricsEndpoints:
    def test_list_rubrics_empty(self, client):
        resp = client.get("/rubrics")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_create_and_delete_rubric(self, client):
        body = {
            "name": "Test Rubric",
            "categories": [
                {"name": "Quality", "weight": 0.6, "min_expectations": "No critical bugs"},
                {"name": "Security", "weight": 0.4, "min_expectations": "No SQL injection"},
            ],
        }
        resp = client.post("/rubrics", json=body)
        assert resp.status_code == 200
        rid = resp.json()["id"]

        # Delete it
        del_resp = client.delete(f"/rubrics/{rid}")
        assert del_resp.status_code == 200


class TestHistoryEndpoints:
    def test_history_empty_project(self, client):
        resp = client.get("/history/nonexistent-project")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_delete_nonexistent_review(self, client):
        resp = client.delete("/history/nonexistent-review-id")
        # Should succeed (no-op) or 404
        assert resp.status_code in (200, 404)
