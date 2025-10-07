"""
Performance tests for RLS policies.

These tests measure the performance impact of RLS policies on database operations
to ensure they don't significantly degrade application performance.
"""

import time

import pytest
from sqlalchemy import text
from sqlmodel import Session, select

from app import crud
from app.core.rls import AdminContext
from app.models import Item, User, UserCreate


@pytest.fixture
def performance_users(db: Session) -> list[User]:
    """Create multiple users for performance testing."""
    import uuid

    users = []
    for i in range(10):
        # Use unique identifier to avoid conflicts across test runs
        unique_id = str(uuid.uuid4())[:8]
        user_in = UserCreate(
            email=f"perf_user_{i}_{unique_id}@example.com",
            password="password123",
            full_name=f"Performance User {i}",
        )
        user = crud.create_user(session=db, user_create=user_in)
        users.append(user)
    return users


@pytest.fixture
def performance_items(db: Session, performance_users: list[User]) -> list[Item]:
    """Create multiple items for performance testing."""
    items = []
    for i, user in enumerate(performance_users):
        for j in range(5):  # 5 items per user
            item = Item(
                title=f"Performance Item {i}-{j}",
                description=f"Performance test item {i}-{j}",
                owner_id=user.id,
            )
            db.add(item)
            items.append(item)
    db.commit()
    for item in items:
        db.refresh(item)
    return items


