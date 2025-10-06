"""
Integration tests for RLS user-scoped model isolation.

These tests verify that users can only access their own data when RLS is enabled.
Tests must fail initially (TDD red phase) before implementation.
"""


import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app import crud
from app.core.config import settings
from app.main import app
from app.models import Item, User, UserCreate


@pytest.fixture
def client():
    """Test client for API requests."""
    return TestClient(app)


@pytest.fixture
def user1(db: Session) -> User:
    """Create first test user."""
    user_in = UserCreate(
        email="user1@example.com", password="password123", full_name="User One"
    )
    return crud.create_user(session=db, user_create=user_in)


@pytest.fixture
def user2(db: Session) -> User:
    """Create second test user."""
    user_in = UserCreate(
        email="user2@example.com", password="password123", full_name="User Two"
    )
    return crud.create_user(session=db, user_create=user_in)


@pytest.fixture
def user1_items(db: Session, user1: User) -> list[Item]:
    """Create items for user1."""
    items = [
        Item(title="User 1 Task 1", description="First task", owner_id=user1.id),
        Item(title="User 1 Task 2", description="Second task", owner_id=user1.id),
    ]
    for item in items:
        db.add(item)
    db.commit()
    db.refresh(items[0])
    db.refresh(items[1])
    return items


@pytest.fixture
def user2_items(db: Session, user2: User) -> list[Item]:
    """Create items for user2."""
    items = [
        Item(title="User 2 Task 1", description="Only task", owner_id=user2.id),
    ]
    for item in items:
        db.add(item)
    db.commit()
    db.refresh(items[0])
    return items


class TestRLSUserIsolation:
    """Test RLS user isolation functionality."""

    def test_user_can_only_see_own_items(
        self,
        client: TestClient,
        user1: User,
        user2: User,
        user1_items: list[Item],
        user2_items: list[Item],
    ):
        """Test that users can only see their own items."""
        # This test should fail initially - no RLS implementation yet
        # RLS is now implemented - test should pass

        # Login as user1
        login_data = {"username": user1.email, "password": "password123"}
        response = client.post("/api/v1/login/access-token", data=login_data)
        assert response.status_code == 200
        user1_token = response.json()["access_token"]

        # Get user1's items - should only see their own
        response = client.get(
            "/api/v1/items/", headers={"Authorization": f"Bearer {user1_token}"}
        )
        assert response.status_code == 200
        items = response.json()["data"]

        # Should only see user1's items
        assert len(items) == 2
        assert all(item["owner_id"] == str(user1.id) for item in items)

        # Login as user2
        login_data = {"username": user2.email, "password": "password123"}
        response = client.post("/api/v1/login/access-token", data=login_data)
        assert response.status_code == 200
        user2_token = response.json()["access_token"]

        # Get user2's items - should only see their own
        response = client.get(
            "/api/v1/items/", headers={"Authorization": f"Bearer {user2_token}"}
        )
        assert response.status_code == 200
        items = response.json()["data"]

        # Should only see user2's items
        assert len(items) == 1
        assert items[0]["owner_id"] == str(user2.id)

    def test_user_cannot_create_item_for_other_user(
        self, client: TestClient, user1: User, user2: User
    ):
        """Test that users cannot create items for other users."""
        # RLS is now implemented - test should pass

        # Login as user1
        login_data = {"username": user1.email, "password": "password123"}
        response = client.post("/api/v1/login/access-token", data=login_data)
        assert response.status_code == 200
        user1_token = response.json()["access_token"]

        # Try to create item with user2's owner_id
        item_data = {
            "title": "Hacked Task",
            "description": "Should not work",
            "owner_id": str(user2.id),  # Trying to create for user2
        }

        response = client.post(
            "/api/v1/items/",
            json=item_data,
            headers={"Authorization": f"Bearer {user1_token}"},
        )

        # Should fail - cannot create items for other users
        assert response.status_code == 403

    def test_user_cannot_update_other_users_items(
        self, client: TestClient, user1: User, user2: User, user2_items: list[Item]
    ):
        """Test that users cannot update other users' items."""
        # RLS is now implemented - test should pass

        # Login as user1
        login_data = {"username": user1.email, "password": "password123"}
        response = client.post("/api/v1/login/access-token", data=login_data)
        assert response.status_code == 200
        user1_token = response.json()["access_token"]

        # Try to update user2's item
        user2_item = user2_items[0]
        update_data = {"title": "Hacked Title"}

        response = client.patch(
            f"/api/v1/items/{user2_item.id}",
            json=update_data,
            headers={"Authorization": f"Bearer {user1_token}"},
        )

        # Should fail - cannot update other users' items
        assert response.status_code == 403

    def test_user_cannot_delete_other_users_items(
        self, client: TestClient, user1: User, user2: User, user2_items: list[Item]
    ):
        """Test that users cannot delete other users' items."""
        # RLS is now implemented - test should pass

        # Login as user1
        login_data = {"username": user1.email, "password": "password123"}
        response = client.post("/api/v1/login/access-token", data=login_data)
        assert response.status_code == 200
        user1_token = response.json()["access_token"]

        # Try to delete user2's item
        user2_item = user2_items[0]

        response = client.delete(
            f"/api/v1/items/{user2_item.id}",
            headers={"Authorization": f"Bearer {user1_token}"},
        )

        # Should fail - cannot delete other users' items
        assert response.status_code == 403

    def test_rls_disabled_allows_cross_user_access(
        self,
        client: TestClient,
        user1: User,
        user2: User,
        user1_items: list[Item],
        user2_items: list[Item],
    ):
        """Test that when RLS is disabled, users can see all items."""
        # RLS is now implemented - test should pass

        # Disable RLS for this test
        original_rls_enabled = settings.RLS_ENABLED
        settings.RLS_ENABLED = False

        try:
            # Login as user1
            login_data = {"username": user1.email, "password": "password123"}
            response = client.post("/api/v1/login/access-token", data=login_data)
            assert response.status_code == 200
            user1_token = response.json()["access_token"]

            # Get items - should see all items when RLS is disabled
            response = client.get(
                "/api/v1/items/", headers={"Authorization": f"Bearer {user1_token}"}
            )
            assert response.status_code == 200
            items = response.json()["data"]

            # Should see all items (3 total: 2 from user1, 1 from user2)
            assert len(items) == 3

        finally:
            # Restore original setting
            settings.RLS_ENABLED = original_rls_enabled
