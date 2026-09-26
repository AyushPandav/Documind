import re
import io
import time
import base64
import hashlib
import logging
from typing import Tuple, Optional
import numpy as np

logger = logging.getLogger("DocuMind.KokoroTTS")

# In-memory audio cache so repeated voice-over requests are instant
_AUDIO_CACHE = {}


def extract_short_speech_summary(text: str, max_words: int = 45) -> str:
    """
    Cleans markdown, citations, tables, and trims response to a crisp, punchy short voiceover text.
    """
    if not text:
        return ""

    # 1. Remove citations like [1], [2], [1, 2], [DOC: ... | PAGE: ...]
    cleaned = re.sub(r'\[(?:DOC:[^\]]+|\d+(?:[,\s]+\d+)*|cite-[^\]]+)\]', '', text)

    # 2. Remove markdown tables and separator bars
    cleaned = re.sub(r'\|[^\n]+\|', '', cleaned)
    cleaned = re.sub(r'[-=]{3,}', '', cleaned)

    # 3. Remove markdown headers, bold, italics, bullets
    cleaned = re.sub(r'#+\s*', '', cleaned)
    cleaned = re.sub(r'\*{1,3}([^*]+)\*{1,3}', r'\1', cleaned)
    cleaned = re.sub(r'^\s*[-*•]\s*', '', cleaned, flags=re.MULTILINE)

    # 4. Collapse multiple whitespaces and newlines
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()

    # 5. Extract first 2-3 clean sentences up to ~max_words
    sentences = re.split(r'(?<=[.!?])\s+', cleaned)
    selected_sentences = []
    total_words = 0

    for s in sentences:
        s_clean = s.strip()
        if not s_clean:
            continue
        words = s_clean.split()
        if total_words + len(words) <= max_words or not selected_sentences:
            selected_sentences.append(s_clean)
            total_words += len(words)
        else:
            break

    summary = " ".join(selected_sentences).strip()
    return summary if summary else cleaned[:220].strip()


