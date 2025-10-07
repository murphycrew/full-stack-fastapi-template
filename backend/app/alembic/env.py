import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
# target_metadata = None

from app.models import SQLModel  # noqa
from app.core.config import settings # noqa
from app.core.rls import rls_registry, policy_generator # noqa

target_metadata = SQLModel.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def get_url():
    return str(settings.SQLALCHEMY_DATABASE_URI)


def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = get_url()
    context.configure(
        url=url, target_metadata=target_metadata, literal_binds=True, compare_type=True
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    RLS policies are automatically applied after migrations if RLS is enabled.

    """
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata, compare_type=True
        )

        with context.begin_transaction():
            context.run_migrations()

            # Apply RLS policies after migrations if RLS is enabled
            if settings.RLS_ENABLED:
                apply_rls_policies(connection)


def apply_rls_policies(connection):
    """Apply RLS policies to all registered RLS-scoped tables."""
    from sqlalchemy import text

    # Get all registered RLS tables
    registered_tables = rls_registry.get_registered_tables()

    for table_name, metadata in registered_tables.items():
        try:
            # Generate and execute RLS setup SQL
            rls_sql_statements = policy_generator.generate_complete_rls_setup_sql(table_name)

            for sql_statement in rls_sql_statements:
                connection.execute(text(sql_statement))

            print(f"Applied RLS policies to table: {table_name}")

        except Exception as e:
            print(f"Warning: Failed to apply RLS policies to table {table_name}: {e}")
            # Continue with other tables even if one fails


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
