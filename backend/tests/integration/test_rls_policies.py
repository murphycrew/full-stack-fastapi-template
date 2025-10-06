"""
Integration tests for RLS policy enforcement.

These tests verify that RLS policies are properly enforced at the database level.
Tests must fail initially (TDD red phase) before implementation.
"""


import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select, text

from app import crud
from app.core.config import settings
from app.models import Item, User, UserCreate


@pytest.fixture
def user1(session: Session) -> User:
    """Create first test user."""
    user_in = UserCreate(
        email="user1@example.com", password="password123", full_name="User One"
    )
    return crud.create_user(session=session, user_create=user_in)


@pytest.fixture
def user2(session: Session) -> User:
    """Create second test user."""
    user_in = UserCreate(
        email="user2@example.com", password="password123", full_name="User Two"
    )
    return crud.create_user(session=session, user_create=user_in)


@pytest.fixture
def user1_items(session: Session, user1: User) -> list[Item]:
    """Create items for user1."""
    items = [
        Item(title="User 1 Task 1", description="First task", owner_id=user1.id),
        Item(title="User 1 Task 2", description="Second task", owner_id=user1.id),
    ]
    for item in items:
        session.add(item)
    session.commit()
    for item in items:
        session.refresh(item)
    return items


@pytest.fixture
def user2_items(session: Session, user2: User) -> list[Item]:
    """Create items for user2."""
    items = [
        Item(title="User 2 Task 1", description="Only task", owner_id=user2.id),
    ]
    for item in items:
        session.add(item)
    session.commit()
    session.refresh(items[0])
    return items


