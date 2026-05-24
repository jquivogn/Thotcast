import os

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Episode
from app.schemas import EpisodeOut

router = APIRouter(prefix="/episodes", tags=["episodes"])

BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000")


def _to_schema(ep: Episode) -> EpisodeOut:
    audio_url = None
    if ep.audio_path and os.path.exists(ep.audio_path):
        filename = os.path.basename(ep.audio_path)
        audio_url = f"{BASE_URL}/audio/{filename}"
    return EpisodeOut(
        id=ep.id,
        title=ep.title,
        summary=ep.summary,
        audio_url=audio_url,
        status=ep.status,
        created_at=ep.created_at,
    )


@router.get("", response_model=list[EpisodeOut])
async def list_episodes(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Episode).order_by(Episode.created_at.desc()))
    return [_to_schema(ep) for ep in result.scalars().all()]


@router.get("/{episode_id}", response_model=EpisodeOut)
async def get_episode(episode_id: int, db: AsyncSession = Depends(get_db)):
    ep = await db.get(Episode, episode_id)
    if not ep:
        raise HTTPException(status_code=404, detail="Episode not found")
    return _to_schema(ep)
