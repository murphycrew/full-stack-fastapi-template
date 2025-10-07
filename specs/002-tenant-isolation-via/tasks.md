# Tasks: Tenant Isolation via Automatic Row-Level Security (RLS) - Internal Infrastructure

**Input**: Design documents from `/specs/002-tenant-isolation-via/`
**Prerequisites**: plan.md (required), research.md, data-model.md, quickstart.md

## Execution Flow (main)
```
1. Load plan.md from feature directory
   → Extract: tech stack, libraries, structure
2. Load optional design documents:
   → data-model.md: Extract entities → model tasks
   → research.md: Extract decisions → setup tasks
   → quickstart.md: Extract test scenarios → integration tests
3. Generate tasks by category:
   → Setup: project init, dependencies, linting
   → Tests: integration tests, unit tests
   → Core: models, services, utilities
   → Integration: DB, middleware, migrations
   → Polish: performance, docs
4. Apply task rules:
   → Different files = mark [P] for parallel
   → Same file = sequential (no [P])
   → Tests before implementation (TDD)
5. Number tasks sequentially (T001, T002...)
6. Generate dependency graph
7. Create parallel execution examples
8. Validate task completeness:
   → All entities have models?
   → All test scenarios covered?
9. Return: SUCCESS (tasks ready for execution)
```

## Format: `[ID] [P?] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- Include exact file paths in descriptions

## Path Conventions
- **Backend**: `backend/app/`
- **Tests**: `backend/tests/`
- **Documentation**: `docs/`
- **Migrations**: `backend/app/alembic/versions/`

## Phase 3.1: Setup
- [x] T001 Create RLS infrastructure directory structure
- [x] T002 Add RLS dependencies to pyproject.toml
- [x] T003 [P] Configure RLS environment variables in core/config.py
- [x] T004 [P] Add RLS linting rules to pre-commit hooks
- [x] T035 [P] Add initial user configuration variables to copier.yml
- [x] T036 [P] Add database role configuration variables to copier.yml

## Phase 3.2: Tests First (TDD) ✅ COMPLETED
**CRITICAL: These tests MUST be written and MUST FAIL before ANY implementation**
- [x] T005 [P] Integration test user-scoped model isolation in tests/integration/test_rls_isolation.py
- [x] T006 [P] Integration test admin bypass functionality in tests/integration/test_rls_admin.py
- [x] T007 [P] Integration test RLS policy enforcement in tests/integration/test_rls_policies.py
- [x] T008 [P] Integration test session context management in tests/integration/test_rls_context.py
- [x] T009 [P] Unit test UserScopedBase model behavior in tests/unit/test_rls_models.py
- [x] T010 [P] Unit test RLS registry functionality in tests/unit/test_rls_registry.py

## Phase 3.3: Core Implementation ✅ COMPLETED
- [x] T011 [P] UserScopedBase model in backend/app/core/rls.py
- [x] T012 [P] RLS registry system in backend/app/core/rls.py
- [x] T013 [P] Identity context management in backend/app/api/deps.py
- [x] T014 [P] RLS policy generation utilities in backend/app/core/rls.py
- [x] T015 [P] Admin context management in backend/app/core/rls.py
- [x] T016 [P] RLS configuration management in backend/app/core/config.py

## Phase 3.4: Model Updates ✅ COMPLETED
- [x] T017 [P] Update Item model to inherit from UserScopedBase in backend/app/models.py
- [x] T018 [P] Add RLS validation to existing models in backend/app/models.py
- [x] T019 [P] Update CRUD operations for RLS compatibility in backend/app/crud.py
- [x] T037 [P] Create initial regular user in backend/app/initial_data.py
- [x] T038 [P] Create initial admin user in backend/app/initial_data.py

## Phase 3.5: Migration Integration ✅ COMPLETED
- [x] T020 [P] Add RLS policy generation to Alembic env.py in backend/app/alembic/env.py
- [x] T021 [P] Create RLS policy migration utilities in backend/app/alembic/rls_policies.py
- [x] T022 [P] Generate initial RLS migration for existing models in backend/app/alembic/versions/
- [x] T039 [P] Create application database user role in backend/scripts/setup_db_roles.py
- [x] T040 [P] Create maintenance admin database user role in backend/scripts/setup_db_roles.py

