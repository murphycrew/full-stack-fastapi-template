"""
Integration tests for RLS admin bypass functionality.

These tests verify that admin users can bypass RLS and access all data.
Tests must fail initially (TDD red phase) before implementation.
"""


import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app import crud
from app.main import app
from app.models import Item, User, UserCreate


@pytest.fixture
def client():
    """Test client for API requests."""
    return TestClient(app)


@pytest.fixture
def regular_user(db: Session) -> User:
    """Create regular user."""
    import uuid

    unique_id = str(uuid.uuid4())[:8]
    user_in = UserCreate(
        email=f"regular_{unique_id}@example.com",
        password="password123",
        full_name="Regular User",
    )
    return crud.create_user(session=db, user_create=user_in)


@pytest.fixture
def admin_user(db: Session) -> User:
    """Create admin user."""
    import uuid

    unique_id = str(uuid.uuid4())[:8]
    user_in = UserCreate(
        email=f"admin_{unique_id}@example.com",
        password="password123",
        full_name="Admin User",
        is_superuser=True,
    )
    return crud.create_user(session=db, user_create=user_in)


@pytest.fixture
def regular_user_items(db: Session, regular_user: User) -> list[Item]:
    """Create items for regular user."""
    items = [
        Item(
            title="Regular Task 1", description="First task", owner_id=regular_user.id
        ),
        Item(
            title="Regular Task 2", description="Second task", owner_id=regular_user.id
        ),
    ]
    for item in items:
        db.add(item)
        db.commit()
    for item in items:
        db.refresh(item)
    return items


@pytest.fixture
def admin_user_items(db: Session, admin_user: User) -> list[Item]:
    """Create items for admin user."""
    items = [
        Item(title="Admin Task", description="Admin task", owner_id=admin_user.id),
    ]
    for item in items:
        db.add(item)
        db.commit()
    db.refresh(items[0])
    return items


class TestRLSAdminBypass:
    """Test RLS admin bypass functionality."""

    def test_admin_can_see_all_items(
        self,
        client: TestClient,
        admin_user: User,
        regular_user: User,
        regular_user_items: list[Item],
        admin_user_items: list[Item],
    ):
        """Test that admin users can see all items regardless of owner."""
        # RLS is now implemented - test should pass

        # Login as admin
        login_data = {"username": admin_user.email, "password": "password123"}
        response = client.post("/api/v1/login/access-token", data=login_data)
        assert response.status_code == 200
        admin_token = response.json()["access_token"]

        # Get all items - admin should see everything
        response = client.get(
            "/api/v1/items/", headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        items = response.json()["data"]

        # Should see all items (3 total: 2 from regular user, 1 from admin)
        assert len(items) == 3

        # Verify items from both users are present
        owner_ids = {item["owner_id"] for item in items}
        assert str(regular_user.id) in owner_ids
        assert str(admin_user.id) in owner_ids

    def test_admin_can_create_items_for_any_user(
        self, client: TestClient, admin_user: User, regular_user: User
    ):
        """Test that admin users can create items for any user."""
        # RLS is now implemented - test should pass

        # Login as admin
        login_data = {"username": admin_user.email, "password": "password123"}
        response = client.post("/api/v1/login/access-token", data=login_data)
        assert response.status_code == 200
        admin_token = response.json()["access_token"]

        # Create item for regular user using admin endpoint
        item_data = {
            "title": "Admin Created Task",
            "description": "Created by admin for regular user",
        }

        response = client.post(
            f"/api/v1/items/admin/?owner_id={regular_user.id}",
            json=item_data,
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # Should succeed - admin can create items for any user
        assert response.status_code == 200
        created_item = response.json()
        assert created_item["owner_id"] == str(regular_user.id)

    def test_admin_can_update_any_users_items(
        self, client: TestClient, admin_user: User, regular_user_items: list[Item]
    ):
        """Test that admin users can update any user's items."""
        # RLS is now implemented - test should pass

        # Login as admin
        login_data = {"username": admin_user.email, "password": "password123"}
        response = client.post("/api/v1/login/access-token", data=login_data)
        assert response.status_code == 200
        admin_token = response.json()["access_token"]

        # Update regular user's item
        regular_item = regular_user_items[0]
        update_data = {"title": "Updated by Admin"}

        response = client.put(
            f"/api/v1/items/admin/{regular_item.id}",
            json=update_data,
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # Should succeed - admin can update any user's items
        assert response.status_code == 200
        updated_item = response.json()
        assert updated_item["title"] == "Updated by Admin"

    def test_admin_can_delete_any_users_items(
        self, client: TestClient, admin_user: User, regular_user_items: list[Item]
    ):
        """Test that admin users can delete any user's items."""
        # RLS is now implemented - test should pass

        # Login as admin
        login_data = {"username": admin_user.email, "password": "password123"}
        response = client.post("/api/v1/login/access-token", data=login_data)
        assert response.status_code == 200
        admin_token = response.json()["access_token"]

        # Delete regular user's item
        regular_item = regular_user_items[0]

        response = client.delete(
            f"/api/v1/items/{regular_item.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # Should succeed - admin can delete any user's items
        assert response.status_code == 200

    def test_admin_can_see_all_and_modify_items(
        self,
        client: TestClient,
        admin_user: User,
        regular_user: User,
        regular_user_items: list[Item],
    ):
        """Test that admin users can see all items and modify them."""
        # RLS is now implemented - test should pass

        # Login as admin
        login_data = {"username": admin_user.email, "password": "password123"}
        response = client.post("/api/v1/login/access-token", data=login_data)
        assert response.status_code == 200
        admin_token = response.json()["access_token"]

        # Should be able to read all items using admin endpoint
        response = client.get(
            "/api/v1/items/admin/all",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        items = response.json()["data"]
        assert len(items) == 2  # All regular user items

        # Should be able to create items (admin has full permissions)
        item_data = {
            "title": "Admin Created Item",
            "description": "Admin can create items for any user",
        }

        response = client.post(
            f"/api/v1/items/admin/?owner_id={regular_user.id}",
            json=item_data,
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # Should succeed - admin has full permissions
        assert response.status_code == 200
        created_item = response.json()
        assert created_item["owner_id"] == str(regular_user.id)

    def test_regular_user_cannot_bypass_rls_even_with_admin_endpoints(
        self,
        client: TestClient,
        regular_user: User,
        admin_user: User,
        admin_user_items: list[Item],
    ):
        """Test that regular users cannot access admin-only endpoints."""
        # RLS is now implemented - test should pass

        # Login as regular user
        login_data = {"username": regular_user.email, "password": "password123"}
        response = client.post("/api/v1/login/access-token", data=login_data)
        assert response.status_code == 200
        regular_token = response.json()["access_token"]

        # Try to access admin-only endpoint to see all items
        response = client.get(
            "/api/v1/items/admin/all",
            headers={"Authorization": f"Bearer {regular_token}"},
        )

        # Should fail - regular users cannot access admin endpoints
        assert response.status_code == 403
