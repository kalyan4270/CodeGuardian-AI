from __future__ import annotations

import io
import os
import tempfile
from typing import Any

from core.exceptions import TranscriptionError
from core.logging import get_logger

logger = get_logger(__name__)

_whisper_model = None


def _get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        import whisper

        logger.info("Loading Whisper model...")
        _whisper_model = whisper.load_model("base")
        logger.info("Whisper model ready")
    return _whisper_model


def transcribe_audio(audio_bytes: bytes, file_extension: str = "wav") -> dict[str, Any]:
    with tempfile.NamedTemporaryFile(suffix=f".{file_extension}", delete=False) as tmp_file:
        tmp_file.write(audio_bytes)
        tmp_path = tmp_file.name

    try:
        result = _get_whisper_model().transcribe(tmp_path, fp16=False)
        return {
            "text": result["text"].strip(),
            "language": result.get("language", "en"),
            "success": True,
        }
    except Exception as exc:
        return {"text": "", "success": False, "error": str(exc)}
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def process_voice_query(audio_bytes: bytes, file_extension: str = "wav") -> str:
    result = transcribe_audio(audio_bytes, file_extension)
    if result.get("success") and result.get("text"):
        logger.info("Transcribed query (%s): %s", result.get("language"), result["text"])
        return result["text"]
    raise TranscriptionError(result.get("error", "Unknown transcription error"))
