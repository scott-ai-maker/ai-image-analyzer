"""
Simple database demo to showcase async database operations.
This version focuses on the learning concepts rather than production complexity.
"""

import asyncio
import logging

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.models.database import AnalysisStatus, ApiKey, Base, ImageAnalysis, User

# Simple SQLite setup for demo
DATABASE_URL = "sqlite+aiosqlite:///./demo_database.db"

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


async def demo_database_operations():
    """
    Demonstrate key database concepts that are asked about in interviews.

    This covers:
    1. Async database connections
    2. Creating tables
    3. CRUD operations
    4. Relationships
    5. Transaction management
    """
    logger.info("🚀 Starting Database Demo!")

    # 1. Create async engine
    engine = create_async_engine(DATABASE_URL, echo=True)  # echo=True shows SQL queries

    # 2. Create session factory
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    # 3. Create tables
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    logger.info("✅ Database tables created!")

    # 4. Demonstrate CRUD operations
    await demo_crud_operations(async_session)

    # 5. Demonstrate relationships
    await demo_relationships(async_session)

    # 6. Demonstrate transactions
    await demo_transactions(async_session)

    # 7. Demonstrate queries
    await demo_complex_queries(async_session)

    await engine.dispose()
    logger.info("🎉 Database demo completed!")


async def demo_crud_operations(async_session):
    """Demonstrate Create, Read, Update, Delete operations."""
    logger.info("📝 CRUD Operations Demo")

    async with async_session() as session:
        # CREATE - Insert a new user
        new_user = User(
            email="demo@example.com",
            username="demouser",
            role="user",
            is_active=True,
            is_verified=True,
            preferences={"theme": "dark", "notifications": True},
        )
        session.add(new_user)
        await session.commit()
        logger.info(f"✅ Created user: {new_user.email} (ID: {new_user.id})")

        # READ - Query the user
        result = await session.execute(
            select(User).where(User.email == "demo@example.com")
        )
        user = result.scalar_one_or_none()
        logger.info(
            f"✅ Found user: {user.username} with preferences: {user.preferences}"
        )

        # UPDATE - Modify user data
        user.preferences["notifications"] = False
        user.role = "premium"
        await session.commit()
        logger.info(f"✅ Updated user role to: {user.role}")

        # DELETE (soft delete) - Mark as deleted
        user.is_deleted = True
        user.deleted_at = user.updated_at
        await session.commit()
        logger.info("✅ Soft deleted user (data preserved)")


async def demo_relationships(async_session):
    """Demonstrate database relationships and joins."""
    logger.info("🔗 Relationships Demo")

    async with async_session() as session:
        # Create user and related API key
        user = User(email="relationships@example.com", username="reluser", role="admin")
        session.add(user)
        await session.flush()  # Get the user ID without committing

        # Create API key for the user
        api_key = ApiKey(
            user_id=user.id,
            key_hash="demo_api_key_hash_123",
            name="Demo API Key",
            scopes=["read", "write"],
            is_active=True,
        )
        session.add(api_key)

        # Create image analysis for the user
        analysis = ImageAnalysis(
            user_id=user.id,
            api_key_id=api_key.id,
            image_url="https://example.com/demo.jpg",
            image_hash="demo_hash_456",
            requested_features=["description", "objects"],
            status=AnalysisStatus.COMPLETED,
            processing_time_ms=1200,
            analysis_results={
                "description": "A demo image",
                "objects": ["demo", "object"],
            },
            cost_cents=10,
        )
        session.add(analysis)
        await session.commit()

        # Query with relationships (JOIN)
        result = await session.execute(
            select(User, ApiKey, ImageAnalysis)
            .join(ApiKey, User.id == ApiKey.user_id)
            .join(ImageAnalysis, User.id == ImageAnalysis.user_id)
            .where(User.email == "relationships@example.com")
        )

        for user, api_key, analysis in result:
            logger.info(f"✅ User: {user.email}")
            logger.info(f"   API Key: {api_key.name} (scopes: {api_key.scopes})")
            logger.info(
                f"   Analysis: {analysis.status} - Cost: ${analysis.cost_cents/100:.2f}"
            )


async def demo_transactions(async_session):
    """Demonstrate transaction management - critical for data consistency."""
    logger.info("💳 Transaction Management Demo")

    async with async_session() as session:
        try:
            # Start a transaction
            user = User(
                email="transaction@example.com", username="transuser", role="user"
            )
            session.add(user)
            await session.flush()

            # This will succeed
            analysis1 = ImageAnalysis(
                user_id=user.id,
                image_url="https://example.com/image1.jpg",
                image_hash="hash1",
                requested_features=["description"],
                status=AnalysisStatus.COMPLETED,
                cost_cents=5,
            )
            session.add(analysis1)

            # This could fail (simulating an error)
            analysis2 = ImageAnalysis(
                user_id=user.id,
                image_url="https://example.com/image2.jpg",
                image_hash="hash2",
                requested_features=["description"],
                status=AnalysisStatus.COMPLETED,
                cost_cents=5,
            )
            session.add(analysis2)

            # Commit the transaction
            await session.commit()
            logger.info("✅ Transaction committed successfully")

        except Exception as e:
            # Rollback on error
            await session.rollback()
            logger.error(f"❌ Transaction rolled back due to: {e}")


async def demo_complex_queries(async_session):
    """Demonstrate complex queries that are common in production."""
    logger.info("🔍 Complex Queries Demo")

    async with async_session() as session:
        # Aggregate query - Count analyses by status
        result = await session.execute(
            text(
                """
                SELECT status, COUNT(*) as count, AVG(processing_time_ms) as avg_time
                FROM image_analyses
                WHERE is_deleted = false
                GROUP BY status
                ORDER BY count DESC
            """
            )
        )

        logger.info("📊 Analysis Statistics:")
        for row in result:
            logger.info(
                f"   {row.status}: {row.count} analyses, avg time: {row.avg_time:.1f}ms"
            )

        # Query with pagination (important for large datasets)
        page_size = 5
        offset = 0

        result = await session.execute(
            select(ImageAnalysis)
            .where(ImageAnalysis.is_deleted == False)
            .order_by(ImageAnalysis.created_at.desc())
            .limit(page_size)
            .offset(offset)
        )

        analyses = result.scalars().all()
        logger.info(f"📄 Recent analyses (page 1, {len(analyses)} items):")
        for analysis in analyses:
            logger.info(f"   {analysis.id}: {analysis.status} - {analysis.image_url}")


if __name__ == "__main__":
    asyncio.run(demo_database_operations())
