"""Integration tests — run against a live server with in-memory storage.

These tests start the FastAPI app with USE_LOCAL_STORAGE=true and exercise
the full request/response cycle through all API endpoints.
"""

import os

# Must be set before any app imports
os.environ["USE_LOCAL_STORAGE"] = "true"

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services import firestore  # will be local_storage


@pytest.fixture(autouse=True)
def clean_storage():
    """Reset in-memory storage before each test."""
    firestore.reset()
    yield
    firestore.reset()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def elder_payload():
    return {
        "name": "Fatima",
        "phone_number": "+12025551234",
        "seed_context": "Mom grew up in Amman, amazing cook, dad passed 2 years ago",
        "created_by": "+12025559999",
    }


@pytest.fixture
def created_elder(client, elder_payload):
    """Create and return an elder for use in tests."""
    resp = client.post("/elders", json=elder_payload)
    assert resp.status_code == 201
    return resp.json()


# ──────────────────────────── Health ────────────────────────────

class TestHealth:
    def test_health_endpoint(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["service"] == "nonna-api"


# ──────────────────────────── Elders CRUD ────────────────────────────

class TestEldersCRUD:
    def test_create_elder(self, client, elder_payload):
        resp = client.post("/elders", json=elder_payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Fatima"
        assert data["phone_number"] == "+12025551234"
        assert data["seed_context"] == elder_payload["seed_context"]
        assert data["created_by"] == "+12025559999"
        assert "id" in data
        assert "created_at" in data
        assert "call_schedule" in data

    def test_create_elder_with_schedule(self, client):
        resp = client.post("/elders", json={
            "name": "Hassan",
            "phone_number": "+12025555678",
            "seed_context": "Dad was an engineer",
            "created_by": "+12025559999",
            "call_schedule": {
                "days": ["tuesday", "thursday"],
                "time": "14:00",
                "timezone": "America/New_York",
            },
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["call_schedule"]["days"] == ["tuesday", "thursday"]
        assert data["call_schedule"]["time"] == "14:00"

    def test_create_elder_validation_bad_phone(self, client):
        resp = client.post("/elders", json={
            "name": "Test",
            "phone_number": "not-a-phone",
            "seed_context": "Test",
            "created_by": "x",
        })
        assert resp.status_code == 422
        detail = resp.json()["detail"]
        assert any("phone_number" in str(e) for e in detail)

    def test_create_elder_validation_empty_name(self, client):
        resp = client.post("/elders", json={
            "name": "",
            "phone_number": "+12025551234",
            "seed_context": "Test",
            "created_by": "x",
        })
        assert resp.status_code == 422

    def test_get_elder(self, client, created_elder):
        elder_id = created_elder["id"]
        resp = client.get(f"/elders/{elder_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == elder_id
        assert data["name"] == "Fatima"

    def test_get_elder_not_found(self, client):
        resp = client.get("/elders/nonexistent-id")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_update_schedule(self, client, created_elder):
        elder_id = created_elder["id"]
        resp = client.put(f"/elders/{elder_id}/schedule", json={
            "call_schedule": {
                "days": ["monday", "wednesday", "friday"],
                "time": "10:00",
                "timezone": "America/Chicago",
            },
        })
        assert resp.status_code == 200
        assert resp.json()["status"] == "updated"

        # Verify the schedule was actually updated by re-fetching
        elder = client.get(f"/elders/{elder_id}").json()
        assert elder["call_schedule"]["days"] == ["monday", "wednesday", "friday"]
        assert elder["call_schedule"]["time"] == "10:00"

    def test_update_schedule_not_found(self, client):
        resp = client.put("/elders/nonexistent/schedule", json={
            "call_schedule": {"days": ["monday"], "time": "10:00", "timezone": "UTC"},
        })
        assert resp.status_code == 404


# ──────────────────────────── Elder Memory ────────────────────────────

class TestElderMemory:
    def test_get_memory_initial(self, client, created_elder):
        elder_id = created_elder["id"]
        resp = client.get(f"/elders/{elder_id}/memory")
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_count"] == 0
        assert data["people"] == []
        assert data["places"] == []
        assert data["themes"] == []

    def test_get_memory_not_found(self, client):
        resp = client.get("/elders/nonexistent/memory")
        assert resp.status_code == 404


# ──────────────────────────── Sessions ────────────────────────────

class TestSessions:
    def test_list_sessions_empty(self, client, created_elder):
        elder_id = created_elder["id"]
        resp = client.get(f"/elders/{elder_id}/sessions")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_sessions_global_empty(self, client):
        resp = client.get("/sessions")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_session_not_found(self, client):
        resp = client.get("/sessions/nonexistent")
        assert resp.status_code == 404

    def test_list_sessions_not_found_elder(self, client):
        resp = client.get("/elders/nonexistent/sessions")
        assert resp.status_code == 404


# ──────────────────────────── Moments ────────────────────────────

class TestMoments:
    def test_get_moments_session_not_found(self, client):
        resp = client.get("/sessions/nonexistent/moments")
        assert resp.status_code == 404


# ──────────────────────────── Reels ────────────────────────────

class TestReels:
    def test_get_reel_not_found(self, client):
        resp = client.get("/sessions/nonexistent/reel")
        assert resp.status_code == 404


# ──────────────────────────── Twilio Webhooks ────────────────────────────

class TestTwilioWebhooks:
    def test_inbound_call_known_number(self, client, created_elder):
        """Inbound call from a registered elder should connect to media stream."""
        resp = client.post("/twilio/voice", data={
            "From": "+12025551234",
            "To": "+15551234567",
            "CallSid": "CA123456",
        })
        assert resp.status_code == 200
        # Should return TwiML
        body = resp.text
        assert "<Response>" in body
        assert "<Connect>" in body or "<Say>" in body

    def test_inbound_call_unknown_number(self, client):
        """Inbound call from unknown number should be rejected."""
        resp = client.post("/twilio/voice", data={
            "From": "+19999999999",
            "To": "+15551234567",
            "CallSid": "CA789012",
        })
        assert resp.status_code == 200
        body = resp.text
        assert "<Response>" in body
        assert "recognize" in body.lower() or "Hangup" in body

    def test_status_callback(self, client):
        """Status callback should return 200."""
        resp = client.post("/twilio/status", data={
            "CallSid": "CA123456",
            "CallStatus": "completed",
        })
        assert resp.status_code == 200


# ──────────────────────────── Full Flow ────────────────────────────

class TestFullFlow:
    def test_family_setup_to_archive_flow(self, client):
        """Simulate the complete family setup flow end-to-end."""
        # Step 1: Family member creates elder
        resp = client.post("/elders", json={
            "name": "Grandma Rose",
            "phone_number": "+13105551234",
            "seed_context": "Rose grew up in Brooklyn, taught piano for 40 years, makes the best cheesecake",
            "created_by": "+13105559999",
            "call_schedule": {
                "days": ["tuesday", "thursday"],
                "time": "14:00",
                "timezone": "America/New_York",
            },
        })
        assert resp.status_code == 201
        elder = resp.json()
        elder_id = elder["id"]
        assert elder["name"] == "Grandma Rose"

        # Step 2: Verify elder exists
        resp = client.get(f"/elders/{elder_id}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Grandma Rose"

        # Step 3: Check initial memory is empty
        resp = client.get(f"/elders/{elder_id}/memory")
        assert resp.status_code == 200
        memory = resp.json()
        assert memory["session_count"] == 0

        # Step 4: Check no sessions yet
        resp = client.get(f"/elders/{elder_id}/sessions")
        assert resp.status_code == 200
        assert resp.json() == []

        # Step 5: Update schedule
        resp = client.put(f"/elders/{elder_id}/schedule", json={
            "call_schedule": {
                "days": ["monday", "wednesday", "friday"],
                "time": "10:00",
                "timezone": "America/Los_Angeles",
            },
        })
        assert resp.status_code == 200

        # Verify schedule updated
        resp = client.get(f"/elders/{elder_id}")
        assert resp.status_code == 200
        assert resp.json()["call_schedule"]["days"] == ["monday", "wednesday", "friday"]

    def test_multiple_elders(self, client):
        """Can create and manage multiple elders independently."""
        # Create two elders
        r1 = client.post("/elders", json={
            "name": "Elder One",
            "phone_number": "+11111111111",
            "seed_context": "First elder",
            "created_by": "+10000000000",
        })
        r2 = client.post("/elders", json={
            "name": "Elder Two",
            "phone_number": "+12222222222",
            "seed_context": "Second elder",
            "created_by": "+10000000000",
        })
        assert r1.status_code == 201
        assert r2.status_code == 201

        id1 = r1.json()["id"]
        id2 = r2.json()["id"]
        assert id1 != id2

        # Each elder is independent
        assert client.get(f"/elders/{id1}").json()["name"] == "Elder One"
        assert client.get(f"/elders/{id2}").json()["name"] == "Elder Two"
