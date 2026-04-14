"""
Database migration utilities

This module provides simple migration support for the video-back application.
For production, consider using Alembic for more robust migration management.
"""

from __future__ import annotations

import asyncio

from persistence.db import Database
from utils.logger import get_logger

logger = get_logger(__name__)


async def create_all_tables(database_url: str) -> None:
    """Create all tables in the database."""
    logger.info("Creating all tables...")
    db = Database(database_url)
    try:
        await db.create_tables()
        logger.info("All tables created successfully")
    finally:
        await db.close()


async def drop_all_tables(database_url: str) -> None:
    """Drop all tables in the database."""
    logger.warning("Dropping all tables...")
    db = Database(database_url)
    try:
        await db.drop_tables()
        logger.info("All tables dropped successfully")
    finally:
        await db.close()


if __name__ == "__main__":
    import sys

    from app.config import get_settings

    settings = get_settings()

    if len(sys.argv) < 2:
        print("Usage: python -m persistence.migrations.init_db [create|drop]")
        sys.exit(1)

    command = sys.argv[1]

    if command == "create":
        asyncio.run(create_all_tables(settings.database_url))
    elif command == "drop":
        asyncio.run(drop_all_tables(settings.database_url))
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
