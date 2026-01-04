"""
Pytest configuration and fixtures for EINA Platform tests
"""
import pytest
import asyncio
from typing import AsyncGenerator, Generator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.database import Base, get_db
from app.main import app
from models import *  # Import all models to ensure they're registered


# Test database URL (in-memory SQLite)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def db_engine():
    """Create a test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Drop all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture(scope="function")
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async_session_maker = async_sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session_maker() as session:
        yield session
        await session.rollback()


@pytest.fixture(scope="function")
def test_client(db_session: AsyncSession) -> TestClient:
    """Create a test client with database override."""
    def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as client:
        yield client
    
    app.dependency_overrides.clear()


@pytest.fixture
def mock_ai_service(monkeypatch):
    """Mock AIService to avoid actual OpenAI API calls."""
    from unittest.mock import AsyncMock, MagicMock
    
    mock_service = AsyncMock()
    mock_service.client = MagicMock()
    mock_service.model = "gpt-4"
    
    # Mock common methods
    mock_service.analyze_as_geopolitical_expert = AsyncMock(return_value={
        "analysis_type": "geopolitical",
        "bilateral_relations": [],
        "key_insights": ["Test insight"]
    })
    
    mock_service.analyze_as_investment_advisor = AsyncMock(return_value={
        "analysis_type": "investment",
        "recommendations": [],
        "key_insights": ["Test insight"]
    })
    
    mock_service.analyze_as_reputation_manager = AsyncMock(return_value={
        "analysis_type": "reputation",
        "crisis_analysis": {"crisis_level": "none"},
        "key_insights": ["Test insight"]
    })
    
    mock_service.analyze_as_public_affairs_consultant = AsyncMock(return_value={
        "analysis_type": "public_affairs",
        "stakeholder_analysis": [],
        "key_insights": ["Test insight"]
    })
    
    return mock_service


@pytest.fixture
def mock_api_services(monkeypatch):
    """Mock external API services."""
    from unittest.mock import AsyncMock
    
    mocks = {
        "news_api": AsyncMock(),
        "reddit_api": AsyncMock(),
        "permutable_api": AsyncMock(),
        "alphavantage_api": AsyncMock(),
        "finnhub_api": AsyncMock(),
        "ensembledata_api": AsyncMock(),
    }
    
    # Default responses
    mocks["news_api"].search = AsyncMock(return_value={
        "status": "ok",
        "articles": []
    })
    
    mocks["reddit_api"].search = AsyncMock(return_value={
        "data": {"children": []}
    })
    
    mocks["permutable_api"].get_geopolitical_events = AsyncMock(return_value={
        "status": "success",
        "events": []
    })
    
    return mocks


@pytest.fixture
async def sample_case(db_session: AsyncSession):
    """Create a sample case for testing."""
    from models.case import Case, CaseType, CaseStatus
    from datetime import datetime
    
    case = Case(
        name="Test Case",
        description="Test case description",
        case_type=CaseType.GEOPOLITICAL,
        status=CaseStatus.PENDING,
        created_at=datetime.now()
    )
    db_session.add(case)
    await db_session.commit()
    await db_session.refresh(case)
    return case


@pytest.fixture
async def sample_osint_data(db_session: AsyncSession, sample_case):
    """Create sample OSINT data for testing."""
    from models.osint import OSINTQuery, OSINTResult, OSINTQueryType
    from datetime import datetime
    
    query = OSINTQuery(
        case_id=sample_case.id,
        query_type=OSINTQueryType.NEWS,
        query_text="test query",
        created_at=datetime.now()
    )
    db_session.add(query)
    await db_session.flush()
    
    result = OSINTResult(
        query_id=query.id,
        data={"title": "Test article", "content": "Test content"},
        status="completed",
        created_at=datetime.now()
    )
    db_session.add(result)
    await db_session.commit()
    
    return {"query": query, "result": result}



