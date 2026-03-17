"""Programmatic Alembic Migration Runner for PostgreSQL.

Provides a CLI and programmatic interface for running
Alembic migrations against the PostgreSQL database.

Usage (CLI):
    poetry run python -m docmind.dbase.psql.services.migrate upgrade
    poetry run python -m docmind.dbase.psql.services.migrate downgrade
    poetry run python -m docmind.dbase.psql.services.migrate current
    poetry run python -m docmind.dbase.psql.services.migrate history
    poetry run python -m docmind.dbase.psql.services.migrate generate "add new column"

Usage (Programmatic):
    from docmind.dbase.psql.services.migrate import upgrade
    upgrade()  # Runs all pending migrations
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

from alembic import command
from alembic.config import Config

logger = logging.getLogger(__name__)


def _find_project_root() -> Path:
    """Find project root by locating alembic.ini.

    Walks up from the current file's directory until alembic.ini is found.

    Returns:
        Path: Absolute path to the project root.

    Raises:
        FileNotFoundError: If alembic.ini cannot be found.
    """
    current = Path(__file__).resolve().parent
    for _ in range(10):
        if (current / "alembic.ini").exists():
            return current
        current = current.parent
    raise FileNotFoundError(
        "Could not find alembic.ini in parent directories. "
        "Ensure you are running from within the project."
    )


def get_alembic_config() -> Config:
    """Get Alembic Config object pointing to the project root.

    The actual database URL is resolved in alembic/env.py from
    the application's Pydantic settings.

    Returns:
        Config: Alembic configuration object.
    """
    project_root = _find_project_root()
    alembic_ini = project_root / "alembic.ini"

    config = Config(str(alembic_ini))

    # Ensure script_location is absolute (relative to project root)
    script_location = config.get_main_option("script_location")
    if script_location and not Path(script_location).is_absolute():
        config.set_main_option("script_location", str(project_root / script_location))

    return config


def upgrade(revision: str = "head") -> None:
    """Run Alembic upgrade to specified revision."""
    config = get_alembic_config()
    logger.info("Running PostgreSQL migration upgrade to: %s", revision)
    command.upgrade(config, revision)
    logger.info("PostgreSQL migration upgrade complete")


def downgrade(revision: str = "-1") -> None:
    """Run Alembic downgrade to specified revision."""
    config = get_alembic_config()
    logger.info("Running PostgreSQL migration downgrade to: %s", revision)
    command.downgrade(config, revision)
    logger.info("PostgreSQL migration downgrade complete")


def current() -> None:
    """Show current Alembic revision."""
    config = get_alembic_config()
    command.current(config, verbose=True)


def history() -> None:
    """Show Alembic migration history."""
    config = get_alembic_config()
    command.history(config, verbose=True)


def generate(message: str, autogenerate: bool = True) -> None:
    """Generate a new Alembic migration revision."""
    config = get_alembic_config()
    logger.info("Generating new migration: %s", message)
    command.revision(config, message=message, autogenerate=autogenerate)
    logger.info("Migration file generated successfully")


def heads() -> None:
    """Show current available heads."""
    config = get_alembic_config()
    command.heads(config, verbose=True)


def check() -> None:
    """Check if there are pending migrations."""
    config = get_alembic_config()
    command.check(config)


def main(args: Optional[list] = None) -> None:
    """CLI entry point for PostgreSQL migration management."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="PostgreSQL Migration Tool (DocMind-VLM)",
    )
    subparsers = parser.add_subparsers(dest="command", help="Migration command")

    # upgrade
    up_parser = subparsers.add_parser("upgrade", help="Upgrade database to a revision")
    up_parser.add_argument(
        "revision", nargs="?", default="head", help="Target revision (default: head)"
    )

    # downgrade
    down_parser = subparsers.add_parser(
        "downgrade", help="Downgrade database to a revision"
    )
    down_parser.add_argument(
        "revision",
        nargs="?",
        default="-1",
        help="Target revision (default: -1, one step back)",
    )

    # current
    subparsers.add_parser("current", help="Show current revision")

    # history
    subparsers.add_parser("history", help="Show migration history")

    # generate
    gen_parser = subparsers.add_parser(
        "generate", help="Generate new migration from model changes"
    )
    gen_parser.add_argument(
        "message", help='Migration description (e.g., "add user preferences")'
    )
    gen_parser.add_argument(
        "--no-autogenerate",
        action="store_true",
        help="Generate empty migration (no auto-detection)",
    )

    # heads
    subparsers.add_parser("heads", help="Show current available heads")

    # check
    subparsers.add_parser("check", help="Check for pending migrations")

    parsed = parser.parse_args(args)

    if not parsed.command:
        parser.print_help()
        sys.exit(1)

    try:
        if parsed.command == "upgrade":
            upgrade(parsed.revision)
        elif parsed.command == "downgrade":
            downgrade(parsed.revision)
        elif parsed.command == "current":
            current()
        elif parsed.command == "history":
            history()
        elif parsed.command == "generate":
            generate(parsed.message, autogenerate=not parsed.no_autogenerate)
        elif parsed.command == "heads":
            heads()
        elif parsed.command == "check":
            check()
    except Exception as e:
        logger.error("Migration failed: %s", e, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
