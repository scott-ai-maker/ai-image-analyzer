"""
Working Database Demo - Cross-Database Compatible

This demonstrates all the key database concepts for senior developer interviews:
1. Async database operations
2. CRUD operations with proper error handling
3. Database relationships and joins
4. Transaction management
5. Complex queries and aggregations
6. Connection management and pooling concepts
"""

import asyncio
import logging

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.models.database_compatible import (
    AnalysisStatus,
    ApiKey,
    Base,
    ImageAnalysis,
    User,
)

# Database configuration
DATABASE_URL = "sqlite+aiosqlite:///./ai_analyzer_demo.db"

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


class DatabaseDemo:
    """
    Database demonstration class.

    Interview Pattern: Organize database operations in a service class.
    This shows proper separation of concerns and testability.
    """

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = None
        self.async_session = None

    async def initialize(self):
        """Initialize database connection and tables."""
        logger.info("🚀 Initializing Database Demo...")

        # Create async engine
        self.engine = create_async_engine(
            self.database_url,
            echo=False,  # Set to True to see SQL queries
            future=True,
        )

        # Create session factory
        self.async_session = async_sessionmaker(
            self.engine, expire_on_commit=False, class_=AsyncSession
        )

        # Create all tables
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        logger.info("✅ Database initialized successfully!")

    async def demonstrate_crud_operations(self):
        """
        Demonstrate Create, Read, Update, Delete operations.

        Interview Focus: Basic database operations with async/await.
        """
        logger.info("\n📝 CRUD Operations Demo")

        async with self.async_session() as session:
            # CREATE - Insert new records
            users_data = [
                {
                    "email": "alice@example.com",
                    "username": "alice",
                    "role": "user",
                    "is_active": True,
                    "is_verified": True,
                    "preferences": {"theme": "light", "notifications": True},
                },
                {
                    "email": "bob@example.com",
                    "username": "bob",
                    "role": "premium",
                    "is_active": True,
                    "is_verified": True,
                    "preferences": {"theme": "dark", "notifications": False},
                },
                {
                    "email": "admin@example.com",
                    "username": "admin",
                    "role": "admin",
                    "is_active": True,
                    "is_verified": True,
                    "preferences": {"theme": "auto", "notifications": True},
                },
            ]

            created_users = []
            for user_data in users_data:
                user = User(**user_data)
                session.add(user)
                created_users.append(user)

            await session.commit()
            logger.info(f"✅ Created {len(created_users)} users")

            # READ - Query with different patterns

            # Simple query
            result = await session.execute(
                select(User).where(User.email == "alice@example.com")
            )
            alice = result.scalar_one_or_none()
            logger.info(f"✅ Found user: {alice.username} with role: {alice.role}")

            # Query with filtering and ordering
            result = await session.execute(
                select(User)
                .where(User.is_active == True)
                .order_by(User.created_at.desc())
            )
            active_users = result.scalars().all()
            logger.info(f"✅ Found {len(active_users)} active users")

            # UPDATE - Modify existing records
            alice.preferences["notifications"] = False
            alice.role = "premium"
            await session.commit()
            logger.info(f"✅ Updated Alice's role to: {alice.role}")

            # Bulk update example
            await session.execute(select(User).where(User.role == "user"))
            # In production: session.execute(update(User).where(...).values(...))

            # DELETE (Soft delete) - Mark as deleted without removing data
            bob = await session.get(User, created_users[1].id)
            bob.is_deleted = True
            bob.deleted_at = func.now()
            await session.commit()
            logger.info("✅ Soft deleted Bob (data preserved for audit)")

    async def demonstrate_relationships(self):
        """
        Demonstrate database relationships and joins.

        Interview Focus: Foreign keys, relationships, and join queries.
        """
        logger.info("\n🔗 Database Relationships Demo")

        async with self.async_session() as session:
            # Get an existing user
            result = await session.execute(
                select(User).where(User.email == "alice@example.com")
            )
            alice = result.scalar_one_or_none()

            if not alice:
                logger.error("Alice not found - run CRUD demo first")
                return

            # Create API key for Alice
            api_key = ApiKey(
                user_id=alice.id,
                key_hash="alice_api_key_hash_123",
                name="Alice's Development Key",
                scopes=["read", "write"],
                is_active=True,
                usage_count=0,
            )
            session.add(api_key)
            await session.flush()  # Get the ID without committing

            # Create image analyses for Alice
            analyses_data = [
                {
                    "user_id": alice.id,
                    "api_key_id": api_key.id,
                    "image_url": "https://example.com/sunset.jpg",
                    "image_hash": "sunset_hash_123",
                    "image_dimensions": {"width": 1920, "height": 1080},
                    "requested_features": ["description", "objects"],
                    "status": AnalysisStatus.COMPLETED,
                    "processing_time_ms": 1250,
                    "analysis_results": {
                        "description": "A beautiful sunset over mountains",
                        "objects": ["mountain", "sunset", "sky", "clouds"],
                    },
                    "confidence_scores": {
                        "description": 0.94,
                        "objects": {"mountain": 0.98, "sunset": 0.91},
                    },
                    "cost_cents": 5,
                },
                {
                    "user_id": alice.id,
                    "api_key_id": api_key.id,
                    "image_url": "https://example.com/cityscape.jpg",
                    "image_hash": "city_hash_456",
                    "image_dimensions": {"width": 800, "height": 600},
                    "requested_features": ["description", "text"],
                    "status": AnalysisStatus.COMPLETED,
                    "processing_time_ms": 1800,
                    "analysis_results": {
                        "description": "Urban cityscape with buildings",
                        "text": ["CITY HALL", "MAIN ST"],
                    },
                    "confidence_scores": {"description": 0.89, "text": 0.95},
                    "cost_cents": 7,
                },
            ]

            for analysis_data in analyses_data:
                analysis = ImageAnalysis(**analysis_data)
                session.add(analysis)

            await session.commit()
            logger.info("✅ Created API key and analyses for Alice")

            # Demonstrate JOIN queries

            # Simple join using relationships
            result = await session.execute(
                select(User, ApiKey)
                .join(ApiKey, User.id == ApiKey.user_id)
                .where(User.email == "alice@example.com")
            )

            for user, api_key in result:
                logger.info(f"✅ User: {user.email}")
                logger.info(f"   API Key: {api_key.name} (scopes: {api_key.scopes})")

            # Complex join with aggregation
            result = await session.execute(
                select(
                    User.username,
                    func.count(ImageAnalysis.id).label("analysis_count"),
                    func.sum(ImageAnalysis.cost_cents).label("total_cost_cents"),
                    func.avg(ImageAnalysis.processing_time_ms).label(
                        "avg_processing_time"
                    ),
                )
                .join(ImageAnalysis, User.id == ImageAnalysis.user_id)
                .where(User.is_deleted == False)
                .group_by(User.id, User.username)
                .order_by(func.count(ImageAnalysis.id).desc())
            )

            logger.info("📊 User Analysis Summary:")
            for row in result:
                total_cost = row.total_cost_cents / 100 if row.total_cost_cents else 0
                avg_time = row.avg_processing_time or 0
                logger.info(
                    f"   {row.username}: {row.analysis_count} analyses, ${total_cost:.2f} total, {avg_time:.0f}ms avg"
                )

    async def demonstrate_transactions(self):
        """
        Demonstrate transaction management.

        Interview Focus: ACID properties, rollback scenarios, data consistency.
        """
        logger.info("\n💳 Transaction Management Demo")

        # Scenario 1: Successful transaction
        try:
            async with self.async_session() as session:
                # Create user and related data in a single transaction
                user = User(
                    email="transaction@example.com", username="transuser", role="user"
                )
                session.add(user)
                await session.flush()  # Get user ID

                # Create API key
                api_key = ApiKey(
                    user_id=user.id,
                    key_hash="trans_key_hash",
                    name="Transaction Test Key",
                    scopes=["read"],
                )
                session.add(api_key)

                # Create analysis
                analysis = ImageAnalysis(
                    user_id=user.id,
                    api_key_id=api_key.id,
                    image_url="https://example.com/test.jpg",
                    image_hash="test_hash",
                    requested_features=["description"],
                    status=AnalysisStatus.COMPLETED,
                    cost_cents=3,
                )
                session.add(analysis)

                # Commit all changes together
                await session.commit()
                logger.info(
                    "✅ Transaction 1: Successfully created user with related data"
                )

        except Exception as e:
            logger.error(f"❌ Transaction 1 failed: {e}")

        # Scenario 2: Transaction with rollback
        try:
            async with self.async_session() as session:
                user = User(
                    email="rollback@example.com", username="rollbackuser", role="user"
                )
                session.add(user)
                await session.flush()

                # This would succeed
                api_key = ApiKey(
                    user_id=user.id,
                    key_hash="rollback_key_hash",
                    name="Rollback Test Key",
                    scopes=["read"],
                )
                session.add(api_key)

                # Simulate an error condition
                # In real scenarios, this could be a business rule violation,
                # external service failure, etc.
                if True:  # Simulating an error
                    raise ValueError("Simulated business logic error")

                await session.commit()

        except Exception as e:
            # The session automatically rolls back on exception
            logger.info(f"✅ Transaction 2: Properly rolled back due to: {e}")

    async def demonstrate_complex_queries(self):
        """
        Demonstrate complex queries used in production.

        Interview Focus: Performance, aggregations, subqueries, pagination.
        """
        logger.info("\n🔍 Complex Queries Demo")

        async with self.async_session() as session:
            # 1. Aggregation query with grouping
            result = await session.execute(
                select(
                    ImageAnalysis.status,
                    func.count(ImageAnalysis.id).label("count"),
                    func.avg(ImageAnalysis.processing_time_ms).label("avg_time"),
                    func.min(ImageAnalysis.processing_time_ms).label("min_time"),
                    func.max(ImageAnalysis.processing_time_ms).label("max_time"),
                )
                .where(ImageAnalysis.is_deleted == False)
                .group_by(ImageAnalysis.status)
                .order_by(func.count(ImageAnalysis.id).desc())
            )

            logger.info("📊 Analysis Statistics by Status:")
            for row in result:
                logger.info(f"   {row.status}: {row.count} analyses")
                if row.avg_time:
                    logger.info(
                        f"      Times: {row.avg_time:.0f}ms avg, {row.min_time}-{row.max_time}ms range"
                    )

            # 2. Subquery example - Find users with above-average spending
            avg_spending_subquery = (
                select(func.avg(ImageAnalysis.cost_cents))
                .where(ImageAnalysis.is_deleted == False)
                .scalar_subquery()
            )

            result = await session.execute(
                select(
                    User.username,
                    func.sum(ImageAnalysis.cost_cents).label("total_spent"),
                )
                .join(ImageAnalysis, User.id == ImageAnalysis.user_id)
                .where(User.is_deleted == False)
                .group_by(User.id, User.username)
                .having(func.sum(ImageAnalysis.cost_cents) > avg_spending_subquery)
                .order_by(func.sum(ImageAnalysis.cost_cents).desc())
            )

            logger.info("💰 High-spending users (above average):")
            for row in result:
                logger.info(f"   {row.username}: ${row.total_spent/100:.2f}")

            # 3. Pagination example (critical for large datasets)
            page_size = 2
            offset = 0

            result = await session.execute(
                select(ImageAnalysis)
                .join(User, ImageAnalysis.user_id == User.id)
                .where(ImageAnalysis.is_deleted == False)
                .order_by(ImageAnalysis.created_at.desc())
                .limit(page_size)
                .offset(offset)
            )

            analyses = result.scalars().all()
            logger.info(f"📄 Recent analyses (page 1, {len(analyses)} items):")
            for analysis in analyses:
                logger.info(f"   {analysis.image_url}: {analysis.status}")

            # 4. Raw SQL for complex operations
            result = await session.execute(
                text(
                    """
                    SELECT
                        DATE(created_at) as analysis_date,
                        COUNT(*) as daily_count,
                        SUM(cost_cents) as daily_revenue_cents
                    FROM image_analyses
                    WHERE is_deleted = 0
                    GROUP BY DATE(created_at)
                    ORDER BY analysis_date DESC
                    LIMIT 5
                """
                )
            )

            logger.info("📅 Daily analysis summary (last 5 days):")
            for row in result:
                revenue = (
                    row.daily_revenue_cents / 100 if row.daily_revenue_cents else 0
                )
                logger.info(
                    f"   {row.analysis_date}: {row.daily_count} analyses, ${revenue:.2f} revenue"
                )

    async def demonstrate_performance_patterns(self):
        """
        Demonstrate performance optimization patterns.

        Interview Focus: N+1 queries, eager loading, indexing strategies.
        """
        logger.info("\n⚡ Performance Optimization Demo")

        async with self.async_session() as session:
            # Bad: N+1 query problem (avoid this!)
            logger.info("❌ N+1 Query Problem Example (DON'T DO THIS):")

            # This creates N+1 queries: 1 for users + N queries for each user's analyses
            users = await session.execute(select(User).where(User.is_deleted == False))
            user_list = users.scalars().all()

            for user in user_list:
                # This triggers a separate query for each user - BAD!
                analyses = await session.execute(
                    select(ImageAnalysis).where(ImageAnalysis.user_id == user.id)
                )
                analysis_count = len(analyses.scalars().all())
                logger.info(f"   {user.username}: {analysis_count} analyses")

            # Good: Single query with JOIN (do this instead!)
            logger.info("✅ Optimized Query with JOIN:")

            result = await session.execute(
                select(
                    User.username, func.count(ImageAnalysis.id).label("analysis_count")
                )
                .outerjoin(ImageAnalysis, User.id == ImageAnalysis.user_id)
                .where(User.is_deleted == False)
                .group_by(User.id, User.username)
                .order_by(User.username)
            )

            for row in result:
                logger.info(f"   {row.username}: {row.analysis_count} analyses")

    async def cleanup(self):
        """Clean up database connections."""
        if self.engine:
            await self.engine.dispose()
            logger.info("✅ Database connections closed")


async def run_complete_demo():
    """
    Run the complete database demonstration.

    This covers all major database concepts for senior developer interviews.
    """
    demo = DatabaseDemo(DATABASE_URL)

    try:
        await demo.initialize()
        await demo.demonstrate_crud_operations()
        await demo.demonstrate_relationships()
        await demo.demonstrate_transactions()
        await demo.demonstrate_complex_queries()
        await demo.demonstrate_performance_patterns()

        logger.info("\n🎉 Database Demo Completed Successfully!")
        logger.info("\nKey Concepts Demonstrated:")
        logger.info("✅ Async database operations with SQLAlchemy")
        logger.info("✅ CRUD operations with proper error handling")
        logger.info("✅ Database relationships and joins")
        logger.info("✅ Transaction management and rollback")
        logger.info("✅ Complex queries and aggregations")
        logger.info("✅ Performance optimization (avoiding N+1 queries)")
        logger.info("✅ Cross-database compatibility patterns")

    finally:
        await demo.cleanup()


if __name__ == "__main__":
    asyncio.run(run_complete_demo())
