from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from starfall.config import settings
from starfall.database import SessionLocal, init_db
from starfall.routers import agents, core
from starfall.seed import seed_demo_data


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    with SessionLocal() as db:
        seed_demo_data(db)
    yield


app = FastAPI(
    title="Starfall Merchandise Handling API",
    description="API for Starfall Space Merchandise Handling Co.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(core.router, tags=["core"])
app.include_router(agents.router)


@app.get("/")
def root() -> dict:
    return {
        "company": settings.company_name,
        "docs": "/docs",
        "agents": "/agents",
    }
