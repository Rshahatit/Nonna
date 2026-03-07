"""Tests for REST API endpoints using FastAPI TestClient."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.models.elder import ElderResponse, ElderMemory, CallSchedule
from app.models.session import SessionResponse, MomentResponse, ReelResponse


@pytest.fixture
def client():
    return TestClient(app)


def _elder_response(**overrides):
    """Helper to create a valid ElderResponse."""
    defaults = dict(
        id="elder_abc",
        name="Fatima",
        phone_number="+12025551234",
        seed_context="Loves cooking",
        created_by="+12025559999",
        created_at=datetime(2024, 1, 1),
        call_schedule=CallSchedule(),
    )
    defaults.update(overrides)
    return ElderResponse(**defaults)


def _session_response(**overrides):
    """Helper to create a valid SessionResponse."""
    defaults = dict(
        id="session_001",
        elder_id="elder_abc",
        channel="phone",
        status="complete",
        started_at=datetime(2024, 1, 1, 14, 0, 0),
        duration=600,
        topics_covered=["childhood"],
    )
    defaults.update(overrides)
    return SessionResponse(**defaults)


class TestHealthCheck:
    def test_health(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "nonna-api"


class TestEldersAPI:
    @patch("app.routers.elders.firestore")
    def test_create_elder(self, mock_fs, client):
        mock_fs.create_elder = AsyncMock(return_value=_elder_response())

        response = client.post("/elders", json={
            "name": "Fatima",
            "phone_number": "+12025551234",
            "seed_context": "Loves cooking",
            "created_by": "+12025559999",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Fatima"
        assert data["id"] == "elder_abc"

    @patch("app.routers.elders.firestore")
    def test_get_elder(self, mock_fs, client):
        mock_fs.get_elder = AsyncMock(return_value=_elder_response())

        response = client.get("/elders/elder_abc")
        assert response.status_code == 200
        assert response.json()["name"] == "Fatima"

    @patch("app.routers.elders.firestore")
    def test_get_elder_not_found(self, mock_fs, client):
        mock_fs.get_elder = AsyncMock(return_value=None)

        response = client.get("/elders/nonexistent")
        assert response.status_code == 404

    @patch("app.routers.elders.firestore")
    def test_get_elder_memory(self, mock_fs, client):
        mock_fs.get_elder = AsyncMock(return_value=_elder_response())
        mock_fs.get_elder_memory = AsyncMock(return_value=ElderMemory(
            themes=["family", "cooking"],
            session_count=5,
        ))

        response = client.get("/elders/elder_abc/memory")
        assert response.status_code == 200
        data = response.json()
        assert data["session_count"] == 5
        assert "cooking" in data["themes"]

    @patch("app.routers.elders.firestore")
    def test_update_schedule(self, mock_fs, client):
        mock_fs.update_elder_schedule = AsyncMock(return_value=True)

        response = client.put("/elders/elder_abc/schedule", json={
            "call_schedule": {
                "days": ["tuesday", "thursday"],
                "time": "14:00",
                "timezone": "America/New_York",
            }
        })
        assert response.status_code == 200
        assert response.json()["status"] == "updated"


class TestSessionsAPI:
    @patch("app.routers.sessions.firestore")
    def test_list_sessions(self, mock_fs, client):
        mock_fs.list_sessions = AsyncMock(return_value=[_session_response()])

        response = client.get("/sessions?elder_id=elder_abc")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == "session_001"

    @patch("app.routers.sessions.firestore")
    def test_get_session(self, mock_fs, client):
        mock_fs.get_session = AsyncMock(return_value=_session_response())

        response = client.get("/sessions/session_001")
        assert response.status_code == 200
        assert response.json()["status"] == "complete"

    @patch("app.routers.sessions.firestore")
    def test_get_session_not_found(self, mock_fs, client):
        mock_fs.get_session = AsyncMock(return_value=None)

        response = client.get("/sessions/nonexistent")
        assert response.status_code == 404

    @patch("app.routers.sessions.firestore")
    def test_get_moments(self, mock_fs, client):
        mock_fs.get_session = AsyncMock(return_value=_session_response())
        mock_fs.list_moments = AsyncMock(return_value=[
            MomentResponse(
                id="m1",
                title="Mother's Baklava",
                summary="Learning to cook with her mother",
                quote="The secret was patience",
                visual_description="A warm kitchen",
                emotional_tone="nostalgic",
                order=1,
            ),
        ])

        response = client.get("/sessions/session_001/moments")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "Mother's Baklava"

    @patch("app.routers.sessions.firestore")
    def test_get_reel(self, mock_fs, client):
        mock_fs.get_reel_by_session = AsyncMock(return_value=ReelResponse(
            id="reel_001",
            session_id="session_001",
            elder_id="elder_abc",
            status="ready",
            video_url="https://storage.googleapis.com/reels/reel_001.mp4",
            duration=45,
            created_at=datetime(2024, 1, 1),
        ))

        response = client.get("/sessions/session_001/reel")
        assert response.status_code == 200
        assert response.json()["status"] == "ready"
