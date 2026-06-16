import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.database import Base, get_db
from fastapi import FastAPI
from fastapi.testclient import TestClient
import fakeredis

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

@pytest_asyncio.fixture(scope="function")
async def test_session():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest_asyncio.fixture(scope="function")
async def fake_redis():
    client = fakeredis.FakeAsyncRedis(decode_responses=True)
    yield client
    await client.aclose()

@pytest.fixture(scope="function")
def client(test_session, fake_redis):
    # 1) Patch the Redis module BEFORE importing any app code that uses Redis
    import app.redis_client as redis_mod
    redis_mod.redis_client = fake_redis
    async def fake_get_redis():
        return fake_redis
    redis_mod.get_redis = fake_get_redis

    # 2) NOW import the routers (and thus services) – they’ll see the patched redis module
    from app.routers import accounts, transactions

    app = FastAPI()
    app.include_router(accounts.router)
    app.include_router(transactions.router)

    # 3) Override the database session
    async def override_get_db():
        yield test_session
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c
