import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.inconsistencies import router as inconsistency_router
from app.api.upload import router as upload_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    if os.environ.get("TESTING") != "1":
        from app.database import Base, engine
        Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="RentRoll",
    description="GARBE Mieterliste CSV → BVI Target Database",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload_router, prefix="/api")
app.include_router(inconsistency_router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok"}
