# Quickstart: Tenant Isolation via Automatic Row-Level Security (RLS) - Internal Infrastructure

**Feature**: 002-tenant-isolation-via | **Date**: 2024-12-19 | **Updated**: 2024-12-19

## Overview

This quickstart demonstrates how to use the automatic Row-Level Security (RLS) system for tenant isolation in the FastAPI template. The system provides database-level data isolation that cannot be bypassed by application bugs.

## Prerequisites

- PostgreSQL 9.5+ (RLS support required)
- FastAPI template with RLS feature enabled
- Docker Compose environment running

## Step 1: Enable RLS

RLS is enabled by default in the template. Verify configuration:

```bash
# Check RLS status
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
  http://localhost:8000/api/v1/rls/status
```

Expected response:
```json
{
  "enabled": true,
  "force_enabled": true,
  "active_policies": 2,
  "scoped_models_count": 1
}
```

## Step 2: Create a User-Scoped Model

Create a new model that inherits from `UserScopedBase`:

```python
# backend/app/models.py
from app.core.rls import UserScopedBase

class Task(UserScopedBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    completed: bool = False
    # owner_id is automatically provided by UserScopedBase
```

## Step 3: Generate Migration

Create and run migration to enable RLS on the new model:

```bash
# Generate migration
cd backend
alembic revision --autogenerate -m "Add Task model with RLS"

# Run migration (automatically creates RLS policies)
alembic upgrade head
```

## Step 4: Test Data Isolation

### Create Test Users

```python
# Create two test users
user1 = create_test_user(email="user1@example.com")
user2 = create_test_user(email="user2@example.com")
```

### Create User-Scoped Data

```python
# Create tasks for user1
task1 = Task(title="User 1 Task", owner_id=user1.id)
task2 = Task(title="User 1 Another Task", owner_id=user1.id)

# Create task for user2
task3 = Task(title="User 2 Task", owner_id=user2.id)

# Save to database
session.add_all([task1, task2, task3])
session.commit()
```

### Verify Isolation

```python
# Login as user1
user1_token = authenticate_user("user1@example.com", "password")

# Get user1's tasks (should see only their tasks)
response = client.get("/api/v1/tasks/", headers={"Authorization": f"Bearer {user1_token}"})
assert response.status_code == 200
tasks = response.json()["data"]
assert len(tasks) == 2
assert all(task["owner_id"] == str(user1.id) for task in tasks)

# Login as user2
user2_token = authenticate_user("user2@example.com", "password")

# Get user2's tasks (should see only their tasks)
response = client.get("/api/v1/tasks/", headers={"Authorization": f"Bearer {user2_token}"})
assert response.status_code == 200
tasks = response.json()["data"]
assert len(tasks) == 1
assert tasks[0]["owner_id"] == str(user2.id)
```

## Step 5: Test Admin Modes

### User-Level Admin Access

```python
# Create admin user
admin_user = create_test_user(email="admin@example.com", is_superuser=True)
admin_token = authenticate_user("admin@example.com", "password")

# Admin can see all tasks
response = client.get("/api/v1/tasks/", headers={"Authorization": f"Bearer {admin_token}"})
assert response.status_code == 200
tasks = response.json()["data"]
assert len(tasks) == 3  # All tasks from both users
```

### Read-Only Admin Access

```python
# Set read-only admin context
admin_context = {
    "role": "read_only_admin",
    "duration_minutes": 60
}

response = client.post(
    "/api/v1/rls/admin/context",
    headers={"Authorization": f"Bearer {admin_token}"},
    json=admin_context
)
assert response.status_code == 200

# Read-only admin can view but not modify
response = client.get("/api/v1/tasks/", headers={"Authorization": f"Bearer {admin_token}"})
assert response.status_code == 200

# Attempt to create task should fail
task_data = {"title": "Admin Task"}
response = client.post(
    "/api/v1/tasks/",
    headers={"Authorization": f"Bearer {admin_token}"},
    json=task_data
)
assert response.status_code == 403
```

## Step 6: Test CI Validation

