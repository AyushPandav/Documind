import httpx
import time
import logging
from typing import List, Dict, Any, Optional
from app.config import settings

import re

logger = logging.getLogger("DocuMind.CircuitBreaker")

DOCUMIND_SYSTEM_PROMPT = (
    "You are DocuMind, an intelligent, helpful document assistant. "
    "You talk and respond like a normal, friendly chatbot while remaining grounded and accurate.\n"
    "CRITICAL CONVERSATIONAL RULES:\n"
    "1. Never start responses with repetitive robotic boilerplate such as 'Based on the context evidence provided...', 'Based on the provided documents...', or 'According to the context...'. Jump straight into answering the user's question directly and conversationally.\n"
    "2. For spreadsheets and tabular datasets, directly detail what the data contains: row counts, columns, data types, distributions, and specific records.\n"
    "3. Ground all factual assertions using bracketed citation numbers like [1], [2] referencing the context chunks.\n"
    "4. Format responses cleanly with readable paragraphs, bullet points, or markdown tables when helpful."
)


def clean_robotic_intro(text: str) -> str:
    """
    Strips robotic formulaic opening phrases that LLMs tend to prepend,
    e.g. 'Based on the context evidence provided, the document is...' -> 'The document is...'
    """
    if not text:
        return text
    patterns = [
        r"^(?:Based on the (?:context evidence provided|context provided|provided documents|provided document|context),?\s*)",
        r"^(?:According to the (?:provided documents|provided document|context|evidence),?\s*)",
        r"^(?:From the (?:provided context|provided documents|context),?\s*)"
    ]
    cleaned = text.strip()
    for pat in patterns:
        cleaned = re.sub(pat, "", cleaned, flags=re.IGNORECASE).strip()
    if cleaned and cleaned[0].islower():
        cleaned = cleaned[0].upper() + cleaned[1:]
    return cleaned


