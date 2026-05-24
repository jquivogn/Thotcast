import logging
import os
import tempfile
from datetime import datetime

from app.database import AsyncSessionLocal
from app.models import Episode
from app.services.audio_assembler import assemble_audio
from app.services.llm import generate_script
from app.services.rss import fetch_and_store_articles
from app.services.tts import synthesize_line

logger = logging.getLogger(__name__)

AUDIO_DIR = os.environ.get("AUDIO_DIR", "audio")


async def run_pipeline(episode_id: int) -> None:
    os.makedirs(AUDIO_DIR, exist_ok=True)

    async with AsyncSessionLocal() as db:
        episode = await db.get(Episode, episode_id)
        if not episode:
            logger.error("Episode %d not found", episode_id)
            return

        try:
            # Step 1 — RSS ingestion
            episode.status = "fetching"
            await db.commit()
            new_articles = await fetch_and_store_articles(db)
            logger.info("Ingested %d new articles", new_articles)

            # Step 2 — Script generation
            episode.status = "generating_script"
            await db.commit()
            title, summary, lines = await generate_script(db)

            episode.title = title
            episode.summary = summary
            episode.script = "\n".join(
                f"[{ln['character']}]: {ln['text']}" for ln in lines
            )
            episode.status = "generating_audio"
            await db.commit()
            logger.info("Script ready: %d lines", len(lines))

            # Step 3 — TTS + assembly
            with tempfile.TemporaryDirectory() as tmpdir:
                line_audio: list[dict] = []

                for i, line in enumerate(lines):
                    wav_path = os.path.join(tmpdir, f"line_{i:04d}.wav")
                    ok = synthesize_line(line["text"], line["voice"], wav_path)
                    if ok:
                        line_audio.append({"path": wav_path, "character": line["character"]})
                    else:
                        logger.warning("TTS skipped line %d: %s", i, line["text"][:60])

                if line_audio:
                    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                    mp3_path = os.path.join(AUDIO_DIR, f"episode_{episode_id}_{timestamp}.mp3")
                    if assemble_audio(line_audio, mp3_path):
                        episode.audio_path = mp3_path
                        episode.status = "done"
                    else:
                        episode.status = "error_audio"
                else:
                    # TTS backend absent — still save script as done
                    episode.status = "done_no_audio"
                    logger.warning("No audio backend available; episode saved without audio")

            await db.commit()
            logger.info(
                "Pipeline complete — episode %d status: %s", episode_id, episode.status
            )

        except Exception as exc:
            logger.error("Pipeline failed for episode %d: %s", episode_id, exc, exc_info=True)
            episode.status = "error"
            episode.summary = str(exc)[:500]
            await db.commit()
