import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.analytics import router as analytics_router
from app.api.bvi_import import router as bvi_import_router
from app.api.chat import router as chat_router
from app.api.reports import router as reports_router
from app.api.excel_roundtrip import router as excel_roundtrip_router
from app.api.inconsistencies import router as inconsistency_router
from app.api.master_data import router as master_data_router
from app.api.periods import router as periods_router
from app.api.transform import router as transform_router
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
app.include_router(excel_roundtrip_router, prefix="/api")
app.include_router(transform_router, prefix="/api")
app.include_router(periods_router, prefix="/api")
app.include_router(master_data_router, prefix="/api")
app.include_router(bvi_import_router, prefix="/api")
app.include_router(analytics_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
app.include_router(reports_router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok"}
