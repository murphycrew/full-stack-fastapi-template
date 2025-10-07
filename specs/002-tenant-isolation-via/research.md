# Research: Tenant Isolation via Automatic Row-Level Security (RLS) - Internal Infrastructure

**Feature**: 002-tenant-isolation-via | **Date**: 2024-12-19 | **Updated**: 2024-12-19

## Research Areas

### 1. PostgreSQL RLS Policy Patterns for User-Scoped Data Isolation

**Decision**: Use PostgreSQL RLS with session variables and policy functions for user-scoped data isolation.

**Rationale**:
- PostgreSQL RLS provides database-level security enforcement that cannot be bypassed by application bugs
- Session variables (`app.user_id`, `app.role`) allow per-request context setting
- Policy functions enable complex logic for admin roles vs regular users
- Performance impact is minimal when properly indexed

**Alternatives considered**:
- Application-level filtering: Rejected due to security risks and potential bypass
- Database views: Rejected due to complexity and maintenance overhead
- Separate databases per user: Rejected due to operational complexity

**Implementation pattern**:
```sql
-- Enable RLS on table
ALTER TABLE item ENABLE ROW LEVEL SECURITY;

-- Create policies
CREATE POLICY user_select_policy ON item
    FOR SELECT USING (
        app.user_id = owner_id OR
        app.role = 'admin' OR
        app.role = 'read_only_admin'
    );

CREATE POLICY user_insert_policy ON item
    FOR INSERT WITH CHECK (app.user_id = owner_id OR app.role = 'admin');

CREATE POLICY user_update_policy ON item
    FOR UPDATE USING (
        app.user_id = owner_id OR app.role = 'admin'
    );
```

### 2. Alembic Migration Hooks for Automatic DDL Generation

**Decision**: Use Alembic's `@op.f` functions and custom migration scripts to generate RLS policies automatically.

**Rationale**:
- Alembic provides migration versioning and rollback capabilities
- Custom migration scripts can inspect SQLModel metadata to generate policies
- Integration with existing migration workflow maintains consistency
- Idempotent operations ensure safe re-runs

**Alternatives considered**:
- Manual policy creation: Rejected due to maintenance burden and human error
- Database triggers: Rejected due to complexity and debugging difficulties
- External tools: Rejected due to additional dependencies

**Implementation pattern**:
```python
def upgrade():
    # Enable RLS on user-scoped tables
    for table_name in get_rls_scoped_tables():
        op.execute(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY")
        if settings.RLS_FORCE:
            op.execute(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY")

        # Create policies for each operation
        create_rls_policies(table_name)
```

### 3. SQLModel Base Class Inheritance with Foreign Keys

**Decision**: Create a `UserScopedBase` class that inherits from `SQLModel` and provides `owner_id` field with proper foreign key relationship.

**Rationale**:
- SQLModel supports inheritance and field definition in base classes
- Foreign key relationships are properly maintained
- Type hints and validation work correctly
- Alembic can detect and generate appropriate migrations

**Alternatives considered**:
- Mixins: Rejected due to SQLModel inheritance limitations
- Composition: Rejected due to complexity and relationship issues
- Manual field addition: Rejected due to maintenance burden

**Implementation pattern**:
```python
class UserScopedBase(SQLModel):
    owner_id: uuid.UUID = Field(
        foreign_key="user.id",
        nullable=False,
        index=True,
        description="Owner of this record"
    )

    @classmethod
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # Register with RLS system
        register_rls_model(cls)

class Item(UserScopedBase, ItemBase, table=True):
    # Inherits owner_id automatically
    pass
```

### 4. FastAPI Session Context Injection Patterns

**Decision**: Use FastAPI dependency injection with database session middleware to set session variables.

**Rationale**:
- FastAPI dependencies provide clean separation of concerns
- Database session middleware ensures context is set before any queries
- Type-safe dependency injection with proper error handling
- Integration with existing authentication system

**Alternatives considered**:
- Global variables: Rejected due to concurrency issues
- Request context: Rejected due to complexity and maintenance
- Manual session management: Rejected due to error-prone nature

**Implementation pattern**:
```python
async def set_rls_context(
    session: SessionDep,
    current_user: CurrentUser = Depends(get_current_user)
):
    # Set session variables for RLS
    session.execute(text("SET app.user_id = :user_id"), {"user_id": str(current_user.id)})
    session.execute(text("SET app.role = :role"), {"role": get_user_role(current_user)})
    return session
```

### 5. CI Integration for Model Validation in Python Projects

**Decision**: Use pytest with custom linting rules to validate model inheritance and RLS compliance.

**Rationale**:
- pytest integrates well with existing test infrastructure
- Custom linting rules can detect undeclared user-owned models
- CI integration provides immediate feedback on violations
- Override mechanism allows exceptions when needed

**Alternatives considered**:
- Pre-commit hooks only: Rejected due to bypass possibility
- Manual review: Rejected due to human error potential
- External linting tools: Rejected due to additional dependencies

**Implementation pattern**:
```python
def test_rls_model_compliance():
    """Test that all models with owner_id inherit from UserScopedBase"""
    violations = []
    for model in get_all_sqlmodel_tables():
        if has_owner_id_field(model) and not inherits_from_user_scoped_base(model):
            if not has_rls_override(model):
                violations.append(model.__name__)

    assert not violations, f"Models missing RLS declaration: {violations}"
```

## Performance Considerations

### RLS Policy Performance
- Policies should use indexed columns (`owner_id` with index)
- Complex policy logic should be avoided
- Session variable lookups are fast and cached per connection
- Estimated overhead: <5ms per query for simple policies

### Migration Performance
- Policy creation is done during deployment, not runtime
- Idempotent operations allow safe re-runs
- Batch policy creation for multiple tables
- Estimated time: <30 seconds for 50 tables

## Security Considerations

### RLS Policy Security
- `FORCE ROW LEVEL SECURITY` prevents bypass by privileged roles
- Session variables are connection-scoped and cannot be manipulated by users
- Admin roles require explicit database privileges
- Policy functions prevent SQL injection through proper parameterization

### Admin Role Security
- User-level admin roles use existing authentication system
- Database-level admin roles require separate connection credentials
- Audit logging for admin operations
- Principle of least privilege for maintenance operations

## Compatibility Considerations

### Backward Compatibility
- RLS can be disabled via configuration
- Existing models continue to work without changes
- Gradual migration path for existing applications
- No breaking changes to existing APIs

### Database Compatibility
- PostgreSQL 9.5+ required for RLS support
- Session variables require PostgreSQL 9.2+
- Alembic supports all major PostgreSQL versions
- Docker images provide consistent environment

## Integration Points

### Existing Systems
- Integrates with current SQLModel/SQLAlchemy setup
- Works with existing Alembic migration system
- Compatible with current FastAPI dependency injection
- Leverages existing authentication and user management

### Template Integration
- Updates existing Item model as example
- Provides clear documentation and examples
- Maintains template's production-ready status
- Demonstrates best practices for RLS implementation
