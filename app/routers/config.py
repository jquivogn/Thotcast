from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Config
from app.schemas import ConfigIn, ConfigOut

router = APIRouter(prefix="/config", tags=["config"])

_DEFAULT = {
    "rss_feeds": [
        "https://www.lemonde.fr/rss/une.xml",
        "https://www.lefigaro.fr/rss/figaro_actualites.xml",
        "https://feeds.bbci.co.uk/news/technology/rss.xml",
        "https://www.01net.com/feed/",
    ],
    "keywords": [
        "intelligence artificielle",
        "technologie",
        "science",
        "innovation",
        "numérique",
    ],
    "podcast_structure": [
        {
            "character": "Présentatrice",
            "voice": "af_heart",
            "subject": "Introduction du podcast et présentation des sujets du jour",
        },
        {
            "character": "Intervenant 1",
            "voice": "am_adam",
            "subject": "Revue des principales actualités technologiques et scientifiques",
        },
        {
            "character": "Présentatrice",
            "voice": "af_heart",
            "subject": "Transition vers le focus thématique du jour",
        },
        {
            "character": "Intervenant 2",
            "voice": "am_michael",
            "subject": "Analyse approfondie d'un sujet majeur du jour",
        },
        {
            "character": "Présentatrice",
            "voice": "af_heart",
            "subject": "Conclusion et résumé des points clés du podcast",
        },
    ],
}


async def _get_or_create_config(db: AsyncSession) -> Config:
    result = await db.execute(select(Config).order_by(Config.id.desc()).limit(1))
    config = result.scalar_one_or_none()
    if not config:
        config = Config(**_DEFAULT)
        db.add(config)
        await db.commit()
        await db.refresh(config)
    return config


@router.get("", response_model=ConfigOut)
async def get_config(db: AsyncSession = Depends(get_db)):
    return await _get_or_create_config(db)


@router.post("", response_model=ConfigOut)
async def update_config(payload: ConfigIn, db: AsyncSession = Depends(get_db)):
    config = await _get_or_create_config(db)
    config.rss_feeds = payload.rss_feeds
    config.keywords = payload.keywords
    config.podcast_structure = [s.model_dump() for s in payload.podcast_structure]
    config.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(config)
    return config
