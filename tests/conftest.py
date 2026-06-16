import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.database import Base, get_db
from app.redis_client import get_redis
from app.routers import accounts, transactions
from fastapi import FastAPI
import httpx
import fakeredis

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

def create_test_app():
    app = FastAPI()
    app.include_router(accounts.router)
    app.include_router(transactions.router)
    return app

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
async def async_client(test_session, fake_redis):
    app = create_test_app()

    async def override_get_db():
        yield test_session

    async def override_get_redis():
        return fake_redis

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

# ⭐ Alias so existing test functions that ask for "client" work
@pytest_asyncio.fixture(scope="function")
async def client(async_client):
    return async_client
