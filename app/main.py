import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.database import init_db
from app.routers import config, episodes, generate

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
)

AUDIO_DIR = os.environ.get("AUDIO_DIR", "audio")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure models are registered then create tables
    import app.models  # noqa: F401
    await init_db()
    os.makedirs(AUDIO_DIR, exist_ok=True)
    yield


app = FastAPI(
    title="Thotcast API",
    description=(
        "Agent autonome de veille informationnelle et de podcasting automatisé. "
        "Collecte des flux RSS, génère un script via LLM local (Ollama/Llama 3.1) "
        "et produit un épisode MP3 via synthèse vocale (Kokoro)."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.mount("/audio", StaticFiles(directory=AUDIO_DIR), name="audio")

app.include_router(config.router)
app.include_router(episodes.router)
app.include_router(generate.router)


@app.get("/health", tags=["system"])
async def health():
    return {"status": "ok"}
