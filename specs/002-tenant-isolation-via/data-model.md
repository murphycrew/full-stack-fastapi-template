# Data Model: Tenant Isolation via Automatic Row-Level Security (RLS) - Internal Infrastructure

**Feature**: 002-tenant-isolation-via | **Date**: 2024-12-19 | **Updated**: 2024-12-19

## Core Entities

### UserScopedBase
**Purpose**: Abstract base class that provides automatic RLS enforcement for user-owned data models.

**Fields**:
- `owner_id: uuid.UUID` - Foreign key to user.id, indexed for performance
- `created_at: datetime` - Timestamp of record creation (optional)
- `updated_at: datetime` - Timestamp of last update (optional)

**Relationships**:
- `owner_id` → `User.id` (ForeignKey, CASCADE delete)

**Validation Rules**:
- `owner_id` must not be null
- `owner_id` must reference existing user
- Automatic index creation for performance

**State Transitions**:
- Model creation: owner_id set from current user context
- Model update: owner_id cannot be changed (immutable)
- Model deletion: CASCADE to user deletion

**RLS Integration**:
- Automatically registers with RLS system
- Generates RLS policies during migration
- Enforces user isolation at database level

### RLS Policy
**Purpose**: Database-level security rule that restricts data access based on user identity.

**Attributes**:
- `table_name: str` - Target table for policy
- `operation: str` - Policy operation (SELECT, INSERT, UPDATE, DELETE)
- `condition: str` - SQL condition for policy evaluation
- `role: str` - Target role (user, read_only_admin, admin)

**Policy Types**:
- `user_select_policy`: Users can only SELECT their own data
- `user_insert_policy`: Users can only INSERT with their own owner_id
- `user_update_policy`: Users can only UPDATE their own data
- `admin_select_policy`: Admins can SELECT all data
- `admin_insert_policy`: Admins can INSERT with any owner_id
- `admin_update_policy`: Admins can UPDATE all data

**Generation Rules**:
- Policies are generated automatically from model metadata
- Idempotent operations allow safe re-runs
- Policies are dropped and recreated during migrations

### Admin Context
**Purpose**: Elevated access mode that allows viewing or modifying all user data.

**Types**:
- `User-Level Admin`: Regular user with admin privileges
  - `is_superuser: bool` - Full admin privileges
  - `is_read_only_admin: bool` - Read-only admin privileges
- `Database-Level Admin`: Database role for maintenance operations
  - `role_name: str` - Database role name
  - `permissions: list[str]` - Database permissions

**Context Setting**:
- User-level: Set via session variables (`app.role`)
- Database-level: Set via connection credentials
- Maintenance operations: Explicit context setting

**Security Rules**:
- User-level admin requires authentication
- Database-level admin requires separate credentials
- Audit logging for all admin operations
- Principle of least privilege

### Identity Context
**Purpose**: Per-request information about the current user and their access level.

**Session Variables**:
- `app.user_id: uuid` - Current user ID
- `app.role: str` - Current user role (user, read_only_admin, admin)

**Setting Mechanism**:
- Set by FastAPI dependency injection
- Applied to database session before any queries
- Cleared after request completion

**Validation**:
- User ID must be valid UUID
- Role must be one of defined roles
- Context must be set before RLS enforcement

## Model Relationships

### User → UserScoped Models
```
User (1) ←→ (many) UserScopedModel
├── User.id (primary key)
└── UserScopedModel.owner_id (foreign key)
```

**Cascade Rules**:
- User deletion → CASCADE delete all owned records
- User update → No impact on owned records
- User creation → No owned records initially

### RLS Policy → Table
```
RLS Policy (many) ←→ (1) Table
├── Policy applies to specific table
├── Multiple policies per table (SELECT, INSERT, UPDATE)
└── Policies are table-specific
```

## Validation Rules

### UserScopedBase Validation
- `owner_id` field is required and cannot be null
- `owner_id` must reference existing user in database
- Index must exist on `owner_id` for performance
- Foreign key constraint must be enforced

### RLS Policy Validation
- Policy conditions must be valid SQL
- Policy operations must be supported (SELECT, INSERT, UPDATE, DELETE)
- Policy roles must be defined in system
- Policies must be idempotent (safe to re-run)

### Admin Context Validation
- User-level admin roles must be authenticated
- Database-level admin roles must have proper credentials
- Role transitions must be logged
- Admin operations must be audited

## State Management

### Model Lifecycle
1. **Creation**: owner_id set from current user context
2. **Read**: RLS policies filter based on user context
3. **Update**: RLS policies prevent cross-user updates
4. **Delete**: RLS policies prevent cross-user deletes

### RLS Lifecycle
1. **Enable**: RLS enabled on table during migration
2. **Policy Creation**: Policies created based on model metadata
3. **Policy Enforcement**: Policies enforced on all queries
4. **Policy Updates**: Policies updated during schema changes

### Context Lifecycle
1. **Request Start**: Identity context set from authentication
2. **Query Execution**: Context used by RLS policies
3. **Request End**: Context cleared from session

## Error Handling

### RLS Violation Errors
- Generic "Access denied" messages
- No disclosure of other users' data existence
- Consistent with existing application error patterns
- Proper HTTP status codes (403 Forbidden)

### Policy Generation Errors
- Clear error messages for invalid policies
- Rollback capability for failed migrations
- Validation before policy creation
- Safe fallback to application-level security

### Context Setting Errors
- Fallback to application-level security
- Clear logging of context setting failures
- Graceful degradation when RLS unavailable
- Proper error handling for invalid user context

## Performance Considerations

### Indexing Strategy
- Primary index on `owner_id` field for all user-scoped tables
- Composite indexes for common query patterns
- Index maintenance during schema changes

### Query Optimization
- RLS policies use indexed columns
- Session variables cached per connection
- Minimal overhead for policy evaluation
- Query plan optimization for RLS queries

### Migration Performance
- Batch policy creation for multiple tables
- Idempotent operations for safe re-runs
- Parallel policy creation where possible
- Progress tracking for large migrations

## Security Considerations

### Data Isolation
- Database-level enforcement prevents bypass
- Session variables cannot be manipulated by users
- Admin roles require explicit privileges
- Audit trail for all access attempts

### Policy Security
- Policy conditions prevent SQL injection
- Parameterized queries for all policy conditions
- Regular security audits of policy definitions
- Principle of least privilege for all policies

### Admin Security
- Separate credentials for database-level admin
- Audit logging for all admin operations
- Time-limited admin access where possible
- Regular rotation of admin credentials
