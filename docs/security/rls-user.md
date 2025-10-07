# Row-Level Security (RLS) User Guide

This document provides a comprehensive guide to understanding and using Row-Level Security (RLS) in the FastAPI template project.

## Table of Contents

- [Overview](#overview)
- [Key Concepts](#key-concepts)
- [Configuration](#configuration)
- [Model Development](#model-development)
- [API Usage](#api-usage)
- [Admin Operations](#admin-operations)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)

## Overview

Row-Level Security (RLS) provides automatic data isolation at the database level, ensuring that users can only access data they own. This is implemented using PostgreSQL's Row-Level Security feature with automatic policy generation and enforcement.

### Benefits

- **Automatic Data Isolation**: Users can only see their own data without explicit filtering
- **Database-Level Security**: Security is enforced at the database layer, not just application layer
- **Minimal Developer Overhead**: RLS is automatically applied to models that inherit from `UserScopedBase`
- **Admin Bypass**: Admins can access all data when needed for maintenance operations

## Key Concepts

### UserScopedBase

Models that inherit from `UserScopedBase` automatically get:

- An `owner_id` field with foreign key to `user.id`
- Automatic registration for RLS policy generation
- RLS policies applied during database migrations
- User isolation enforcement at the database level

```python
from app.core.rls import UserScopedBase

class MyModel(UserScopedBase, table=True):
    __tablename__ = "my_model"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    title: str = Field(max_length=255)
    # owner_id is automatically inherited from UserScopedBase
```

### RLS Policies

RLS policies are automatically generated for each `UserScopedBase` model:

- **SELECT**: Users can only see records where `owner_id` matches their user ID
- **INSERT**: Users can only insert records with their own `owner_id`
- **UPDATE**: Users can only update records they own
- **DELETE**: Users can only delete records they own

### Admin Context

Admin users can bypass RLS policies through:

- **User-Level Admin**: Regular users with `is_superuser=True`
- **Database-Level Admin**: Dedicated database roles for maintenance operations

## Configuration

### Environment Variables

```bash
# Enable/disable RLS
RLS_ENABLED=true

# Force RLS even for privileged roles
RLS_FORCE=false

# Database roles for RLS
RLS_APP_USER=rls_app_user
RLS_APP_PASSWORD=changethis
RLS_MAINTENANCE_ADMIN=rls_maintenance_admin
RLS_MAINTENANCE_ADMIN_PASSWORD=changethis

# Initial users for RLS demonstration
FIRST_USER=user@example.com
FIRST_USER_PASSWORD=changethis
FIRST_SUPERUSER=admin@example.com
FIRST_SUPERUSER_PASSWORD=changethis
```

### Settings

RLS configuration is managed in `app/core/config.py`:

```python
class Settings(BaseSettings):
    RLS_ENABLED: bool = True
    RLS_FORCE: bool = False

    # Database role configuration
    RLS_APP_USER: str = "rls_app_user"
    RLS_APP_PASSWORD: str = "changethis"
    RLS_MAINTENANCE_ADMIN: str = "rls_maintenance_admin"
    RLS_MAINTENANCE_ADMIN_PASSWORD: str = "changethis"
```

## Model Development

### Creating RLS-Scoped Models

To create a model with RLS enforcement:

1. **Inherit from UserScopedBase**:
```python
from app.core.rls import UserScopedBase

class Task(UserScopedBase, table=True):
    __tablename__ = "task"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    title: str = Field(max_length=255)
    description: Optional[str] = None
    # owner_id is automatically inherited
```

2. **Define Relationships**:
```python
class Task(UserScopedBase, table=True):
    # ... fields ...

    owner: User = Relationship(back_populates="tasks")
```

3. **Update User Model**:
```python
class User(UserBase, table=True):
    # ... fields ...

    tasks: List[Task] = Relationship(back_populates="owner", cascade_delete=True)
```

### Automatic Registration

Models that inherit from `UserScopedBase` are automatically registered for RLS policy generation. This happens when the model class is defined, so no additional registration is required.

## API Usage

### Regular User Operations

Regular users automatically have RLS context set through FastAPI dependencies:

```python
from app.api.deps import RLSSessionDep, CurrentUser

@router.get("/items/")
def read_items(session: RLSSessionDep, current_user: CurrentUser):
    # RLS context is automatically set
    # User can only see their own items
    items = session.exec(select(Item)).all()
    return items
```

### CRUD Operations

Use the RLS-compatible CRUD operations:

```python
from app import crud

# Create item (automatically sets owner_id)
item = crud.create_item(session=session, item_in=item_data, owner_id=user.id)

# Get user's items (RLS enforced)
items = crud.get_items(session=session, owner_id=user.id)

# Update item (ownership verified)
item = crud.update_item(session=session, db_item=item, item_in=update_data, owner_id=user.id)

# Delete item (ownership verified)
crud.delete_item(session=session, item_id=item_id, owner_id=user.id)
```

## Admin Operations

### User-Level Admin

Admin users can access all data through RLS policies:

```python
from app.api.deps import AdminSessionDep

@router.get("/admin/items/")
def read_all_items(session: AdminSessionDep, current_user: CurrentUser):
    # Admin can see all items regardless of ownership
    items = session.exec(select(Item)).all()
    return items
```

### Admin CRUD Operations

Use admin CRUD operations for maintenance:

```python
# Get any item (admin only)
item = crud.get_item_admin(session=session, item_id=item_id)

# Update any item (admin only)
item = crud.update_item_admin(session=session, db_item=item, item_in=update_data)

# Delete any item (admin only)
crud.delete_item_admin(session=session, item_id=item_id)
```

### Admin Context Manager

For programmatic admin access:

```python
from app.core.rls import AdminContext

with AdminContext.create_full_admin(user_id, session) as admin_ctx:
    # All operations in this block run with admin privileges
    items = session.exec(select(Item)).all()
```

## Troubleshooting

### Common Issues

#### 1. RLS Policies Not Applied

**Symptoms**: Users can see all data instead of just their own.

**Solutions**:
- Check that `RLS_ENABLED=true` in environment variables
- Verify that models inherit from `UserScopedBase`
- Run database migrations: `alembic upgrade head`
- Check RLS policies in database: `SELECT * FROM pg_policies WHERE tablename = 'your_table';`

#### 2. Access Denied Errors

**Symptoms**: Users get 403 errors when accessing their own data.

**Solutions**:
- Verify RLS context is set: `SELECT current_setting('app.user_id');`
- Check user authentication and token validity
- Ensure proper session context management in API endpoints

#### 3. Admin Operations Failing

**Symptoms**: Admin users cannot access all data.

**Solutions**:
- Verify user has `is_superuser=True`
- Check admin session dependency usage
- Verify RLS policies allow admin access

### Debugging Commands

```sql
-- Check if RLS is enabled on a table
SELECT relrowsecurity FROM pg_class WHERE relname = 'item';

-- List all RLS policies
SELECT schemaname, tablename, policyname, cmd, qual
FROM pg_policies
WHERE tablename = 'item';

-- Check current session context
SELECT current_setting('app.user_id'), current_setting('app.role');

-- Test RLS policies
SET app.user_id = 'user-uuid-here';
SET app.role = 'user';
SELECT * FROM item; -- Should only show user's items
```

### Logging

Enable debug logging to troubleshoot RLS issues:

```python
import logging
logging.getLogger('app.core.rls').setLevel(logging.DEBUG)
```

## Best Practices

### Model Design

1. **Always inherit from UserScopedBase** for user-owned data
2. **Use proper relationships** between User and RLS-scoped models
3. **Index the owner_id field** (automatically done by UserScopedBase)
4. **Consider cascade delete** for related data cleanup

### API Design

1. **Use RLSSessionDep** for user endpoints
2. **Use AdminSessionDep** for admin endpoints
3. **Implement proper error handling** for RLS violations
4. **Provide clear error messages** for access denied scenarios

### Security

1. **Never bypass RLS** in regular user operations
2. **Use admin context sparingly** and only when necessary
3. **Audit admin operations** for security compliance
4. **Test RLS policies** with different user scenarios

### Performance

1. **Monitor RLS performance** impact on queries
2. **Use appropriate indexes** on owner_id fields
3. **Consider query optimization** for large datasets
4. **Test concurrent user scenarios** for performance validation

### Migration Management

1. **Always run migrations** after model changes
2. **Test RLS policies** in development environment
3. **Verify policy application** after migrations
4. **Document any manual policy changes**

## Examples

See [RLS Examples](rls-examples.md) for detailed code examples and use cases.

## Support

For additional help with RLS implementation:

1. Check the [Troubleshooting Guide](rls-troubleshooting.md)
2. Review the [Performance Tests](../backend/tests/performance/test_rls_performance.py)
3. Consult the [API Documentation](../backend/app/api/routes/)
4. Check the [Database ERD](../database/erd.md) for model relationships
