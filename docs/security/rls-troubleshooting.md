# RLS Troubleshooting Guide

This guide helps diagnose and resolve common Row-Level Security (RLS) issues in the FastAPI template project.

## Quick Diagnostic Commands

### Check RLS Status

```bash
# Check if RLS is enabled in environment
echo $RLS_ENABLED

# Check database connection and RLS status
docker exec -it <container_name> psql -U postgres -d <database_name> -c "
SELECT schemaname, tablename, rowsecurity
FROM pg_tables
WHERE rowsecurity = true;
"
```

### Verify RLS Policies

```sql
-- List all RLS policies
SELECT schemaname, tablename, policyname, cmd, qual, with_check
FROM pg_policies
WHERE tablename = 'item';

-- Check specific policy details
SELECT * FROM pg_policies WHERE policyname = 'user_select_policy';
```

### Check Session Context

```sql
-- Verify current session context
SELECT
    current_setting('app.user_id') as user_id,
    current_setting('app.role') as role;

-- Test context setting
SET app.user_id = 'test-user-id';
SET app.role = 'user';
SELECT current_setting('app.user_id'), current_setting('app.role');
```

## Common Issues and Solutions

### 1. Users Can See All Data (RLS Not Working)

**Symptoms:**
- Regular users can see data from other users
- Queries return more records than expected
- No access denied errors

**Diagnosis:**
```sql
-- Check if RLS is enabled on the table
SELECT relrowsecurity FROM pg_class WHERE relname = 'item';

-- Check if policies exist
SELECT COUNT(*) FROM pg_policies WHERE tablename = 'item';
```

**Solutions:**

1. **Enable RLS on the table:**
```sql
ALTER TABLE item ENABLE ROW LEVEL SECURITY;
```

2. **Check environment configuration:**
```bash
# Ensure RLS is enabled
export RLS_ENABLED=true
```

3. **Run migrations to apply RLS policies:**
```bash
cd backend
alembic upgrade head
```

4. **Verify model inheritance:**
```python
# Ensure model inherits from UserScopedBase
from app.core.rls import UserScopedBase

class Item(UserScopedBase, table=True):
    # ... model definition
```

### 2. Access Denied Errors

**Symptoms:**
- 403 Forbidden errors when accessing own data
- "Access denied" messages
- Users cannot perform CRUD operations

**Diagnosis:**
```sql
-- Check session context
SELECT current_setting('app.user_id'), current_setting('app.role');

-- Test RLS policies manually
SET app.user_id = 'actual-user-id';
SET app.role = 'user';
SELECT * FROM item; -- Should only show user's items
```

**Solutions:**

1. **Verify authentication:**
```python
# Check user authentication in API endpoint
@router.get("/items/")
def read_items(session: RLSSessionDep, current_user: CurrentUser):
    # current_user should be properly authenticated
    print(f"Authenticated user: {current_user.id}")
```

2. **Check session context setting:**
```python
# Ensure RLS context is set in dependencies
def get_rls_session(current_user: CurrentUser) -> Generator[Session, None, None]:
    with Session(engine) as session:
        # Set RLS context
        session.execute(text(f"SET app.user_id = '{current_user.id}'"))
        session.execute(text(f"SET app.role = 'user'"))
        yield session
```

3. **Verify RLS policies:**
```sql
-- Check policy conditions
SELECT policyname, qual FROM pg_policies
WHERE tablename = 'item' AND cmd = 'SELECT';
```

### 3. Admin Operations Failing

**Symptoms:**
- Admin users cannot access all data
- Admin endpoints return 403 errors
- Maintenance operations fail

**Diagnosis:**
```sql
-- Check admin role context
SET app.role = 'admin';
SELECT current_setting('app.role');

-- Test admin access
SELECT COUNT(*) FROM item; -- Should return all items
```

**Solutions:**

1. **Verify admin user privileges:**
```python
# Check user is superuser
if not current_user.is_superuser:
    raise HTTPException(status_code=403, detail="Admin privileges required")
```

2. **Use admin session dependency:**
```python
from app.api.deps import AdminSessionDep

@router.get("/admin/items/")
def read_all_items(session: AdminSessionDep, current_user: CurrentUser):
    # This should work for admin users
    items = session.exec(select(Item)).all()
    return items
```

3. **Check admin context manager:**
```python
from app.core.rls import AdminContext

with AdminContext.create_full_admin(user_id, session) as admin_ctx:
    # Operations should have admin privileges
    items = session.exec(select(Item)).all()
```

### 4. Migration Issues

**Symptoms:**
- RLS policies not created during migrations
- Migration errors related to RLS
- Inconsistent database state

**Diagnosis:**
```bash
# Check migration status
cd backend
alembic current
alembic history

# Check migration files
ls -la app/alembic/versions/
```

**Solutions:**

1. **Run migrations manually:**
```bash
cd backend
alembic upgrade head
```

2. **Check migration environment:**
```python
# Verify RLS registry in env.py
from app.core.rls import rls_registry, policy_generator

# Check registered tables
print(rls_registry.get_registered_tables())
```

