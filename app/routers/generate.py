from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Episode
from app.schemas import GenerateResponse
from app.tasks.pipeline import run_pipeline

router = APIRouter(prefix="/generate", tags=["generate"])


@router.post("", response_model=GenerateResponse)
async def trigger_generation(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    episode = Episode(
        title=f"Épisode du {datetime.utcnow().strftime('%d/%m/%Y %H:%M')} UTC",
        summary="Génération en cours…",
        status="pending",
    )
    db.add(episode)
    await db.commit()
    await db.refresh(episode)

    background_tasks.add_task(run_pipeline, episode.id)

    return GenerateResponse(
        message="Génération lancée en arrière-plan",
        episode_id=episode.id,
    )