class TestRLSPerformance:
    """Test RLS performance impact."""

    def test_rls_select_performance(
        self, db: Session, performance_users: list[User], performance_items: list[Item]
    ):
        """Test performance of RLS-enabled SELECT operations."""
        user = performance_users[0]

        # Set RLS context
        db.execute(text(f"SET app.user_id = '{user.id}'"))
        db.execute(text("SET app.role = 'user'"))

        # Measure RLS-enabled query performance
        start_time = time.perf_counter()

        statement = select(Item).where(Item.owner_id == user.id)
        items = db.exec(statement).all()

        end_time = time.perf_counter()
        rls_time = end_time - start_time

        # Verify we got the expected items (5 items for user 0)
        assert len(items) == 5
        assert all(item.owner_id == user.id for item in items)

        # RLS query should complete within reasonable time (adjust threshold as needed)
        assert rls_time < 0.1, f"RLS query took {rls_time:.4f}s, which is too slow"

        # Performance logging for debugging
        # print(f"RLS SELECT query time: {rls_time:.4f}s for {len(items)} items")

    def test_rls_insert_performance(self, db: Session, performance_users: list[User]):
        """Test performance of RLS-enabled INSERT operations."""
        user = performance_users[0]

        # Set RLS context
        db.execute(text(f"SET app.user_id = '{user.id}'"))
        db.execute(text("SET app.role = 'user'"))

        # Measure RLS-enabled insert performance
        start_time = time.perf_counter()

        item = Item(
            title="Performance Test Insert",
            description="Testing RLS insert performance",
            owner_id=user.id,
        )
        db.add(item)
        db.commit()
        db.refresh(item)

        end_time = time.perf_counter()
        rls_time = end_time - start_time

        # Verify the item was created
        assert item.id is not None
        assert item.owner_id == user.id

        # RLS insert should complete within reasonable time
        assert rls_time < 0.2, f"RLS insert took {rls_time:.4f}s, which is too slow"

        # Performance logging: print(f"RLS INSERT operation time: {rls_time:.4f}s")

    def test_rls_update_performance(
        self, db: Session, performance_users: list[User], performance_items: list[Item]
    ):
        """Test performance of RLS-enabled UPDATE operations."""
        user = performance_users[0]
        user_items = [item for item in performance_items if item.owner_id == user.id]
        item = user_items[0]

        # Set RLS context
        db.execute(text(f"SET app.user_id = '{user.id}'"))
        db.execute(text("SET app.role = 'user'"))

        # Measure RLS-enabled update performance
        start_time = time.perf_counter()

        item.title = "Updated Performance Test Item"
        db.add(item)
        db.commit()
        db.refresh(item)

        end_time = time.perf_counter()
        rls_time = end_time - start_time

        # Verify the item was updated
        assert item.title == "Updated Performance Test Item"

        # RLS update should complete within reasonable time
        assert rls_time < 0.2, f"RLS update took {rls_time:.4f}s, which is too slow"

        # Performance logging: print(f"RLS UPDATE operation time: {rls_time:.4f}s")

    def test_rls_delete_performance(
        self, db: Session, performance_users: list[User], performance_items: list[Item]
    ):
        """Test performance of RLS-enabled DELETE operations."""
        user = performance_users[0]
        user_items = [item for item in performance_items if item.owner_id == user.id]
        item = user_items[0]

        # Set RLS context
        db.execute(text(f"SET app.user_id = '{user.id}'"))
        db.execute(text("SET app.role = 'user'"))

        # Measure RLS-enabled delete performance
        start_time = time.perf_counter()

        db.delete(item)
        db.commit()

        end_time = time.perf_counter()
        rls_time = end_time - start_time

        # Verify the item was deleted
        deleted_item = db.get(Item, item.id)
        assert deleted_item is None

        # RLS delete should complete within reasonable time
        assert rls_time < 0.2, f"RLS delete took {rls_time:.4f}s, which is too slow"

        # Performance logging: print(f"RLS DELETE operation time: {rls_time:.4f}s")

    def test_admin_context_performance(
        self, db: Session, performance_users: list[User], performance_items: list[Item]
    ):
        """Test performance of admin context operations."""
        admin_user = performance_users[0]

        # Measure admin context performance
        start_time = time.perf_counter()

        with AdminContext.create_full_admin(admin_user.id, db):
            # Admin can see all items
            statement = select(Item)
            all_items = db.exec(statement).all()

        end_time = time.perf_counter()
        admin_time = end_time - start_time

        # Verify admin saw all items
        # Note: This test may see items from other tests due to shared database session
        assert (
            len(all_items) >= len(performance_items) - 1
        )  # At least the items we created, minus any deleted

        # Admin operations should complete within reasonable time
        assert (
            admin_time < 0.2
        ), f"Admin context operation took {admin_time:.4f}s, which is too slow"

        # Performance logging: print(f"Admin context operation time: {admin_time:.4f}s")

    def test_rls_vs_no_rls_performance_comparison(
        self, db: Session, performance_users: list[User], performance_items: list[Item]
    ):
        """Compare performance of RLS-enabled vs non-RLS operations."""
        user = performance_users[0]

        # Test with RLS enabled
        db.execute(text(f"SET app.user_id = '{user.id}'"))
        db.execute(text("SET app.role = 'user'"))

        start_time = time.perf_counter()
        statement = select(Item).where(Item.owner_id == user.id)
        rls_items = db.exec(statement).all()
        rls_time = time.perf_counter() - start_time

        # Test without RLS (admin context)
        db.execute(text("SET app.role = 'admin'"))

        start_time = time.perf_counter()
        statement = select(Item).where(Item.owner_id == user.id)
        no_rls_items = db.exec(statement).all()
        no_rls_time = time.perf_counter() - start_time

        # Both should return the same items
        assert len(rls_items) == len(no_rls_items)

        # Calculate performance overhead
        overhead = rls_time - no_rls_time
        overhead_percentage = (overhead / no_rls_time) * 100 if no_rls_time > 0 else 0

        # Performance logging:
        # print(f"RLS query time: {rls_time:.4f}s")
        # print(f"No-RLS query time: {no_rls_time:.4f}s")
        # print(f"RLS overhead: {overhead:.4f}s ({overhead_percentage:.1f}%)")

        # RLS overhead should be reasonable (adjust threshold as needed)
        assert (
            overhead_percentage < 70
        ), f"RLS overhead is too high: {overhead_percentage:.1f}%"

    def test_concurrent_rls_performance(
        self, db: Session, performance_users: list[User], performance_items: list[Item]
    ):
        """Test performance under concurrent RLS operations."""
        import concurrent.futures

        def rls_query_task(user_id: str, db_factory):
            """Task that performs RLS queries for a specific user."""
            with db_factory() as task_db:
                task_db.execute(text(f"SET app.user_id = '{user_id}'"))
                task_db.execute(text("SET app.role = 'user'"))

                statement = select(Item).where(Item.owner_id == user_id)
                items = task_db.exec(statement).all()
                return len(items)

        # Create db factory for thread safety
        def db_factory():
            return Session(db.bind)

        # Run concurrent queries for different users
        start_time = time.perf_counter()

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            for user in performance_users[:5]:  # Test with 5 concurrent users
                future = executor.submit(rls_query_task, str(user.id), db_factory)
                futures.append(future)

            results = [future.result() for future in futures]

        end_time = time.perf_counter()
        concurrent_time = end_time - start_time

        # Verify all queries returned expected results
        assert all(
            result == 5 for result in results
        ), "Concurrent queries returned unexpected results"

        # Performance logging: print(f"Concurrent RLS operations time: {concurrent_time:.4f}s for 5 users")

        # Concurrent operations should complete within reasonable time
        assert (
            concurrent_time < 1.0
        ), f"Concurrent RLS operations took {concurrent_time:.4f}s, which is too slow"

    def test_rls_policy_complexity_performance(
        self, db: Session, performance_users: list[User]
    ):
        """Test performance with complex RLS policies and large datasets."""
        # Create a larger dataset for complexity testing
        large_items = []
        for user in performance_users:
            for i in range(20):  # 20 items per user
                item = Item(
                    title=f"Complex Item {user.id}-{i}",
                    description=f"Complex performance test item {user.id}-{i}",
                    owner_id=user.id,
                )
                db.add(item)
                large_items.append(item)
        db.commit()
        for item in large_items:
            db.refresh(item)

        # Test complex query with RLS
        user = performance_users[0]
        db.execute(text(f"SET app.user_id = '{user.id}'"))
        db.execute(text("SET app.role = 'user'"))

        start_time = time.perf_counter()

        # Complex query with multiple conditions
        statement = (
            select(Item)
            .where(Item.owner_id == user.id)
            .where(Item.title.like("%Complex%"))
            .order_by(Item.title)
        )
        complex_items = db.exec(statement).all()

        end_time = time.perf_counter()
        complex_time = end_time - start_time

        # Verify results
        assert len(complex_items) == 20  # 20 items for the user
        assert all(item.owner_id == user.id for item in complex_items)

        # Performance logging:
        # print(f"Complex RLS query time: {complex_time:.4f}s for {len(complex_items)} items")

        # Complex queries should still complete within reasonable time
        assert (
            complex_time < 0.5
        ), f"Complex RLS query took {complex_time:.4f}s, which is too slow"