## Phase 3.6: API Integration ✅ COMPLETED
- [x] T023 [P] Update FastAPI dependencies for RLS context in backend/app/api/deps.py
- [x] T024 [P] Update Item API endpoints for RLS compatibility in backend/app/api/routes/items.py
- [x] T025 [P] Add RLS error handling to API responses in backend/app/api/main.py

## Phase 3.7: CI and Validation ✅ COMPLETED
- [x] T026 [P] Add CI lint check for undeclared user-owned models in backend/scripts/lint_rls.py
- [x] T027 [P] Update pre-commit hooks for RLS validation in .pre-commit-config.yaml
- [x] T028 [P] Add RLS validation to backend startup in backend/app/backend_pre_start.py
- [x] T041 [P] Update docker-compose.yml for multiple database users
- [x] T042 [P] Update backend startup scripts for database role setup

## Phase 3.8: Polish ✅ COMPLETED
- [x] T029 [P] Performance tests for RLS policies in tests/performance/test_rls_performance.py
- [x] T030 [P] Create RLS documentation in docs/security/rls-user.md
- [x] T031 [P] Update ERD documentation with RLS models in docs/database/erd.md
- [x] T032 [P] Add RLS troubleshooting guide in docs/security/rls-troubleshooting.md
- [x] T033 [P] Update README with RLS information in backend/README.md
- [x] T034 [P] Create RLS quickstart examples in docs/examples/rls-examples.md

## Dependencies
- Tests (T005-T010) before implementation (T011-T016)
- T011 blocks T017, T020
- T012 blocks T020, T021
- T013 blocks T023, T024
- T016 blocks T023
- T017 blocks T024
- T020 blocks T022
- T035 blocks T037, T038 (configuration before user creation)
- T036 blocks T039, T040 (configuration before role creation)
- T039, T040 blocks T041, T042 (roles before docker/startup updates)
- Implementation before polish (T029-T034)

## Parallel Example
```
# Launch T005-T010 together:
Task: "Integration test user-scoped model isolation in tests/integration/test_rls_isolation.py"
Task: "Integration test admin bypass functionality in tests/integration/test_rls_admin.py"
Task: "Integration test RLS policy enforcement in tests/integration/test_rls_policies.py"
Task: "Integration test session context management in tests/integration/test_rls_context.py"
Task: "Unit test UserScopedBase model behavior in tests/unit/test_rls_models.py"
Task: "Unit test RLS registry functionality in tests/unit/test_rls_registry.py"

# Launch T035-T036 together (configuration setup):
Task: "Add initial user configuration variables to copier.yml"
Task: "Add database role configuration variables to copier.yml"
```

## Notes
- [P] tasks = different files, no dependencies
- Verify tests fail before implementing
- Commit after each task
- Avoid: vague tasks, same file conflicts
- All RLS management is internal infrastructure - no user-facing API endpoints

## Task Generation Rules
*Applied during main() execution*

1. **From Data Model**:
   - UserScopedBase entity → model creation task [P]
   - RLS Policy entity → policy generation task [P]
   - Admin Context entity → admin management task [P]
   - Identity Context entity → context management task [P]

2. **From Research**:
   - PostgreSQL RLS decisions → setup and configuration tasks
   - Performance requirements → performance test tasks

3. **From Quickstart**:
   - User isolation scenarios → integration test tasks [P]
   - Admin bypass scenarios → integration test tasks [P]
   - Policy enforcement scenarios → integration test tasks [P]
   - Context management scenarios → integration test tasks [P]

4. **Ordering**:
   - Setup → Tests → Models → Services → Migrations → API → CI → Polish
   - Dependencies block parallel execution

## Validation Checklist
*GATE: Checked by main() before returning*

- [ ] All entities have model tasks
- [ ] All test scenarios from quickstart covered
- [ ] All tests come before implementation
- [ ] Parallel tasks truly independent
- [ ] Each task specifies exact file path
- [ ] No task modifies same file as another [P] task
- [ ] ERD documentation tasks included for database schema changes
- [ ] No user-facing API endpoints for RLS management
- [ ] Internal infrastructure focus maintained throughout
