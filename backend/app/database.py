"""
Database configuration and session management
"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.config import settings

# Create async engine
# Agregar timeout para SQLite para prevenir bloqueos
connect_args = {}
if "sqlite" in settings.DATABASE_URL:
    connect_args = {
        "timeout": 5.0,  # 5 segundos timeout para SQLite
        "check_same_thread": False
    }

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
    connect_args=connect_args,
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Base class for models
Base = declarative_base()

# Dependency to get database session
async def get_db() -> AsyncSession:
    """Get database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            # Commit automático (puede ser sobrescrito por endpoints específicos)
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