class TestRLSPolicyEnforcement:
    """Test RLS policy enforcement at database level."""

    def test_rls_policies_enabled_on_item_table(self, session: Session):
        """Test that RLS policies are enabled on the item table."""
        # RLS is now implemented - test should pass

        # Check if RLS is enabled on the item table
        query = text(
            """
            SELECT relrowsecurity
            FROM pg_class
            WHERE relname = 'item'
        """
        )

        result = session.exec(query).first()
        assert result is not None
        assert result[0] is True, "RLS should be enabled on item table"

    def test_rls_policies_created_for_item_table(self, session: Session):
        """Test that RLS policies are created for the item table."""
        # RLS is now implemented - test should pass

        # Check if RLS policies exist for the item table
        query = text(
            """
            SELECT policyname, cmd, qual
            FROM pg_policies
            WHERE tablename = 'item'
            ORDER BY policyname
        """
        )

        result = session.exec(query).all()

        # Should have policies for SELECT, INSERT, UPDATE, DELETE
        policy_names = {row[0] for row in result}
        expected_policies = {
            "item_select_policy",
            "item_insert_policy",
            "item_update_policy",
            "item_delete_policy",
        }

        assert (
            policy_names == expected_policies
        ), f"Missing policies: {expected_policies - policy_names}"

    def test_rls_policy_prevents_cross_user_select(
        self,
        session: Session,
        user1: User,
        user2: User,
        user1_items: list[Item],
        user2_items: list[Item],
    ):
        """Test that RLS policies prevent users from selecting other users' items."""
        # RLS is now implemented - test should pass

        # Set session variable for user1
        session.exec(text("SET app.user_id = :user_id"), {"user_id": str(user1.id)})
        session.exec(text("SET app.role = 'user'"))

        # Query items as user1 - should only see user1's items
        query = select(Item)
        result = session.exec(query).all()

        assert len(result) == 2  # Only user1's items
        assert all(item.owner_id == user1.id for item in result)

        # Set session variable for user2
        session.exec(text("SET app.user_id = :user_id"), {"user_id": str(user2.id)})

        # Query items as user2 - should only see user2's items
        result = session.exec(query).all()

        assert len(result) == 1  # Only user2's items
        assert all(item.owner_id == user2.id for item in result)

    def test_rls_policy_prevents_cross_user_insert(
        self, session: Session, user1: User, user2: User
    ):
        """Test that RLS policies prevent users from inserting items for other users."""
        # RLS is now implemented - test should pass

        # Set session variable for user1
        session.exec(text("SET app.user_id = :user_id"), {"user_id": str(user1.id)})
        session.exec(text("SET app.role = 'user'"))

        # Try to insert item with user2's owner_id
        item = Item(
            title="Hacked Task", description="Should not work", owner_id=user2.id
        )

        session.add(item)

        # Should fail due to RLS policy
        with pytest.raises(
            (IntegrityError, ValueError)
        ):  # More specific exception handling
            session.commit()

    def test_rls_policy_prevents_cross_user_update(
        self, session: Session, user1: User, user2: User, user2_items: list[Item]
    ):
        """Test that RLS policies prevent users from updating other users' items."""
        # RLS is now implemented - test should pass

        # Set session variable for user1
        session.exec(text("SET app.user_id = :user_id"), {"user_id": str(user1.id)})
        session.exec(text("SET app.role = 'user'"))

        # Try to update user2's item
        user2_item = user2_items[0]
        user2_item.title = "Hacked Title"

        # Should fail due to RLS policy
        with pytest.raises(
            (IntegrityError, ValueError)
        ):  # More specific exception handling
            session.commit()

    def test_rls_policy_prevents_cross_user_delete(
        self, session: Session, user1: User, user2_items: list[Item]
    ):
        """Test that RLS policies prevent users from deleting other users' items."""
        # RLS is now implemented - test should pass

        # Set session variable for user1
        session.exec(text("SET app.user_id = :user_id"), {"user_id": str(user1.id)})
        session.exec(text("SET app.role = 'user'"))

        # Try to delete user2's item
        user2_item = user2_items[0]
        session.delete(user2_item)

        # Should fail due to RLS policy
        with pytest.raises(
            (IntegrityError, ValueError)
        ):  # More specific exception handling
            session.commit()

    def test_admin_role_bypasses_rls_policies(
        self,
        session: Session,
        user1: User,
        user2: User,
        user1_items: list[Item],
        user2_items: list[Item],
    ):
        """Test that admin role bypasses RLS policies."""
        # RLS is now implemented - test should pass

        # Set session variable for admin role
        session.exec(text("SET app.role = 'admin'"))

        # Query items as admin - should see all items
        query = select(Item)
        result = session.exec(query).all()

        assert len(result) == 3  # All items from both users
        owner_ids = {item.owner_id for item in result}
        assert user1.id in owner_ids
        assert user2.id in owner_ids

    def test_read_only_admin_role_has_select_only_access(
        self, session: Session, user1: User, user2: User, user2_items: list[Item]
    ):
        """Test that read-only admin role can only select, not modify."""
        # RLS is now implemented - test should pass

        # Set session variable for read-only admin role
        session.exec(text("SET app.role = 'read_only_admin'"))

        # Should be able to select all items
        query = select(Item)
        result = session.exec(query).all()
        assert len(result) == 3  # All items

        # Should NOT be able to insert new items
        item = Item(
            title="Should Not Work",
            description="Read-only admin cannot insert",
            owner_id=user1.id,
        )

        session.add(item)

        # Should fail due to read-only policy
        with pytest.raises((IntegrityError, ValueError)):
            session.commit()

    def test_rls_force_setting_enforces_policies_for_all_roles(
        self,
        session: Session,
        user1: User,
        user2: User,
        user1_items: list[Item],
        user2_items: list[Item],
    ):
        """Test that RLS_FORCE setting enforces policies even for privileged roles."""
        # RLS is now implemented - test should pass

        # Enable RLS_FORCE
        original_rls_force = settings.RLS_FORCE
        settings.RLS_FORCE = True

        try:
            # Set session variable for admin role
            session.exec(text("SET app.role = 'admin'"))

            # Even admin should be subject to RLS when RLS_FORCE is enabled
            # This would require setting a user_id for the admin
            session.exec(text("SET app.user_id = :user_id"), {"user_id": str(user1.id)})

            # Query items - should only see user1's items due to RLS_FORCE
            query = select(Item)
            result = session.exec(query).all()

            assert len(result) == 2  # Only user1's items
            assert all(item.owner_id == user1.id for item in result)

        finally:
            # Restore original setting
            settings.RLS_FORCE = original_rls_force

    def test_rls_disabled_allows_unrestricted_access(
        self,
        session: Session,
        user1: User,
        user2: User,
        user1_items: list[Item],
        user2_items: list[Item],
    ):
        """Test that when RLS is disabled, all users can access all data."""
        # RLS is now implemented - test should pass

        # Disable RLS
        original_rls_enabled = settings.RLS_ENABLED
        settings.RLS_ENABLED = False

        try:
            # Set session variable for user1
            session.exec(text("SET app.user_id = :user_id"), {"user_id": str(user1.id)})
            session.exec(text("SET app.role = 'user'"))

            # Query items - should see all items when RLS is disabled
            query = select(Item)
            result = session.exec(query).all()

            assert len(result) == 3  # All items from both users
            owner_ids = {item.owner_id for item in result}
            assert user1.id in owner_ids
            assert user2.id in owner_ids

        finally:
            # Restore original setting
            settings.RLS_ENABLED = original_rls_enabled
