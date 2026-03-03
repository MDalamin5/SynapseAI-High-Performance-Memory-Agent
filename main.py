from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.database import db
from app.api.chat import router as chat_router

# Initialize Services
# (In this architecture, services utilize the db singleton, so implicit init is fine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- STARTUP ---
    print("🚀 SynapseAI Starting...")
    await db.connect() # Connects BOTH Postgres and Redis
    yield
    # --- SHUTDOWN ---
    print("🛑 SynapseAI Shutting down...")
    await db.close()

app = FastAPI(title="SynapseAI - High Performance Bot", lifespan=lifespan)

app.include_router(chat_router, prefix="/api/v1", tags=["Chat"])

if __name__ == "__main__":
    import uvicorn
    # Workers=1 is fine for AsyncIO, but in prod use gunicorn -k uvicorn.workers.UvicornWorker
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)