3. **Recreate RLS policies:**
```sql
-- Drop existing policies
DROP POLICY IF EXISTS user_select_policy ON item;
DROP POLICY IF EXISTS user_insert_policy ON item;
DROP POLICY IF EXISTS user_update_policy ON item;
DROP POLICY IF EXISTS user_delete_policy ON item;

-- Recreate policies (run migration again)
```

### 5. Performance Issues

**Symptoms:**
- Slow query performance
- High database load
- Timeout errors

**Diagnosis:**
```sql
-- Check query performance
EXPLAIN ANALYZE SELECT * FROM item WHERE owner_id = 'user-id';

-- Check indexes
SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'item';
```

**Solutions:**

1. **Verify indexes:**
```sql
-- Check owner_id index exists
CREATE INDEX IF NOT EXISTS idx_item_owner_id ON item(owner_id);
```

2. **Optimize queries:**
```python
# Use specific queries instead of SELECT *
statement = select(Item).where(Item.owner_id == user_id)
items = session.exec(statement).all()
```

3. **Monitor RLS overhead:**
```python
# Use performance tests to measure impact
pytest backend/tests/performance/test_rls_performance.py -v
```

### 6. Context Switching Issues

**Symptoms:**
- Session context not cleared properly
- Cross-user data leakage
- Inconsistent behavior between requests

**Diagnosis:**
```sql
-- Check for stale context
SELECT current_setting('app.user_id'), current_setting('app.role');
```

**Solutions:**

1. **Ensure context cleanup:**
```python
def get_db() -> Generator[Session, None, None]:
    with Session(engine) as session:
        try:
            yield session
        finally:
            # Always clear context
            session.execute(text("SET app.user_id = NULL"))
            session.execute(text("SET app.role = NULL"))
```

2. **Use proper session management:**
```python
# Always use RLS-aware dependencies
@router.get("/items/")
def read_items(session: RLSSessionDep, current_user: CurrentUser):
    # Context is automatically managed
    items = session.exec(select(Item)).all()
    return items
```

## Debugging Tools

### 1. RLS Validation Script

```bash
# Run RLS validation
cd backend
python scripts/lint_rls.py --verbose
```

### 2. Database Inspection

```sql
-- Check all RLS-enabled tables
SELECT schemaname, tablename, rowsecurity
FROM pg_tables
WHERE rowsecurity = true;

-- List all policies
SELECT schemaname, tablename, policyname, cmd, qual
FROM pg_policies
ORDER BY tablename, policyname;

-- Check policy effectiveness
SET app.user_id = 'test-user-id';
SET app.role = 'user';
EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM item;
```

### 3. Application Logging

```python
import logging
logging.getLogger('app.core.rls').setLevel(logging.DEBUG)

# Check RLS registry
from app.core.rls import rls_registry
print("Registered tables:", rls_registry.get_table_names())
print("Registered models:", rls_registry.get_model_names())
```

### 4. Test Scenarios

```bash
# Run RLS integration tests
pytest backend/tests/integration/test_rls_isolation.py -v

# Run RLS admin tests
pytest backend/tests/integration/test_rls_admin.py -v

# Run RLS policy tests
pytest backend/tests/integration/test_rls_policies.py -v

# Run performance tests
pytest backend/tests/performance/test_rls_performance.py -v
```

## Prevention Best Practices

### 1. Development Workflow

1. **Always inherit from UserScopedBase** for user-owned models
2. **Use RLS-aware dependencies** in API endpoints
3. **Test RLS behavior** with different user scenarios
4. **Run migrations** after model changes
5. **Validate RLS policies** in development environment

### 2. Testing Strategy

1. **Unit tests** for RLS model behavior
2. **Integration tests** for user isolation
3. **Admin tests** for bypass functionality
4. **Performance tests** for RLS overhead
5. **Context tests** for session management

### 3. Monitoring

1. **Log RLS context** in production
2. **Monitor query performance** with RLS enabled
3. **Alert on access denied** errors
4. **Track admin operations** for security
5. **Validate RLS policies** regularly

## Getting Help

If you're still experiencing issues:

1. **Check the logs** for detailed error messages
2. **Run diagnostic commands** above
3. **Review the RLS User Guide** for implementation details
4. **Check the API documentation** for proper usage
5. **Run the test suite** to verify functionality
6. **Consult the ERD** for model relationships

## Emergency Procedures

### Disable RLS Temporarily

```bash
# Set environment variable
export RLS_ENABLED=false

# Restart application
docker-compose restart backend
```

### Reset RLS Policies

```sql
-- Disable RLS on all tables
ALTER TABLE item DISABLE ROW LEVEL SECURITY;

-- Drop all policies
DROP POLICY IF EXISTS user_select_policy ON item;
DROP POLICY IF EXISTS user_insert_policy ON item;
DROP POLICY IF EXISTS user_update_policy ON item;
DROP POLICY IF EXISTS user_delete_policy ON item;

-- Re-enable RLS
ALTER TABLE item ENABLE ROW LEVEL SECURITY;

-- Run migrations to recreate policies
```

### Database Recovery

```bash
# Restore from backup if RLS corruption occurs
docker-compose down
docker volume rm <volume_name>
docker-compose up -d

# Run migrations
cd backend
alembic upgrade head
```
