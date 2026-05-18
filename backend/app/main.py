"""FastAPI application entry."""
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.database import AsyncSessionLocal, Base, engine

import models  # noqa: F401 — registers ORM metadata
from models.case import Case
from routers import cases as cases_router
from routers import extract as extract_router
from routers import prospective as prospective_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Case).where(Case.id == 1))
        if res.scalar_one_or_none() is None:
            session.add(Case(id=1, name="Cas per defecte"))
            await session.commit()
    yield


app = FastAPI(title="EINA API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"message": "EINA API", "docs": "/docs"}


app.include_router(
    prospective_router.router,
    prefix="/api/prospective",
    tags=["Prospective Analysis"],
)
app.include_router(
    extract_router.router,
    prefix="/api/extract",
    tags=["Extraction Pipeline"],
)
app.include_router(
    cases_router.router,
    prefix="/api/cases",
    tags=["Cases"],
)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
