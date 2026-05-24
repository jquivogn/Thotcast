"""
TTS synthesis layer.

Tries backends in order:
  1. kokoro-onnx  (pip install kokoro-onnx onnxruntime-gpu soundfile)
  2. kokoro       (pip install kokoro soundfile)
  3. None         (audio generation silently skipped)

For kokoro-onnx the model files (kokoro-v0_19.onnx, voices.json) must be present
in the working directory or the path set via KOKORO_MODEL_DIR env var.
"""
import logging
import os

import numpy as np

logger = logging.getLogger(__name__)

_BACKEND: str | None = None
_INSTANCE = None

KOKORO_MODEL_DIR = os.environ.get("KOKORO_MODEL_DIR", ".")
SAMPLE_RATE = 24000

# --- backend detection ---
try:
    from kokoro_onnx import Kokoro as _KokoroOnnx  # type: ignore

    _BACKEND = "kokoro_onnx"
    logger.info("TTS backend: kokoro-onnx")
except ImportError:
    try:
        from kokoro import KPipeline  # type: ignore

        _BACKEND = "kokoro"
        logger.info("TTS backend: kokoro (PyTorch)")
    except ImportError:
        logger.warning(
            "No TTS backend found. Install kokoro-onnx or kokoro. "
            "Audio generation will be skipped."
        )


def _get_instance():
    global _INSTANCE
    if _INSTANCE is not None:
        return _INSTANCE

    if _BACKEND == "kokoro_onnx":
        model_path = os.path.join(KOKORO_MODEL_DIR, "kokoro-v0_19.onnx")
        voices_path = os.path.join(KOKORO_MODEL_DIR, "voices.json")
        _INSTANCE = _KokoroOnnx(model_path, voices_path)
    elif _BACKEND == "kokoro":
        _INSTANCE = KPipeline(lang_code="a")
    return _INSTANCE


def synthesize_line(text: str, voice: str, output_path: str) -> bool:
    if _BACKEND is None:
        return False

    try:
        import soundfile as sf  # type: ignore

        instance = _get_instance()

        if _BACKEND == "kokoro_onnx":
            samples, sr = instance.create(text, voice=voice, speed=1.0, lang="en-us")
            sf.write(output_path, samples, sr)

        elif _BACKEND == "kokoro":
            chunks = [
                audio for _, _, audio in instance(text, voice=voice, speed=1.0)
                if audio is not None
            ]
            if not chunks:
                return False
            audio_data = np.concatenate(chunks)
            sf.write(output_path, audio_data, SAMPLE_RATE)

        return True

    except Exception as exc:
        logger.error("TTS failed for %r: %s", text[:60], exc)
        return False
