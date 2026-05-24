import logging
import os

from pydub import AudioSegment  # type: ignore

logger = logging.getLogger(__name__)

# Silence durations in milliseconds
_PAUSE_SAME_SPEAKER = 300
_PAUSE_DIFF_SPEAKER = 800


def assemble_audio(line_audio_paths: list[dict], output_path: str) -> bool:
    """
    Concatenate per-line audio files into a single MP3.

    Each entry in line_audio_paths must have keys:
      - "path": str  — path to the WAV/audio file
      - "character": str — speaker name (used to insert longer pauses on speaker change)
    """
    try:
        combined = AudioSegment.empty()
        prev_character: str | None = None

        for item in line_audio_paths:
            path: str = item["path"]
            character: str = item["character"]

            if not os.path.exists(path):
                logger.warning("Audio file not found, skipping: %s", path)
                continue

            segment = AudioSegment.from_file(path)

            if prev_character is not None:
                pause_ms = (
                    _PAUSE_DIFF_SPEAKER
                    if character != prev_character
                    else _PAUSE_SAME_SPEAKER
                )
                combined += AudioSegment.silent(duration=pause_ms)

            combined += segment
            prev_character = character

        if len(combined) == 0:
            logger.error("No audio segments assembled — output skipped")
            return False

        combined.export(output_path, format="mp3", bitrate="128k")
        logger.info(
            "Audio assembled → %s (%.1f s)", output_path, len(combined) / 1000
        )
        return True

    except Exception as exc:
        logger.error("Audio assembly failed: %s", exc)
        return False
