from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.database import engine, Base
from app.redis_client import redis_client
from app.routers import accounts, transactions

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await redis_client.ping()
    yield
    await engine.dispose()
    await redis_client.close()

app = FastAPI(title="Idempotent Transaction Ledger", lifespan=lifespan)

app.include_router(accounts.router)
app.include_router(transactions.router)

@app.get("/health")
async def health():
    return {"status": "ok"}
