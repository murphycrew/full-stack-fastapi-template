import logging

from sqlmodel import Session

from app import crud
from app.core.config import settings
from app.core.db import engine, init_db
from app.models import UserCreate

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_initial_users(session: Session) -> None:
    """Create initial users for RLS demonstration."""

    # Create initial superuser (admin)
    superuser = crud.get_user_by_email(session=session, email=settings.FIRST_SUPERUSER)
    if not superuser:
        user_in = UserCreate(
            email=settings.FIRST_SUPERUSER,
            password=settings.FIRST_SUPERUSER_PASSWORD,
            full_name="Initial Admin User",
            is_superuser=True,
        )
        superuser = crud.create_user(session=session, user_create=user_in)
        logger.info(f"Created initial superuser: {superuser.email}")
    else:
        logger.info(f"Initial superuser already exists: {superuser.email}")

    # Create initial regular user
    regular_user = crud.get_user_by_email(session=session, email=settings.FIRST_USER)
    if not regular_user:
        user_in = UserCreate(
            email=settings.FIRST_USER,
            password=settings.FIRST_USER_PASSWORD,
            full_name="Initial Regular User",
            is_superuser=False,
        )
        regular_user = crud.create_user(session=session, user_create=user_in)
        logger.info(f"Created initial regular user: {regular_user.email}")
    else:
        logger.info(f"Initial regular user already exists: {regular_user.email}")


def init() -> None:
    with Session(engine) as session:
        init_db(session)
        create_initial_users(session)


def main() -> None:
    logger.info("Creating initial data")
    init()
    logger.info("Initial data created")


if __name__ == "__main__":
    main()
