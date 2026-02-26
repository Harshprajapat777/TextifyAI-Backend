from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.services.nlp_service import nlp_service
from app.routes import spellcheck, predict, chat, files


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: load SymSpell dictionary
    nlp_service.load()
    yield


app = FastAPI(
    title="TextifyAI API",
    description="AI-powered writing assistant backend",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(spellcheck.router, prefix="/api")
app.include_router(predict.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(files.router, prefix="/api")


@app.get("/")
async def root():
    return {"status": "ok", "service": "TextifyAI API"}
