"""
Database configuration and connection management.

This demonstrates production-grade database patterns:
- Async connection pooling for high performance
- Connection lifecycle management
- Health checking and monitoring
- Environment-specific configuration
- Graceful shutdown handling
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Optional
from urllib.parse import quote_plus

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool, QueuePool

from src.core.config import Settings
from src.models.database import Base

logger = logging.getLogger(__name__)


class DatabaseConfig:
    """
    Database configuration management.

    Interview Question: How do you handle database connections
    in a high-throughput async application?
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self.engine: Optional[AsyncEngine] = None
        self.session_factory: Optional[async_sessionmaker] = None
        self._connection_tested = False

    def _build_database_url(self) -> str:
        """
        Build database URL with proper encoding.

        Production Tip: Always URL-encode passwords to handle special characters.
        """
        # For demo purposes, use SQLite if PostgreSQL is not available
        # In production, always use PostgreSQL
        if (
            self.settings.environment == "development"
            and not self.settings.use_postgresql
        ):
            # SQLite for development demo
            return "sqlite+aiosqlite:///./ai_image_analyzer.db"

        # Use environment variables for database connection
        host = self.settings.database_host
        port = self.settings.database_port
        user = self.settings.database_user
        password = quote_plus(self.settings.database_password)  # URL encode password
        database = self.settings.database_name

        # Build async PostgreSQL URL
        return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}"

    def _configure_engine_options(self) -> dict:
        """
        Configure SQLAlchemy engine options for production.

        Key Concepts:
        - Connection pooling for performance
        - Pool recycling to handle connection timeouts
        - Echo for development debugging
        """
        options = {
            "echo": self.settings.debug,  # Log SQL queries in development
            "echo_pool": self.settings.debug,  # Log connection pool events
            "future": True,  # Use SQLAlchemy 2.0 style
        }

        # Check if using SQLite (for development/demo)
        database_url = self._build_database_url()
        is_sqlite = database_url.startswith("sqlite")

        # Connection pool configuration
        if self.settings.environment == "testing" or is_sqlite:
            # Use NullPool for testing or SQLite to avoid connection issues
            options["poolclass"] = NullPool
        else:
            # Production connection pool settings (PostgreSQL)
            options.update(
                {
                    "poolclass": QueuePool,
                    "pool_size": self.settings.database_pool_size,  # Base number of connections
                    "max_overflow": self.settings.database_max_overflow,  # Extra connections when needed
                    "pool_timeout": self.settings.database_pool_timeout,  # Wait time for connection
                    "pool_recycle": self.settings.database_pool_recycle,  # Recycle connections (prevent timeouts)
                    "pool_pre_ping": True,  # Validate connections before use
                }
            )

        return options

    async def initialize(self) -> None:
        """
        Initialize database engine and session factory.

        This is called during application startup.
        """
        logger.info("Initializing database connection...")

        database_url = self._build_database_url()
        engine_options = self._configure_engine_options()

        # Create async engine
        self.engine = create_async_engine(database_url, **engine_options)

        # Create session factory
        self.session_factory = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,  # Don't expire objects after commit
            autoflush=True,  # Automatically flush before queries
            autocommit=False,  # Explicit transaction control
        )

        # Set up engine event listeners for monitoring
        self._setup_engine_events()

        logger.info("Database engine initialized successfully")

    def _setup_engine_events(self) -> None:
        """
        Set up SQLAlchemy event listeners for monitoring and debugging.

        Production Pattern: Monitor database performance and connection health.
        """

        @event.listens_for(self.engine.sync_engine, "connect")
        def on_connect(dbapi_connection, connection_record):
            """Configure connection-level settings."""
            logger.debug("Database connection established")

            # Set connection-level parameters for PostgreSQL
            with dbapi_connection.cursor() as cursor:
                # Set statement timeout to prevent hanging queries
                cursor.execute("SET statement_timeout = '30s'")
                # Set timezone
                cursor.execute("SET timezone = 'UTC'")

        @event.listens_for(self.engine.sync_engine, "checkout")
        def on_checkout(dbapi_connection, connection_record, connection_proxy):
            """Called when connection is retrieved from pool."""
            logger.debug("Connection checked out from pool")

        @event.listens_for(self.engine.sync_engine, "checkin")
        def on_checkin(dbapi_connection, connection_record):
            """Called when connection is returned to pool."""
            logger.debug("Connection returned to pool")

    async def test_connection(self) -> bool:
        """
        Test database connectivity.

        Used for health checks and startup validation.
        """
        if not self.engine:
            return False

        try:
            async with self.engine.begin() as connection:
                result = await connection.execute(text("SELECT 1"))
                row = result.fetchone()
                success = row[0] == 1

                if success and not self._connection_tested:
                    logger.info("Database connection test successful")
                    self._connection_tested = True

                return success

        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False

    async def create_tables(self) -> None:
        """
        Create database tables.

        Note: In production, use Alembic migrations instead!
        This is only for development and testing.
        """
        if not self.engine:
            raise RuntimeError("Database engine not initialized")

        logger.info("Creating database tables...")

        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        logger.info("Database tables created successfully")

    async def drop_tables(self) -> None:
        """
        Drop all database tables.

        WARNING: This deletes all data! Only use in development/testing.
        """
        if not self.engine:
            raise RuntimeError("Database engine not initialized")

        if self.settings.environment == "production":
            raise RuntimeError("Cannot drop tables in production environment")

        logger.warning("Dropping all database tables...")

        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)

        logger.info("Database tables dropped")

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get database session with automatic cleanup.

        This is the primary way to interact with the database.

        Usage:
            async with db_config.get_session() as session:
                result = await session.execute(select(User))
        """
        if not self.session_factory:
            raise RuntimeError("Database not initialized")

        session = self.session_factory()
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    async def close(self) -> None:
        """
        Close database engine and all connections.

        Called during application shutdown.
        """
        if self.engine:
            logger.info("Closing database connections...")
            await self.engine.dispose()
            logger.info("Database connections closed")


# Global database instance
db_config = DatabaseConfig(Settings())


# Dependency for FastAPI endpoints
async def get_database_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for database sessions.

    Usage in endpoints:
        @app.get("/users")
        async def get_users(session: AsyncSession = Depends(get_database_session)):
            result = await session.execute(select(User))
            return result.scalars().all()
    """
    async with db_config.get_session() as session:
        yield session


# Database health check function
async def check_database_health() -> dict:
    """
    Check database health for monitoring endpoints.

    Returns connection status, pool statistics, etc.
    """
    health_info = {"status": "unhealthy", "connection_test": False, "pool_info": {}}

    try:
        # Test basic connectivity
        health_info["connection_test"] = await db_config.test_connection()

        # Get pool statistics if available
        if db_config.engine and hasattr(db_config.engine.pool, "size"):
            pool = db_config.engine.pool
            health_info["pool_info"] = {
                "size": pool.size(),
                "checked_in": pool.checkedin(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
                "total": pool.size() + pool.overflow(),
            }

        health_info["status"] = (
            "healthy" if health_info["connection_test"] else "unhealthy"
        )

    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        health_info["error"] = str(e)

    return health_info