Run the model validation to ensure RLS compliance:

```bash
# Run RLS model validation
curl -X POST \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  http://localhost:8000/api/v1/rls/validate/models
```

Expected response for compliant models:
```json
{
  "valid": true,
  "violations": [],
  "count": 0
}
```

## Step 7: Test Background Operations

### Set Admin Context for Background Job

```python
# Background job that needs admin access
def cleanup_old_tasks():
    # Set admin context for maintenance operation
    admin_context = {
        "role": "admin",
        "duration_minutes": 10
    }

    response = client.post(
        "/api/v1/rls/admin/context",
        headers={"Authorization": f"Bearer {admin_token}"},
        json=admin_context
    )
    assert response.status_code == 200

    # Now can access all tasks for cleanup
    old_tasks = session.query(Task).filter(
        Task.created_at < datetime.now() - timedelta(days=30)
    ).all()

    for task in old_tasks:
        session.delete(task)
    session.commit()

    # Clear admin context
    response = client.delete(
        "/api/v1/rls/admin/context",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
```

## Step 8: Disable RLS (Optional)

To disable RLS system-wide:

```python
# Update RLS configuration
config_update = {
    "rls_enabled": False
}

response = client.put(
    "/api/v1/rls/config",
    headers={"Authorization": f"Bearer {admin_token}"},
    json=config_update
)
assert response.status_code == 200

# Verify RLS is disabled
response = client.get("/api/v1/rls/status", headers={"Authorization": f"Bearer {admin_token}"})
assert response.json()["enabled"] == False
```

## Common Patterns

### Model Declaration

```python
# Always inherit from UserScopedBase for user-scoped data
class MyModel(UserScopedBase, table=True):
    # owner_id is automatically provided
    # Add your model fields here
    pass

# For non-user-scoped data, use regular SQLModel
class SystemConfig(SQLModel, table=True):
    # No owner_id field
    # No RLS enforcement
    pass
```

### API Endpoints

```python
# RLS automatically enforced for user-scoped models
@router.get("/items/")
def read_items(session: SessionDep, current_user: CurrentUser):
    # Automatically filtered by owner_id
    items = session.exec(select(Item)).all()
    return items

# Admin endpoints can bypass RLS with proper context
@router.get("/admin/items/")
def read_all_items(session: SessionDep, admin_user: AdminUser):
    # Can see all items regardless of owner
    items = session.exec(select(Item)).all()
    return items
```

### Migration Patterns

```python
# Migration automatically creates RLS policies
def upgrade():
    # RLS policies are created automatically
    # based on model metadata
    pass

def downgrade():
    # RLS policies are dropped automatically
    pass
```

## Troubleshooting

### RLS Not Working

1. Check RLS status:
   ```bash
   curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/rls/status
   ```

2. Verify model inheritance:
   ```python
   # Model should inherit from UserScopedBase
   assert issubclass(MyModel, UserScopedBase)
   ```

3. Check migration ran successfully:
   ```bash
   alembic current
   ```

### CI Validation Failing

1. Run validation manually:
   ```bash
   curl -X POST -H "Authorization: Bearer $ADMIN_TOKEN" \
     http://localhost:8000/api/v1/rls/validate/models
   ```

2. Fix violations:
   - Add `UserScopedBase` inheritance
   - Add `@rls_override` decorator if needed
   - Ensure `owner_id` field exists

### Performance Issues

1. Check indexes:
   ```sql
   -- Verify owner_id index exists
   SELECT * FROM pg_indexes WHERE tablename = 'your_table';
   ```

2. Monitor query performance:
   ```python
   # Enable query logging
   import logging
   logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
   ```

## Security Considerations

- RLS policies are enforced at the database level
- Session variables cannot be manipulated by users
- Admin roles require explicit authentication
- All access attempts are logged
- Use `FORCE ROW LEVEL SECURITY` in production

## Next Steps

- Review the [RLS Documentation](../docs/security/rls-user.md)
- Explore advanced RLS patterns
- Set up monitoring and alerting
- Configure backup and recovery procedures
