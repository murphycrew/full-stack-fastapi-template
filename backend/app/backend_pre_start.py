import logging

from sqlalchemy import Engine
from sqlmodel import Session, select
from tenacity import after_log, before_log, retry, stop_after_attempt, wait_fixed

from app.core.config import settings
from app.core.db import engine
from app.core.rls import rls_registry

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

max_tries = 60 * 5  # 5 minutes
wait_seconds = 1


@retry(
    stop=stop_after_attempt(max_tries),
    wait=wait_fixed(wait_seconds),
    before=before_log(logger, logging.INFO),
    after=after_log(logger, logging.WARN),
)
def init(db_engine: Engine) -> None:
    try:
        with Session(db_engine) as session:
            # Try to create session to check if DB is awake
            session.exec(select(1))

            # Validate RLS configuration
            validate_rls_configuration(session)

    except Exception as e:
        logger.error(e)
        raise e


def validate_rls_configuration(_session: Session) -> None:
    """Validate RLS configuration and registry."""
    logger.info("Validating RLS configuration...")

    # Check if RLS is enabled
    if settings.RLS_ENABLED:
        logger.info("✅ RLS is enabled")

        # Validate RLS registry
        registered_tables = rls_registry.get_registered_tables()
        registered_models = rls_registry.get_registered_models()

        logger.info("📊 RLS Registry Status:")
        logger.info(f"  • Registered tables: {len(registered_tables)}")
        logger.info(f"  • Registered models: {len(registered_models)}")

        if registered_tables:
            logger.info(f"  • Tables: {', '.join(sorted(registered_tables.keys()))}")

        if registered_models:
            logger.info(
                f"  • Models: {', '.join(sorted(model.__name__ for model in registered_models))}"
            )

        # Validate that we have at least one RLS-scoped model
        if not registered_models:
            logger.warning("⚠️  RLS is enabled but no RLS-scoped models are registered")

        # Check RLS policies in database
        try:
            from app.alembic.rls_policies import check_rls_enabled_for_table

            for table_name in registered_tables.keys():
                rls_enabled = check_rls_enabled_for_table(table_name)
                if rls_enabled:
                    logger.info(f"✅ RLS policies enabled for table: {table_name}")
                else:
                    logger.warning(
                        f"⚠️  RLS policies not enabled for table: {table_name}"
                    )

        except Exception as e:
            logger.warning(f"Could not validate RLS policies in database: {e}")

    else:
        logger.info("ℹ️  RLS is disabled")

    # Validate database roles configuration
    if settings.RLS_APP_USER and settings.RLS_MAINTENANCE_ADMIN:
        logger.info("✅ Database roles configured")
        logger.info(f"  • Application user: {settings.RLS_APP_USER}")
        logger.info(f"  • Maintenance admin: {settings.RLS_MAINTENANCE_ADMIN}")
    else:
        logger.warning("⚠️  Database roles not fully configured")

    logger.info("✅ RLS configuration validation completed")


def main() -> None:
    logger.info("Initializing service")
    init(engine)
    logger.info("Service finished initializing")


if __name__ == "__main__":
    main()
