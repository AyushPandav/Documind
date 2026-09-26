import base64
import logging
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import JSONResponse
from app.tts.kokoro_service import kokoro_tts

router = APIRouter(prefix="/api/tts", tags=["Text-to-Speech"])
logger = logging.getLogger("DocuMind.TTSRouter")


class VoiceoverRequest(BaseModel):
    text: str
    voice: Optional[str] = "af_heart"
    speed: Optional[float] = 1.05


@router.post("/voiceover")
async def generate_voiceover_summary(req: VoiceoverRequest):
    """
    Generates a natural, short spoken voiceover summary using Kokoro-82M.
    Returns Base64 audio URI + short summary transcript for direct playback.
    """
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty.")

    audio_bytes, short_summary, model, dur = await kokoro_tts.synthesize_async(
        full_text=req.text,
        voice=req.voice or "af_heart",
        speed=req.speed or 1.05
    )

    if not audio_bytes:
        raise HTTPException(status_code=500, detail="Voice synthesis failed.")

    # Determine audio format (WAV for Kokoro, MP3 for Edge-TTS)
    is_wav = audio_bytes[:4] == b"RIFF"
    mime_type = "audio/wav" if is_wav else "audio/mpeg"
    b64_audio = f"data:{mime_type};base64,{base64.b64encode(audio_bytes).decode('utf-8')}"

    return {
        "status": "success",
        "model": model,
        "short_summary": short_summary,
        "duration_seconds": dur,
        "audio_base64": b64_audio,
        "mime_type": mime_type
    }


@router.post("/stream")
async def stream_voiceover(req: VoiceoverRequest):
    """
    Streams raw audio bytes directly (audio/wav or audio/mpeg) for direct HTML5/Expo Audio playback.
    """
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty.")

    audio_bytes, short_summary, model, dur = await kokoro_tts.synthesize_async(
        full_text=req.text,
        voice=req.voice or "af_heart",
        speed=req.speed or 1.05
    )

    if not audio_bytes:
        raise HTTPException(status_code=500, detail="Voice synthesis failed.")

    is_wav = audio_bytes[:4] == b"RIFF"
    media_type = "audio/wav" if is_wav else "audio/mpeg"

    return Response(
        content=audio_bytes,
        media_type=media_type,
        headers={
            "X-TTS-Model": model,
            "X-TTS-Duration": str(dur),
            "Content-Disposition": "inline; filename=voiceover.wav"
        }
    )


@router.get("/speak")
async def speak_text_get(text: str, voice: Optional[str] = "af_heart", speed: Optional[float] = 1.05):
    """
    Direct GET streaming endpoint for Kokoro-82M audio.
    Enables direct streaming playback in browsers, Expo Audio, and mobile media players.
    """
    if not text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty.")

    audio_bytes, short_summary, model, dur = await kokoro_tts.synthesize_async(
        full_text=text,
        voice=voice or "af_heart",
        speed=speed or 1.05
    )

    if not audio_bytes:
        raise HTTPException(status_code=500, detail="Voice synthesis failed.")

    is_wav = audio_bytes[:4] == b"RIFF"
    media_type = "audio/wav" if is_wav else "audio/mpeg"

    return Response(
        content=audio_bytes,
        media_type=media_type,
        headers={
            "X-TTS-Model": model,
            "X-TTS-Duration": str(dur),
            "Content-Disposition": "inline; filename=voiceover.wav"
        }
    )