async def call_ollama_api(prompt: str, context_chunks: List[Dict[str, Any]]) -> Optional[str]:
    """
    PRIMARY LLM: Local Ollama (Qwen 2.5 3B-Instruct).
    Ultra-low latency, zero external API costs, private on-device generation.
    """
    url = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/chat"
    logger.info(f"[CircuitBreaker] 🔷 Attempting PRIMARY: Ollama ({settings.OLLAMA_MODEL}) at {url}...")
    t_start = time.monotonic()

    try:
        payload = {
            "model": settings.OLLAMA_MODEL,
            "messages": [
                {"role": "system", "content": DOCUMIND_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            "stream": False,
            "options": {
                "temperature": 0.1,
                "top_p": 0.9,
                "num_predict": 1024
            }
        }
        timeout_cfg = httpx.Timeout(60.0, connect=3.0)
        async with httpx.AsyncClient(timeout=timeout_cfg) as client:
            resp = await client.post(url, json=payload)
            elapsed = time.monotonic() - t_start

            if resp.status_code == 200:
                data = resp.json()
                answer = data.get("message", {}).get("content", "").strip()
                if answer:
                    logger.info(f"[CircuitBreaker] ✅ Ollama SUCCESS ({settings.OLLAMA_MODEL}) — {elapsed:.2f}s | chars: {len(answer)}")
                    return answer
            else:
                logger.warning(f"[CircuitBreaker] ✗ Ollama HTTP {resp.status_code} in {elapsed:.2f}s: {resp.text[:180]}")

    except httpx.ConnectError:
        elapsed = time.monotonic() - t_start
        logger.info(f"[CircuitBreaker] ⚠ Ollama not running at {settings.OLLAMA_BASE_URL} ({elapsed:.2f}s) — switching to Fallback-1 (Groq)")
    except httpx.TimeoutException:
        elapsed = time.monotonic() - t_start
        logger.warning(f"[CircuitBreaker] ✗ Ollama TIMEOUT after {elapsed:.2f}s — switching to Fallback-1 (Groq)")
    except Exception as e:
        elapsed = time.monotonic() - t_start
        logger.warning(f"[CircuitBreaker] ✗ Ollama ERROR in {elapsed:.2f}s: {e}")

    return None


async def call_groq_api(prompt: str, context_chunks: List[Dict[str, Any]]) -> Optional[str]:
    """
    FALLBACK-1: High-speed cloud inference via Groq API.
    Activated when local Ollama is offline or times out.
    """
    if not settings.GROQ_API_KEY:
        logger.info("[CircuitBreaker] Groq API key not configured — skipping Groq fallback")
        return None

    logger.info(f"[CircuitBreaker] 🔶 Attempting FALLBACK-1: Groq ({settings.GROQ_MODEL})...")
    t_start = time.monotonic()

    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": settings.GROQ_MODEL,
            "messages": [
                {"role": "system", "content": DOCUMIND_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "max_tokens": 1024
        }
        async with httpx.AsyncClient(timeout=12.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            elapsed = time.monotonic() - t_start

            if resp.status_code == 200:
                data = resp.json()
                answer = data["choices"][0]["message"]["content"].strip()
                usage = data.get("usage", {})
                logger.info(
                    f"[CircuitBreaker] ✅ Groq SUCCESS — "
                    f"{elapsed:.2f}s | "
                    f"tokens: {usage.get('total_tokens', '?')} "
                    f"(prompt={usage.get('prompt_tokens', '?')}, "
                    f"completion={usage.get('completion_tokens', '?')})"
                )
                return answer
            else:
                logger.warning(
                    f"[CircuitBreaker] ✗ Groq HTTP {resp.status_code} in {elapsed:.2f}s: "
                    f"{resp.text[:200]}"
                )

    except httpx.TimeoutException:
        elapsed = time.monotonic() - t_start
        logger.warning(f"[CircuitBreaker] ✗ Groq TIMEOUT after {elapsed:.2f}s — falling back")
    except httpx.ConnectError as e:
        logger.warning(f"[CircuitBreaker] ✗ Groq CONNECTION ERROR: {e} — falling back")
    except Exception as e:
        elapsed = time.monotonic() - t_start
        logger.warning(f"[CircuitBreaker] ✗ Groq ERROR in {elapsed:.2f}s: {e}")

    return None


async def call_mistral_api(prompt: str, context_chunks: List[Dict[str, Any]]) -> Optional[str]:
    """
    FALLBACK-2: Mistral API.
    Activated when both Ollama and Groq are unavailable.
    """
    if not settings.MISTRAL_API_KEY:
        logger.info("[CircuitBreaker] Mistral API key not configured — skipping Mistral fallback")
        return None

    logger.info(f"[CircuitBreaker] 🔷 Attempting FALLBACK-2: Mistral ({settings.MISTRAL_MODEL})...")
    t_start = time.monotonic()

    try:
        url = "https://api.mistral.ai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.MISTRAL_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": settings.MISTRAL_MODEL,
            "messages": [
                {"role": "system", "content": DOCUMIND_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "max_tokens": 1024
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            elapsed = time.monotonic() - t_start

            if resp.status_code == 200:
                data = resp.json()
                answer = data["choices"][0]["message"]["content"].strip()
                usage = data.get("usage", {})
                logger.info(
                    f"[CircuitBreaker] ✅ Mistral SUCCESS — "
                    f"{elapsed:.2f}s | "
                    f"tokens: {usage.get('total_tokens', '?')}"
                )
                return answer
            else:
                logger.warning(
                    f"[CircuitBreaker] ✗ Mistral HTTP {resp.status_code} in {elapsed:.2f}s: "
                    f"{resp.text[:200]}"
                )

    except httpx.TimeoutException:
        elapsed = time.monotonic() - t_start
        logger.warning(f"[CircuitBreaker] ✗ Mistral TIMEOUT after {elapsed:.2f}s — falling back")
    except Exception as e:
        elapsed = time.monotonic() - t_start
        logger.warning(f"[CircuitBreaker] ✗ Mistral ERROR in {elapsed:.2f}s: {e}")

    return None


def offline_heuristic_synthesizer(query: str, chunks: List[Dict[str, Any]]) -> str:
    """
    FALLBACK-3 (Offline): Deterministic Document Synthesis Engine.
    When internet is disconnected and no LLM is reachable, DocuMind still
    synthesizes an accurate, citation-grounded response directly from top chunk sentences.
    """
    logger.info("[CircuitBreaker] 🔴 FALLBACK-3: Offline Heuristic Synthesizer activated (no LLM/internet)")

    if not chunks:
        return "No document text is available yet. Please upload a document to get an analysis and description."

    summary_triggers = ["what is", "about", "describe", "description", "summary", "overview", "explain", "tell me", "compare"]
    is_desc = any(st in query.lower() for st in summary_triggers)

    unique_docs = list(dict.fromkeys(c.get("doc_name", "document") for c in chunks))

    if len(unique_docs) > 1:
        # Multi-document synthesis: pull best representative sentences from each selected document
        doc_bullets = []
        for dname in unique_docs:
            d_chunks = [c for c in chunks if c.get("doc_name") == dname]
            if d_chunks:
                c = d_chunks[0]
                citation_num = chunks.index(c) + 1
                sentences = [s.strip() for s in c["content"].split(".") if len(s.strip()) > 15]
                chosen = sentences[0] if sentences else c["content"][:140]
                clean = chosen.rstrip(". ")
                doc_bullets.append(f"• **{dname}**: {clean} [{citation_num}].")

        result = (
            f"Based on the {len(unique_docs)} selected documents ({', '.join(unique_docs)}), here is a cross-document summary:\n\n"
            + "\n".join(doc_bullets)
        )
        logger.info(f"[CircuitBreaker] ✓ Multi-doc offline synthesis complete: {len(result)} chars from {len(unique_docs)} doc(s)")
        return result

    query_words = set(query.lower().split())
    answer_sentences = []

    for idx, c in enumerate(chunks[:3]):
        citation_num = idx + 1
        sentences = [s.strip() for s in c["content"].split(".") if len(s.strip()) > 15]

        best_sent = None
        best_score = -1
        for s in sentences:
            score = sum(1 for w in query_words if w in s.lower())
            if score > best_score:
                best_score = score
                best_sent = s

        chosen = best_sent if (best_sent and best_score > 0) else (sentences[0] if sentences else c["content"][:140])
        clean_text = chosen.rstrip(". ")
        answer_sentences.append(f"{clean_text} [{citation_num}].")

    if is_desc:
        result = "Based on the uploaded document, here is a description of its key contents:\n\n" + "\n\n".join(answer_sentences)
    else:
        result = " ".join(answer_sentences)

    logger.info(f"[CircuitBreaker] ✓ Offline synthesis complete: {len(result)} chars from {len(chunks[:3])} chunk(s)")
    return result


async def generate_rag_response(prompt: str, context_chunks: List[Dict[str, Any]], raw_query: str) -> Dict[str, Any]:
    """
    Circuit Breaker Dispatcher (4-tier failover):
    1. PRIMARY:    Ollama (Qwen 2.5 3B-Instruct) (local, private, on-device)
    2. FALLBACK-1: Groq API                      (high-speed cloud inference)
    3. FALLBACK-2: Mistral API                   (cloud reasoning LLM)
    4. FALLBACK-3: Offline Semantic Synthesizer  (zero internet requirement)
    """
    logger.info(f"[CircuitBreaker] ▶ Dispatching RAG response (prompt: {len(prompt)} chars)")

    # Tier 1: Local Ollama (Qwen 2.5 3B-Instruct)
    res = await call_ollama_api(prompt, context_chunks)
    if res:
        return {"response": clean_robotic_intro(res), "model": f"Ollama ({settings.OLLAMA_MODEL})"}

    # Tier 2: Groq API
    res = await call_groq_api(prompt, context_chunks)
    if res:
        return {"response": clean_robotic_intro(res), "model": f"Groq ({settings.GROQ_MODEL})"}

    # Tier 3: Mistral API
    res = await call_mistral_api(prompt, context_chunks)
    if res:
        return {"response": clean_robotic_intro(res), "model": f"Mistral ({settings.MISTRAL_MODEL})"}

    # Tier 4: Offline Fallback
    res = offline_heuristic_synthesizer(raw_query, context_chunks)
    return {"response": clean_robotic_intro(res), "model": "Offline Semantic Synthesizer"}
