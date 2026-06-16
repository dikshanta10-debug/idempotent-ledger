import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.database import Base, get_db
import app.redis_client as redis_module
from app.routers import accounts, transactions
from fastapi import FastAPI
from fastapi.testclient import TestClient
import fakeredis

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

# Create a new FastAPI app without any lifespan (no external connections)
def create_test_app():
    app = FastAPI()
    app.include_router(accounts.router)
    app.include_router(transactions.router)
    return app

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
    # Replace the module-level redis_client with our fake
    original = redis_module.redis_client
    redis_module.redis_client = client
    yield client
    redis_module.redis_client = original
    await client.aclose()

@pytest.fixture(scope="function")
def client(test_session, fake_redis):
    app = create_test_app()

    async def override_get_db():
        yield test_session

    app.dependency_overrides[get_db] = override_get_db

    # We no longer need to override get_redis because the module-level client is already fake
    # But to keep router-level Depends happy, we provide a no-op override
    app.dependency_overrides[redis_module.get_redis] = lambda: fake_redis

    with TestClient(app) as c:
        yield c
