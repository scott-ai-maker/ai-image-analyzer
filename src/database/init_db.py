"""
Database initialization and management script.

This script handles:
- Database connection testing
- Table creation for development
- Sample data insertion
- Database health verification

In production, you would use Alembic migrations instead of direct table creation.
"""

import asyncio
import logging
from typing import List

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from src.database.config import db_config
from src.models.database import User, ApiKey, ImageAnalysis, AnalysisStatus
from src.core.config import Settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def init_database():
    """
    Initialize database with tables and sample data.
    
    This demonstrates:
    - Async database operations
    - Transaction management
    - Error handling
    - Sample data creation
    """
    logger.info("Starting database initialization...")
    
    # Initialize database connection
    await db_config.initialize()
    
    # Test connection
    if not await db_config.test_connection():
        logger.error("Database connection failed!")
        return False
    
    # Create tables (in production, use Alembic migrations)
    await db_config.create_tables()
    
    # Insert sample data for development
    await create_sample_data()
    
    logger.info("Database initialization completed successfully!")
    return True


async def create_sample_data():
    """
    Create sample users and data for development.
    
    Interview Question: How do you handle data insertion conflicts?
    Answer: Use ON CONFLICT clauses or try/except with IntegrityError.
    """
    logger.info("Creating sample data...")
    
    async with db_config.get_session() as session:
        try:
            # Create sample users
            users_data = [
                {
                    "email": "john.doe@example.com",
                    "username": "johndoe",
                    "role": "user",
                    "is_active": True,
                    "is_verified": True,
                    "preferences": {
                        "default_features": ["description", "objects"],
                        "notifications": True
                    }
                },
                {
                    "email": "jane.admin@example.com", 
                    "username": "janeadmin",
                    "role": "admin",
                    "is_active": True,
                    "is_verified": True,
                    "preferences": {
                        "default_features": ["description", "objects", "text", "faces"],
                        "notifications": False
                    }
                },
                {
                    "email": "premium.user@example.com",
                    "username": "premiumuser", 
                    "role": "premium",
                    "is_active": True,
                    "is_verified": True,
                    "preferences": {
                        "default_features": ["description", "objects", "text"],
                        "notifications": True
                    }
                }
            ]
            
            created_users = []
            for user_data in users_data:
                # Check if user already exists
                result = await session.execute(
                    select(User).where(User.email == user_data["email"])
                )
                existing_user = result.scalar_one_or_none()
                
                if existing_user:
                    logger.info(f"User {user_data['email']} already exists, skipping...")
                    created_users.append(existing_user)
                    continue
                
                # Create new user
                user = User(**user_data)
                session.add(user)
                created_users.append(user)
                logger.info(f"Created user: {user_data['email']}")
            
            # Commit users first
            await session.commit()
            
            # Create API keys for users
            for user in created_users:
                # Check if API key already exists
                result = await session.execute(
                    select(ApiKey).where(ApiKey.user_id == user.id)
                )
                existing_key = result.scalar_one_or_none()
                
                if existing_key:
                    logger.info(f"API key for user {user.email} already exists, skipping...")
                    continue
                
                # Create API key (in production, use proper key generation and hashing)
                api_key = ApiKey(
                    user_id=user.id,
                    key_hash=f"dev_key_hash_{user.username}",  # In production: hash the actual key
                    name=f"{user.username}_default_key",
                    scopes=["read", "write"] if user.role == "admin" else ["read"],
                    is_active=True
                )
                session.add(api_key)
                logger.info(f"Created API key for user: {user.email}")
            
            await session.commit()
            
            # Create sample analysis records
            await create_sample_analyses(session, created_users)
            
            logger.info("Sample data created successfully!")
            
        except IntegrityError as e:
            await session.rollback()
            logger.warning(f"Some sample data already exists: {e}")
        except Exception as e:
            await session.rollback()
            logger.error(f"Error creating sample data: {e}")
            raise


async def create_sample_analyses(session, users: List[User]):
    """Create sample image analysis records."""
    
    # Sample analysis data
    sample_analyses = [
        {
            "image_url": "https://example.com/sample1.jpg",
            "image_hash": "abc123def456789",
            "image_size_bytes": 1024000,
            "image_format": "JPEG",
            "image_dimensions": {"width": 1920, "height": 1080},
            "requested_features": ["description", "objects"],
            "status": AnalysisStatus.COMPLETED,
            "processing_time_ms": 1500,
            "analysis_results": {
                "description": "A beautiful sunset over mountains",
                "objects": ["mountain", "sky", "sun", "clouds"],
                "confidence": 0.95
            },
            "confidence_scores": {
                "description": 0.95,
                "objects": {"mountain": 0.98, "sky": 0.97, "sun": 0.93, "clouds": 0.89}
            },
            "cost_cents": 5  # 5 cents per analysis
        },
        {
            "image_url": "https://example.com/sample2.jpg", 
            "image_hash": "def456ghi789abc",
            "image_size_bytes": 2048000,
            "image_format": "PNG",
            "image_dimensions": {"width": 800, "height": 600},
            "requested_features": ["description", "text"],
            "status": AnalysisStatus.COMPLETED,
            "processing_time_ms": 2100,
            "analysis_results": {
                "description": "A street sign with text",
                "text": "Main Street",
                "confidence": 0.88
            },
            "confidence_scores": {
                "description": 0.88,
                "text": 0.92
            },
            "cost_cents": 7
        }
    ]
    
    for i, analysis_data in enumerate(sample_analyses):
        user = users[i % len(users)]  # Distribute analyses among users
        
        # Check if analysis already exists
        result = await session.execute(
            select(ImageAnalysis).where(ImageAnalysis.image_hash == analysis_data["image_hash"])
        )
        existing_analysis = result.scalar_one_or_none()
        
        if existing_analysis:
            continue
        
        # Create analysis record
        analysis = ImageAnalysis(
            user_id=user.id,
            **analysis_data
        )
        session.add(analysis)
    
    await session.commit()


async def check_database_status():
    """
    Check database status and print summary.
    
    Useful for debugging and monitoring.
    """
    logger.info("Checking database status...")
    
    await db_config.initialize()
    
    # Test connection
    connection_ok = await db_config.test_connection()
    logger.info(f"Database connection: {'OK' if connection_ok else 'FAILED'}")
    
    if not connection_ok:
        return
    
    # Count records in each table
    async with db_config.get_session() as session:
        # Count users
        result = await session.execute(select(User))
        user_count = len(result.scalars().all())
        
        # Count API keys
        result = await session.execute(select(ApiKey))
        api_key_count = len(result.scalars().all())
        
        # Count analyses
        result = await session.execute(select(ImageAnalysis))
        analysis_count = len(result.scalars().all())
        
        logger.info(f"Database summary:")
        logger.info(f"  Users: {user_count}")
        logger.info(f"  API Keys: {api_key_count}")
        logger.info(f"  Analyses: {analysis_count}")


async def reset_database():
    """
    Reset database for development.
    
    WARNING: This deletes all data!
    """
    logger.warning("Resetting database - ALL DATA WILL BE LOST!")
    
    await db_config.initialize()
    await db_config.drop_tables()
    await db_config.create_tables()
    await create_sample_data()
    
    logger.info("Database reset completed!")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "init":
            asyncio.run(init_database())
        elif command == "status":
            asyncio.run(check_database_status())
        elif command == "reset":
            asyncio.run(reset_database())
        else:
            print("Usage: python init_db.py [init|status|reset]")
    else:
        # Default: initialize database
        asyncio.run(init_database())