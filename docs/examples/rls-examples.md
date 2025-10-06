# RLS Examples and Use Cases

This document provides practical examples of implementing and using Row-Level Security (RLS) in the FastAPI template project.

## Table of Contents

- [Basic Model Creation](#basic-model-creation)
- [API Endpoint Examples](#api-endpoint-examples)
- [CRUD Operations](#crud-operations)
- [Admin Operations](#admin-operations)
- [Advanced Use Cases](#advanced-use-cases)
- [Testing Examples](#testing-examples)

## Basic Model Creation

### Creating a Simple RLS-Scoped Model

```python
from uuid import UUID, uuid4
from typing import Optional
from datetime import datetime

from sqlmodel import Field, Relationship, SQLModel
from app.core.rls import UserScopedBase

class Task(UserScopedBase, table=True):
    __tablename__ = "task"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    title: str = Field(max_length=255)
    description: Optional[str] = None
    completed: bool = Field(default=False)
    due_date: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # owner_id is automatically inherited from UserScopedBase
    # owner relationship is automatically available
    owner: User = Relationship(back_populates="tasks")

# Update User model to include the relationship
class User(UserBase, table=True):
    # ... existing fields ...

    tasks: List[Task] = Relationship(back_populates="owner", cascade_delete=True)
```

### Creating a Complex RLS-Scoped Model with Relationships

```python
class Project(UserScopedBase, table=True):
    __tablename__ = "project"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(max_length=255)
    description: Optional[str] = None
    status: str = Field(default="active")  # active, completed, archived
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    owner: User = Relationship(back_populates="projects")
    tasks: List[Task] = Relationship(back_populates="project", cascade_delete=True)

class Task(UserScopedBase, table=True):
    __tablename__ = "task"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    title: str = Field(max_length=255)
    description: Optional[str] = None
    completed: bool = Field(default=False)
    due_date: Optional[datetime] = None

    # Foreign key to project (also user-scoped)
    project_id: UUID = Field(foreign_key="project.id")

    # Relationships
    owner: User = Relationship(back_populates="tasks")
    project: Project = Relationship(back_populates="tasks")

# Update User model
class User(UserBase, table=True):
    # ... existing fields ...

    projects: List[Project] = Relationship(back_populates="owner", cascade_delete=True)
    tasks: List[Task] = Relationship(back_populates="owner", cascade_delete=True)
```

## API Endpoint Examples

### Basic CRUD Endpoints

```python
from fastapi import APIRouter, HTTPException, status
from sqlmodel import select
from typing import List

from app.api.deps import RLSSessionDep, CurrentUser
from app.models import Task, TaskCreate, TaskUpdate, TaskPublic
from app import crud

router = APIRouter(prefix="/tasks", tags=["tasks"])

@router.get("/", response_model=List[TaskPublic])
def read_tasks(
    session: RLSSessionDep,
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 100
) -> List[TaskPublic]:
    """Get user's tasks (RLS enforced)."""
    tasks = crud.get_tasks(session=session, owner_id=current_user.id, skip=skip, limit=limit)
    return tasks

@router.get("/{task_id}", response_model=TaskPublic)
def read_task(
    task_id: UUID,
    session: RLSSessionDep,
    current_user: CurrentUser
) -> TaskPublic:
    """Get a specific task (RLS enforced)."""
    task = crud.get_task(session=session, task_id=task_id, owner_id=current_user.id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@router.post("/", response_model=TaskPublic)
def create_task(
    task_in: TaskCreate,
    session: RLSSessionDep,
    current_user: CurrentUser
) -> TaskPublic:
    """Create a new task (RLS enforced)."""
    task = crud.create_task(session=session, task_in=task_in, owner_id=current_user.id)
    return task

@router.put("/{task_id}", response_model=TaskPublic)
def update_task(
    task_id: UUID,
    task_in: TaskUpdate,
    session: RLSSessionDep,
    current_user: CurrentUser
) -> TaskPublic:
    """Update a task (RLS enforced)."""
    task = crud.get_task(session=session, task_id=task_id, owner_id=current_user.id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    try:
        task = crud.update_task(session=session, db_task=task, task_in=task_in, owner_id=current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))

    return task

@router.delete("/{task_id}")
def delete_task(
    task_id: UUID,
    session: RLSSessionDep,
    current_user: CurrentUser
) -> dict:
    """Delete a task (RLS enforced)."""
    task = crud.delete_task(session=session, task_id=task_id, owner_id=current_user.id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return {"message": "Task deleted successfully"}
```

### Advanced Query Endpoints

```python
@router.get("/search/", response_model=List[TaskPublic])
def search_tasks(
    q: str,
    completed: Optional[bool] = None,
    session: RLSSessionDep,
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 100
) -> List[TaskPublic]:
    """Search user's tasks with filters."""
    tasks = crud.search_tasks(
        session=session,
        owner_id=current_user.id,
        query=q,
        completed=completed,
        skip=skip,
        limit=limit
    )
    return tasks

@router.get("/due/", response_model=List[TaskPublic])
def get_due_tasks(
    days_ahead: int = 7,
    session: RLSSessionDep,
    current_user: CurrentUser
) -> List[TaskPublic]:
    """Get tasks due within specified days."""
    from datetime import datetime, timedelta

    due_date = datetime.utcnow() + timedelta(days=days_ahead)
    tasks = crud.get_due_tasks(session=session, owner_id=current_user.id, due_date=due_date)
    return tasks

@router.get("/stats/", response_model=dict)
def get_task_stats(
    session: RLSSessionDep,
    current_user: CurrentUser
) -> dict:
    """Get task statistics for the user."""
    stats = crud.get_task_stats(session=session, owner_id=current_user.id)
    return stats
```

## CRUD Operations

### User-Scoped CRUD Functions

```python
# In app/crud.py

def create_task(*, session: Session, task_in: TaskCreate, owner_id: UUID) -> Task:
    """Create a new task for a specific user."""
    db_task = Task.model_validate(task_in, update={"owner_id": owner_id})
    session.add(db_task)
    session.commit()
    session.refresh(db_task)
    return db_task

def get_task(*, session: Session, task_id: UUID, owner_id: UUID) -> Task | None:
    """Get a task by ID, ensuring it belongs to the owner."""
    statement = select(Task).where(Task.id == task_id, Task.owner_id == owner_id)
    return session.exec(statement).first()

def get_tasks(*, session: Session, owner_id: UUID, skip: int = 0, limit: int = 100) -> list[Task]:
    """Get tasks for a specific owner."""
    statement = select(Task).where(Task.owner_id == owner_id).offset(skip).limit(limit)
    return session.exec(statement).all()

def update_task(*, session: Session, db_task: Task, task_in: TaskUpdate, owner_id: UUID) -> Task:
    """Update a task, ensuring it belongs to the owner."""
    # Verify ownership
    if db_task.owner_id != owner_id:
        raise ValueError("Task does not belong to the specified owner")

    task_data = task_in.model_dump(exclude_unset=True)
    db_task.sqlmodel_update(task_data)
    session.add(db_task)
    session.commit()
    session.refresh(db_task)
    return db_task

def delete_task(*, session: Session, task_id: UUID, owner_id: UUID) -> Task | None:
    """Delete a task, ensuring it belongs to the owner."""
    db_task = get_task(session=session, task_id=task_id, owner_id=owner_id)
    if db_task:
        session.delete(db_task)
        session.commit()
    return db_task

def search_tasks(*, session: Session, owner_id: UUID, query: str, completed: Optional[bool] = None, skip: int = 0, limit: int = 100) -> list[Task]:
    """Search tasks for a specific owner."""
    statement = select(Task).where(Task.owner_id == owner_id)

    if query:
        statement = statement.where(Task.title.contains(query) | Task.description.contains(query))

    if completed is not None:
        statement = statement.where(Task.completed == completed)

    statement = statement.offset(skip).limit(limit)
    return session.exec(statement).all()

def get_task_stats(*, session: Session, owner_id: UUID) -> dict:
    """Get task statistics for a specific owner."""
    from sqlmodel import func

    total = session.exec(select(func.count()).select_from(Task).where(Task.owner_id == owner_id)).one()
    completed = session.exec(select(func.count()).select_from(Task).where(Task.owner_id == owner_id, Task.completed == True)).one()

    return {
        "total": total,
        "completed": completed,
        "pending": total - completed,
        "completion_rate": (completed / total * 100) if total > 0 else 0
    }
```

## Admin Operations

### Admin-Only Endpoints

```python
from app.api.deps import AdminSessionDep, ReadOnlyAdminSessionDep

@router.get("/admin/all", response_model=List[TaskPublic])
def read_all_tasks_admin(
    session: AdminSessionDep,
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 100
) -> List[TaskPublic]:
    """Get all tasks (admin only)."""
    tasks = crud.get_all_tasks_admin(session=session, skip=skip, limit=limit)
    return tasks

@router.get("/admin/user/{user_id}", response_model=List[TaskPublic])
def read_user_tasks_admin(
    user_id: UUID,
    session: AdminSessionDep,
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 100
) -> List[TaskPublic]:
    """Get tasks for a specific user (admin only)."""
    tasks = crud.get_tasks(session=session, owner_id=user_id, skip=skip, limit=limit)
    return tasks

@router.post("/admin/", response_model=TaskPublic)
def create_task_admin(
    task_in: TaskCreate,
    owner_id: UUID,
    session: AdminSessionDep,
    current_user: CurrentUser
) -> TaskPublic:
    """Create a task for any user (admin only)."""
    task = crud.create_task(session=session, task_in=task_in, owner_id=owner_id)
    return task

@router.put("/admin/{task_id}", response_model=TaskPublic)
def update_task_admin(
    task_id: UUID,
    task_in: TaskUpdate,
    session: AdminSessionDep,
    current_user: CurrentUser
) -> TaskPublic:
    """Update any task (admin only)."""
    task = crud.get_task_admin(session=session, task_id=task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task = crud.update_task_admin(session=session, db_task=task, task_in=task_in)
    return task

@router.delete("/admin/{task_id}")
def delete_task_admin(
    task_id: UUID,
    session: AdminSessionDep,
    current_user: CurrentUser
) -> dict:
    """Delete any task (admin only)."""
    task = crud.delete_task_admin(session=session, task_id=task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return {"message": "Task deleted successfully"}

@router.get("/admin/stats/", response_model=dict)
def get_all_task_stats_admin(
    session: ReadOnlyAdminSessionDep,
    current_user: CurrentUser
) -> dict:
    """Get task statistics for all users (read-only admin)."""
    from sqlmodel import func

    total = session.exec(select(func.count()).select_from(Task)).one()
    completed = session.exec(select(func.count()).select_from(Task).where(Task.completed == True)).one()

    # Get per-user stats
    user_stats = session.exec(
        select(
            Task.owner_id,
            func.count().label('total'),
            func.sum(func.cast(Task.completed, Integer)).label('completed')
        )
        .group_by(Task.owner_id)
    ).all()

    return {
        "global": {
            "total": total,
            "completed": completed,
            "pending": total - completed,
            "completion_rate": (completed / total * 100) if total > 0 else 0
        },
        "by_user": [
            {
                "user_id": str(stat.owner_id),
                "total": stat.total,
                "completed": stat.completed,
                "pending": stat.total - stat.completed
            }
            for stat in user_stats
        ]
    }
```

### Admin CRUD Functions

```python
# Admin CRUD operations (bypass RLS)

def get_all_tasks_admin(*, session: Session, skip: int = 0, limit: int = 100) -> list[Task]:
    """Get all tasks (admin operation)."""
    statement = select(Task).offset(skip).limit(limit)
    return session.exec(statement).all()

def get_task_admin(*, session: Session, task_id: UUID) -> Task | None:
    """Get any task by ID (admin operation)."""
    statement = select(Task).where(Task.id == task_id)
    return session.exec(statement).first()

def update_task_admin(*, session: Session, db_task: Task, task_in: TaskUpdate) -> Task:
    """Update any task (admin operation)."""
    task_data = task_in.model_dump(exclude_unset=True)
    db_task.sqlmodel_update(task_data)
    session.add(db_task)
    session.commit()
    session.refresh(db_task)
    return db_task

def delete_task_admin(*, session: Session, task_id: UUID) -> Task | None:
    """Delete any task (admin operation)."""
    db_task = get_task_admin(session=session, task_id=task_id)
    if db_task:
        session.delete(db_task)
        session.commit()
    return db_task
```

## Advanced Use Cases

### Batch Operations

```python
@router.post("/batch/", response_model=List[TaskPublic])
def create_batch_tasks(
    tasks_in: List[TaskCreate],
    session: RLSSessionDep,
    current_user: CurrentUser
) -> List[TaskPublic]:
    """Create multiple tasks in a single operation."""
    tasks = []
    for task_in in tasks_in:
        task = crud.create_task(session=session, task_in=task_in, owner_id=current_user.id)
        tasks.append(task)
    return tasks

@router.put("/batch/complete", response_model=dict)
def complete_batch_tasks(
    task_ids: List[UUID],
    session: RLSSessionDep,
    current_user: CurrentUser
) -> dict:
    """Mark multiple tasks as completed."""
    completed_count = 0
    for task_id in task_ids:
        task = crud.get_task(session=session, task_id=task_id, owner_id=current_user.id)
        if task and not task.completed:
            task.completed = True
            session.add(task)
            completed_count += 1

    session.commit()
    return {"message": f"Completed {completed_count} tasks"}
```

### Complex Queries with RLS

```python
@router.get("/analytics/", response_model=dict)
def get_task_analytics(
    session: RLSSessionDep,
    current_user: CurrentUser,
    days: int = 30
) -> dict:
    """Get task analytics for the user."""
    from datetime import datetime, timedelta
    from sqlmodel import func, and_

    start_date = datetime.utcnow() - timedelta(days=days)

    # Tasks created in the last N days
    created = session.exec(
        select(func.count()).select_from(Task)
        .where(and_(Task.owner_id == current_user.id, Task.created_at >= start_date))
    ).one()

    # Tasks completed in the last N days
    completed = session.exec(
        select(func.count()).select_from(Task)
        .where(and_(Task.owner_id == current_user.id, Task.completed == True))
    ).one()

    # Average completion time (for completed tasks)
    avg_completion_time = session.exec(
        select(func.avg(func.extract('epoch', Task.updated_at - Task.created_at)))
        .select_from(Task)
        .where(and_(Task.owner_id == current_user.id, Task.completed == True))
    ).one()

    return {
        "period_days": days,
        "tasks_created": created,
        "tasks_completed": completed,
        "completion_rate": (completed / created * 100) if created > 0 else 0,
        "avg_completion_time_hours": (avg_completion_time / 3600) if avg_completion_time else 0
    }
```

### Using Admin Context Manager

```python
from app.core.rls import AdminContext

def bulk_import_tasks(session: Session, tasks_data: List[dict], target_user_id: UUID) -> List[Task]:
    """Import tasks for a specific user using admin context."""
    tasks = []

    with AdminContext.create_full_admin(target_user_id, session) as admin_ctx:
        for task_data in tasks_data:
            task = Task(
                title=task_data["title"],
                description=task_data.get("description"),
                owner_id=target_user_id
            )
            session.add(task)
            tasks.append(task)

        session.commit()

        # Refresh all tasks
        for task in tasks:
            session.refresh(task)

    return tasks
```

## Testing Examples

### Unit Tests for RLS Models

```python
import pytest
from uuid import uuid4
from app.models import Task, User, TaskCreate
from app.core.rls import UserScopedBase

def test_task_inherits_user_scoped_base():
    """Test that Task inherits from UserScopedBase."""
    assert issubclass(Task, UserScopedBase)

    # Check that owner_id field exists
    assert hasattr(Task, 'owner_id')

def test_task_creation_with_owner():
    """Test creating a task with an owner."""
    user_id = uuid4()
    task = Task(
        title="Test Task",
        description="Test Description",
        owner_id=user_id
    )

    assert task.owner_id == user_id
    assert task.title == "Test Task"
    assert task.completed == False  # Default value

@pytest.fixture
def test_user(session: Session) -> User:
    """Create a test user."""
    user = User(
        email="test@example.com",
        hashed_password="hashed_password",
        full_name="Test User"
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user

@pytest.fixture
def test_task(session: Session, test_user: User) -> Task:
    """Create a test task."""
    task = Task(
        title="Test Task",
        description="Test Description",
        owner_id=test_user.id
    )
    session.add(task)
    session.commit()
    session.refresh(task)
    return task

def test_task_crud_operations(session: Session, test_user: User):
    """Test CRUD operations for tasks."""
    # Create
    task_in = TaskCreate(title="New Task", description="New Description")
    task = crud.create_task(session=session, task_in=task_in, owner_id=test_user.id)

    assert task.title == "New Task"
    assert task.owner_id == test_user.id

    # Read
    retrieved_task = crud.get_task(session=session, task_id=task.id, owner_id=test_user.id)
    assert retrieved_task is not None
    assert retrieved_task.title == "New Task"

    # Update
    task_in_update = TaskUpdate(title="Updated Task")
    updated_task = crud.update_task(
        session=session,
        db_task=task,
        task_in=task_in_update,
        owner_id=test_user.id
    )
    assert updated_task.title == "Updated Task"

    # Delete
    deleted_task = crud.delete_task(session=session, task_id=task.id, owner_id=test_user.id)
    assert deleted_task is not None

    # Verify deletion
    retrieved_task = crud.get_task(session=session, task_id=task.id, owner_id=test_user.id)
    assert retrieved_task is None
```

### Integration Tests for RLS Isolation

```python
def test_user_isolation(session: Session):
    """Test that users can only see their own tasks."""
    # Create two users
    user1 = User(email="user1@example.com", hashed_password="password")
    user2 = User(email="user2@example.com", hashed_password="password")
    session.add_all([user1, user2])
    session.commit()
    session.refresh(user1)
    session.refresh(user2)

    # Create tasks for each user
    task1 = Task(title="User 1 Task", owner_id=user1.id)
    task2 = Task(title="User 2 Task", owner_id=user2.id)
    session.add_all([task1, task2])
    session.commit()

    # Set context for user1
    session.execute(text(f"SET app.user_id = '{user1.id}'"))
    session.execute(text("SET app.role = 'user'"))

    # User1 should only see their own task
    user1_tasks = session.exec(select(Task)).all()
    assert len(user1_tasks) == 1
    assert user1_tasks[0].title == "User 1 Task"

    # Set context for user2
    session.execute(text(f"SET app.user_id = '{user2.id}'"))
    session.execute(text("SET app.role = 'user'"))

    # User2 should only see their own task
    user2_tasks = session.exec(select(Task)).all()
    assert len(user2_tasks) == 1
    assert user2_tasks[0].title == "User 2 Task"

def test_admin_bypass(session: Session, test_user: User):
    """Test that admin users can see all tasks."""
    # Create tasks for regular user
    task1 = Task(title="Regular Task", owner_id=test_user.id)
    session.add(task1)
    session.commit()

    # Set admin context
    with AdminContext.create_full_admin(test_user.id, session) as admin_ctx:
        # Admin should see all tasks
        all_tasks = session.exec(select(Task)).all()
        assert len(all_tasks) >= 1

        # Admin should be able to update any task
        task1.title = "Admin Updated Task"
        session.add(task1)
        session.commit()

        assert task1.title == "Admin Updated Task"
```

### API Endpoint Tests

```python
def test_create_task_endpoint(client: TestClient, user_token_headers: dict):
    """Test creating a task via API."""
    task_data = {
        "title": "API Test Task",
        "description": "Created via API"
    }

    response = client.post(
        "/api/v1/tasks/",
        json=task_data,
        headers=user_token_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "API Test Task"
    assert "id" in data
    assert "owner_id" in data

def test_get_user_tasks_endpoint(client: TestClient, user_token_headers: dict):
    """Test getting user's tasks via API."""
    response = client.get(
        "/api/v1/tasks/",
        headers=user_token_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

    # Each task should belong to the authenticated user
    user_id = client.get("/api/v1/users/me", headers=user_token_headers).json()["id"]
    for task in data:
        assert task["owner_id"] == user_id

def test_admin_get_all_tasks_endpoint(client: TestClient, admin_token_headers: dict):
    """Test admin endpoint to get all tasks."""
    response = client.get(
        "/api/v1/tasks/admin/all",
        headers=admin_token_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    # Admin should see tasks from all users

def test_regular_user_cannot_access_admin_endpoint(client: TestClient, user_token_headers: dict):
    """Test that regular users cannot access admin endpoints."""
    response = client.get(
        "/api/v1/tasks/admin/all",
        headers=user_token_headers
    )

    assert response.status_code == 403
```

These examples demonstrate the full range of RLS functionality in the FastAPI template, from basic model creation to advanced admin operations and comprehensive testing strategies.
