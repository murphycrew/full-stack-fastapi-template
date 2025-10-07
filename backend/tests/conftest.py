from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, delete

from app.core.config import settings
from app.core.db import engine, init_db
from app.crud import create_user
from app.main import app
from app.models import Item, User, UserCreate
from tests.utils.user import authentication_token_from_email
from tests.utils.utils import get_superuser_token_headers, random_email


@pytest.fixture(scope="function", autouse=True)
def db() -> Generator[Session, None, None]:
    with Session(engine) as session:
        init_db(session)
        yield session
        # Clean up after each test
        try:
            statement = delete(Item)
            session.execute(statement)
            statement = delete(User)
            session.execute(statement)
            session.commit()
        except Exception:
            # If cleanup fails, rollback to ensure clean state
            session.rollback()


@pytest.fixture(scope="function")
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="function")
def superuser_token_headers(client: TestClient) -> dict[str, str]:
    return get_superuser_token_headers(client)


@pytest.fixture(scope="function")
def normal_user_token_headers(client: TestClient, db: Session) -> dict[str, str]:
    return authentication_token_from_email(
        client=client, email=settings.EMAIL_TEST_USER, db=db
    )


@pytest.fixture(scope="function")
def inactive_user(db: Session) -> User:
    """Create an inactive user for testing."""
    email = random_email()
    user_in = UserCreate(
        email=email, password="changethis", full_name="Inactive User", is_active=False
    )
    return create_user(session=db, user_create=user_in)
