from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config
from sqlalchemy import pool

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import the project's settings and database Base so autogenerate can inspect metadata
from app.config import settings
# Import the app.database module which defines one declarative Base (may be a fallback)
from app import database as app_database
# Import model modules to ensure they are registered with the declarative Base
# Import the models' Base definition (the project uses app.models.base.Base)
from app.models import base as models_base

# Prefer the Base used by app.models (so autogenerate sees model classes registered there).
# Fallback to app_database.Base if needed.
if getattr(models_base, 'Base', None) is not None:
    target_metadata = getattr(models_base, 'Base').metadata
else:
    target_metadata = getattr(app_database, 'Base', None).metadata if getattr(app_database, 'Base',
                                                                              None) is not None else None

# Ensure the DB URL from app.config is used if not set in alembic.ini
db_url = str(settings.DATABASE_URL) if settings.DATABASE_URL is not None else config.get_main_option('sqlalchemy.url')
if db_url:
    config.set_main_option('sqlalchemy.url', db_url)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
