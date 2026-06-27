import whisper
import tempfile
import os

# Load Whisper model once at startup
# base = good balance of speed and accuracy, free, runs locally
print("Loading Whisper model...")
whisper_model = whisper.load_model("base")
print("✅ Whisper model loaded")

def transcribe_audio(audio_bytes: bytes, 
                     file_extension: str = "wav") -> dict:
    """
    Converts voice audio to text using OpenAI Whisper.
    Runs completely locally — no API key needed.

    Supports: wav, mp3, m4a, webm, mp4, ogg
    Returns: dict with transcribed text and language detected
    """
    # Save audio bytes to temp file
    # Whisper needs a file path, not raw bytes
    with tempfile.NamedTemporaryFile(
        suffix=f".{file_extension}",
        delete=False
    ) as tmp_file:
        tmp_file.write(audio_bytes)
        tmp_path = tmp_file.name

    try:
        # Transcribe using Whisper
        result = whisper_model.transcribe(
            tmp_path,
            fp16=False  # fp16=False for CPU, True for GPU
        )
        return {
            "text":     result["text"].strip(),
            "language": result.get("language", "en"),
            "success":  True
        }
    except Exception as e:
        return {
            "text":    "",
            "success": False,
            "error":   str(e)
        }
    finally:
        # Always clean up temp file
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

def process_voice_query(audio_bytes: bytes,
                        file_extension: str = "wav") -> str:
    """
    Main function called by the API endpoint.
    Returns just the transcribed text string.
    """
    result = transcribe_audio(audio_bytes, file_extension)

    if result["success"] and result["text"]:
        print(f"Transcribed: {result['text']}")
        print(f"Language detected: {result['language']}")
        return result["text"]
    else:
        raise Exception(
            f"Transcription failed: {result.get('error', 'Unknown error')}"
        )