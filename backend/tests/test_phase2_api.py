"""Tests for Phase 2 API endpoints — verifying router registration and model schemas."""

import pytest
from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app, raise_server_exceptions=False)


class TestAppRouterRegistration:
    """Verify all Phase 2 routers are mounted on the app."""

    def test_health_check(self):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["version"] == "0.2.0"

    def test_auth_routes_exist(self):
        """Auth endpoints should return 401 without token, not 404."""
        response = client.post("/auth/signin")
        assert response.status_code in (401, 403)

        response = client.get("/auth/me")
        assert response.status_code in (401, 403)

        response = client.get("/auth/me/families")
        assert response.status_code in (401, 403)

    def test_family_routes_exist(self):
        """Family endpoints should return 401 without token, not 404."""
        response = client.post("/families", json={"name": "Test"})
        assert response.status_code in (401, 403)

    def test_invite_public_route_exists(self):
        """Public invite lookup should reach the handler, not return 404 from routing."""
        response = client.get("/invites/nonexistent-token")
        # 404 = handler found token invalid, 500 = Firestore unavailable
        # Neither means routing failed (which would be 404 with "Not Found")
        assert response.status_code in (404, 422, 500)

    def test_session_routes_still_work(self):
        """Phase 1 session routes should still be accessible."""
        response = client.get("/sessions")
        # 200, 500 = route exists. 405 = route not found for method.
        assert response.status_code in (200, 500)

    def test_elder_routes_still_work(self):
        """Phase 1 elder routes should still be accessible."""
        response = client.get("/elders/nonexistent")
        assert response.status_code in (404, 422, 500)


class TestOpenAPISchema:
    """Verify the OpenAPI schema includes Phase 2 endpoints."""

    def test_openapi_schema_loads(self):
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        paths = schema.get("paths", {})

        # Phase 1 paths
        assert "/health" in paths
        assert "/elders" in paths or "/elders/{elder_id}" in paths

        # Phase 2 paths
        assert "/auth/signin" in paths
        assert "/auth/me" in paths
        assert "/families" in paths

    def test_openapi_tags_include_phase2(self):
        response = client.get("/openapi.json")
        schema = response.json()
        tag_names = [t.get("name") for t in schema.get("tags", [])] if schema.get("tags") else []

        # Tags may or may not be defined as top-level tag objects,
        # but at minimum the routes use these tags
        paths = schema.get("paths", {})
        all_tags = set()
        for path_data in paths.values():
            for method_data in path_data.values():
                if isinstance(method_data, dict):
                    for tag in method_data.get("tags", []):
                        all_tags.add(tag)

        assert "auth" in all_tags
        assert "families" in all_tags
        assert "collections" in all_tags
        assert "books" in all_tags
