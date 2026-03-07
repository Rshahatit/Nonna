"""Tests for Phase 2 data models."""

import pytest
from datetime import datetime, timezone
from app.models.user import (
    UserResponse, FamilyCreate, FamilyResponse, FamilyMemberResponse,
    FamilyMemberUpdate, NotificationPrefs, InviteCreate, InviteResponse,
    CollectionCreate, CollectionResponse, CollectionUpdate, MomentRef,
    ThreadResponse, BookCreate, BookResponse,
)
from app.models.session import MomentResponse


class TestUserModels:
    def test_user_response(self):
        user = UserResponse(
            id="uid1", email="test@example.com", name="Test User",
            photo_url="https://photo.url", provider="google",
            created_at=datetime.now(timezone.utc),
        )
        assert user.id == "uid1"
        assert user.email == "test@example.com"
        assert user.provider == "google"

    def test_notification_prefs_defaults(self):
        prefs = NotificationPrefs()
        assert prefs.reel_ready is True
        assert prefs.missed_calls is True
        assert prefs.weekly_digest is False
        assert prefs.channel == "sms"

    def test_notification_prefs_custom(self):
        prefs = NotificationPrefs(
            reel_ready=False, weekly_digest=True, channel="email",
        )
        assert prefs.reel_ready is False
        assert prefs.weekly_digest is True
        assert prefs.channel == "email"


class TestFamilyModels:
    def test_family_create(self):
        fc = FamilyCreate(name="The Haddad Family")
        assert fc.name == "The Haddad Family"

    def test_family_create_validation(self):
        with pytest.raises(Exception):
            FamilyCreate(name="")

    def test_family_response(self):
        fr = FamilyResponse(
            id="fam1", name="Test Family", created_by="user1",
            created_at=datetime.now(timezone.utc),
            elder_ids=["elder1", "elder2"],
        )
        assert len(fr.elder_ids) == 2

    def test_family_member_response(self):
        fm = FamilyMemberResponse(
            user_id="user1", role="organizer",
            joined_at=datetime.now(timezone.utc),
        )
        assert fm.role == "organizer"
        assert fm.notification_prefs.reel_ready is True

    def test_family_member_update_partial(self):
        update = FamilyMemberUpdate(role="viewer")
        assert update.role == "viewer"
        assert update.notification_prefs is None

    def test_family_member_update_prefs_only(self):
        update = FamilyMemberUpdate(
            notification_prefs=NotificationPrefs(weekly_digest=True),
        )
        assert update.role is None
        assert update.notification_prefs.weekly_digest is True


class TestInviteModels:
    def test_invite_create_defaults(self):
        ic = InviteCreate()
        assert ic.email is None
        assert ic.role == "member"
        assert ic.expires_in_days == 7

    def test_invite_create_custom(self):
        ic = InviteCreate(email="test@test.com", role="viewer", expires_in_days=14)
        assert ic.email == "test@test.com"
        assert ic.role == "viewer"

    def test_invite_response(self):
        ir = InviteResponse(
            id="inv1", family_id="fam1", role="member",
            token="abc123", created_by="user1",
            created_at=datetime.now(timezone.utc),
            family_name="Test Family", inviter_name="Alice",
        )
        assert ir.status == "pending"
        assert ir.redeemed_at is None


class TestCollectionModels:
    def test_moment_ref(self):
        ref = MomentRef(session_id="s1", moment_id="m1")
        assert ref.session_id == "s1"

    def test_collection_create(self):
        cc = CollectionCreate(name="Grandma's Kitchen")
        assert cc.description == ""

    def test_collection_response(self):
        cr = CollectionResponse(
            id="coll1", family_id="fam1", elder_id="e1",
            name="Test", created_by="u1",
            created_at=datetime.now(timezone.utc),
            moment_refs=[MomentRef(session_id="s1", moment_id="m1")],
        )
        assert len(cr.moment_refs) == 1
        assert cr.is_public is False

    def test_collection_update(self):
        cu = CollectionUpdate(name="Updated", is_public=True)
        assert cu.name == "Updated"
        assert cu.description is None


class TestThreadModels:
    def test_thread_response(self):
        tr = ThreadResponse(
            id="t1", family_id="fam1", elder_id="e1",
            type="person", name="Brother Samir",
            generated_at=datetime.now(timezone.utc),
            session_count=3,
            moment_refs=[
                MomentRef(session_id="s1", moment_id="m1"),
                MomentRef(session_id="s2", moment_id="m2"),
            ],
        )
        assert tr.type == "person"
        assert len(tr.moment_refs) == 2


class TestBookModels:
    def test_book_create(self):
        bc = BookCreate(title="Grandma's Stories", elder_id="e1")
        assert bc.source_type == "sessions"
        assert bc.source_ids == []

    def test_book_response(self):
        br = BookResponse(
            id="b1", family_id="fam1", elder_id="e1",
            title="Test Book", created_by="u1",
            created_at=datetime.now(timezone.utc),
        )
        assert br.status == "generating"
        assert br.page_count == 0


class TestMomentResponsePhase2Fields:
    def test_moment_with_tags(self):
        m = MomentResponse(
            id="m1", title="Test", summary="Sum", quote="Q",
            visual_description="VD", emotional_tone="joy",
            tags=["recipe", "family_history"],
            people_mentioned=["Samir", "Mother"],
            place_mentioned="Amman",
        )
        assert "recipe" in m.tags
        assert len(m.people_mentioned) == 2
        assert m.place_mentioned == "Amman"

    def test_moment_backward_compatible(self):
        """Phase 1 moments without new fields should still work."""
        m = MomentResponse(
            id="m1", title="Test", summary="Sum", quote="Q",
            visual_description="VD", emotional_tone="joy",
        )
        assert m.tags == []
        assert m.people_mentioned == []
        assert m.place_mentioned is None