class KokoroTTSEngine:
    """
    Kokoro-82M Text-to-Speech Engine:
    Ultra-lightweight (82M parameter) state-of-the-art TTS model.
    Generates natural, high-fidelity 24kHz voice-over summaries.
    Falls back gracefully to Edge-TTS if needed.
    """
    def __init__(self):
        self._pipeline = None
        self._initialized = False

    def _lazy_init(self):
        if not self._initialized:
            try:
                from kokoro import KPipeline
                logger.info("[KokoroTTS] Loading Kokoro-82M pipeline (lang_code='a')...")
                self._pipeline = KPipeline(lang_code='a', repo_id='hexgrad/Kokoro-82M')
                self._initialized = True
                logger.info("[KokoroTTS] ✅ Kokoro-82M pipeline loaded successfully!")
            except Exception as e:
                logger.warning(f"[KokoroTTS] ⚠ Kokoro-82M init error: {e}. Edge-TTS fallback will be used.")
                self._pipeline = None
                self._initialized = True

    async def _fallback_edge_tts(self, text: str, voice: str = "en-US-JennyNeural") -> bytes:
        """
        Fast, high-fidelity cloud TTS fallback via Edge-TTS (free, zero API key).
        """
        try:
            import edge_tts
            logger.info(f"[KokoroTTS] Generating voice via Edge-TTS fallback: '{voice}'...")
            communicate = edge_tts.Communicate(text, voice)
            audio_buffer = io.BytesIO()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_buffer.write(chunk["data"])
            return audio_buffer.getvalue()
        except Exception as e:
            logger.error(f"[KokoroTTS] Edge-TTS error: {e}")
            return b""

    def synthesize(
        self,
        full_text: str,
        voice: str = "af_heart",
        speed: float = 1.05
    ) -> Tuple[bytes, str, str, float]:
        """
        Synthesizes a short voice-over summary of the input text using Kokoro-82M.
        Returns: (audio_bytes, short_summary_text, model_name, duration_seconds)
        """
        speech_text = extract_short_speech_summary(full_text)
        if not speech_text:
            return b"", "", "none", 0.0

        cache_key = hashlib.md5(f"{speech_text}:{voice}:{speed}".encode()).hexdigest()
        if cache_key in _AUDIO_CACHE:
            logger.info(f"[KokoroTTS] ⚡ Cache HIT for audio voice-over ({len(speech_text)} chars)")
            cached_bytes, cached_model, cached_dur = _AUDIO_CACHE[cache_key]
            return cached_bytes, speech_text, f"{cached_model} (Cached)", cached_dur

        self._lazy_init()

        # ── Primary: Kokoro-82M ───────────────────────────────────────────────
        if self._pipeline is not None:
            try:
                import soundfile as sf
                t_start = time.monotonic()
                logger.info(f"[KokoroTTS] Synthesizing via Kokoro-82M (voice={voice}, speed={speed}): '{speech_text[:60]}...'")

                generator = self._pipeline(speech_text, voice=voice, speed=speed, split_pattern=r'\n+')
                all_audio = []
                for _, _, audio in generator:
                    if audio is not None:
                        # Convert torch tensor or numpy array
                        if hasattr(audio, 'numpy'):
                            audio = audio.numpy()
                        all_audio.append(audio)

                if all_audio:
                    full_audio = np.concatenate(all_audio, axis=0) if len(all_audio) > 1 else all_audio[0]
                    sample_rate = 24000
                    duration_sec = round(len(full_audio) / sample_rate, 2)

                    buffer = io.BytesIO()
                    sf.write(buffer, full_audio, sample_rate, format='WAV')
                    wav_bytes = buffer.getvalue()
                    elapsed = time.monotonic() - t_start

                    logger.info(f"[KokoroTTS] ✅ Kokoro-82M synthesized {duration_sec}s audio in {elapsed:.2f}s ({len(wav_bytes)} bytes)")
                    _AUDIO_CACHE[cache_key] = (wav_bytes, "Kokoro-82M", duration_sec)
                    return wav_bytes, speech_text, "Kokoro-82M", duration_sec

            except Exception as kokoro_err:
                logger.warning(f"[KokoroTTS] Kokoro-82M inference failed: {kokoro_err} — switching to Edge-TTS")

    async def synthesize_async(
        self,
        full_text: str,
        voice: str = "af_heart",
        speed: float = 1.05
    ) -> Tuple[bytes, str, str, float]:
        """
        Asynchronously synthesizes a short voiceover summary.
        Uses Kokoro-82M as primary engine with automatic Edge-TTS fallback.
        """
        import asyncio
        # Run Kokoro synthesis in thread pool to avoid blocking the event loop
        loop = asyncio.get_running_loop()
        wav_bytes, speech_text, model, dur = await loop.run_in_executor(
            None, lambda: self.synthesize(full_text, voice, speed)
        )

        if wav_bytes and len(wav_bytes) > 1000:
            return wav_bytes, speech_text, model, dur

        # If Kokoro produced no bytes, fall back to Edge-TTS
        cache_key = hashlib.md5(f"edge:{speech_text}".encode()).hexdigest()
        if cache_key in _AUDIO_CACHE:
            cached_bytes, cached_model, cached_dur = _AUDIO_CACHE[cache_key]
            return cached_bytes, speech_text, cached_model, cached_dur

        edge_bytes = await self._fallback_edge_tts(speech_text)
        if edge_bytes:
            dur = round(len(speech_text.split()) / 2.8, 1)  # Approx duration
            _AUDIO_CACHE[cache_key] = (edge_bytes, "Edge-TTS (Fallback)", dur)
            return edge_bytes, speech_text, "Edge-TTS", dur

        return b"", speech_text, "Failed", 0.0


kokoro_tts = KokoroTTSEngine()

