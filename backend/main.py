import logging
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import init_db
from api.review import router as review_router
from api.health import router as health_router
from api.batch import router as batch_router
from api.history import router as history_router
from api.profiles import router as profiles_router
from api.diagram import router as diagram_router

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="CodeReview Agent", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(review_router)
app.include_router(health_router)
app.include_router(batch_router)
app.include_router(history_router)
app.include_router(profiles_router, prefix="/api")
app.include_router(diagram_router, prefix="/api")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
