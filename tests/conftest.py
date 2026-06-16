import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.database import Base, get_db
from app.redis_client import get_redis
from fastapi import FastAPI
import httpx
import fakeredis
from contextlib import asynccontextmanager

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

@pytest_asyncio.fixture(scope="function")
async def test_engine():
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        connect_args={"timeout": 30}
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest_asyncio.fixture(scope="function")
async def test_session(test_engine):
    async_session = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session

@pytest_asyncio.fixture(scope="function")
async def fake_redis():
    client = fakeredis.FakeAsyncRedis(decode_responses=True)
    yield client
    await client.aclose()

@pytest_asyncio.fixture(scope="function")
async def client(test_session, fake_redis):
    # Import the real app but remove its lifespan (which connects to real DB/Redis)
    from app.main import app as real_app

    @asynccontextmanager
    async def dummy_lifespan(app: FastAPI):
        yield

    real_app.router.lifespan_context = dummy_lifespan

    async def override_get_db():
        yield test_session

    async def override_get_redis():
        return fake_redis

    real_app.dependency_overrides[get_db] = override_get_db
    real_app.dependency_overrides[get_redis] = override_get_redis

    transport = httpx.ASGITransport(app=real_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
