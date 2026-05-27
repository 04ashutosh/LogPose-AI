from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from app.core.config import settings
from app.core.database import engine, Base
from app.api import auth, chat, keys

app = FastAPI(title=settings.PROJECT_NAME)

# Setup CORS for development interface
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Router Nodes
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(chat.router, prefix=settings.API_V1_STR)
app.include_router(keys.router, prefix=settings.API_V1_STR)

@app.on_event("startup")
async def startup_event():
    # Automatically bootstrap schemas into local PostgreSQL Database
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.get("/")
def health_check():
    return {"status": "online", "platform": "LogPose AI Orchestrator"}

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)