import httpx
import logging
from typing import List, Dict, Any, Optional
from app.config import settings

logger = logging.getLogger("DocuMind.CircuitBreaker")

DOCUMIND_SYSTEM_PROMPT = (
    "You are DocuMind, an elite AI Document Intelligence Engine. "
    "Answer strictly using the provided context chunks. "
    "Cite your sources using bracketed notation like [1], [2] referencing the numbered context items. "
    "If the context does not contain sufficient facts to answer the question, state: "
    "'The uploaded documents do not contain sufficient evidence to answer this.'"
)

async def call_mistral_api(prompt: str, context_chunks: List[Dict[str, Any]]) -> Optional[str]:
    """
    PRIMARY LLM: Mistral Large via Mistral API.
    Used as the main inference engine for all DocuMind RAG responses.
    """
    if not settings.MISTRAL_API_KEY:
        logger.info("Mistral API key not configured, skipping primary LLM.")
        return None
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
            if resp.status_code == 200:
                data = resp.json()
                return data["choices"][0]["message"]["content"].strip()
            else:
                logger.warning(f"Mistral API returned status {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        logger.warning(f"Mistral API call failed: {e}")
    return None

async def call_groq_api(prompt: str, context_chunks: List[Dict[str, Any]]) -> Optional[str]:
    """
    FALLBACK LLM: High-speed Cloud Inference via Groq API.
    Activated only when Mistral API is unavailable or times out.
    """
    if not settings.GROQ_API_KEY:
        return None
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
            "max_tokens": 800
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.warning(f"Groq API fallback failed: {e}")
    return None

def offline_heuristic_synthesizer(query: str, chunks: List[Dict[str, Any]]) -> str:
    """
    Final Fallback: Deterministic Document Synthesis Engine.
    When internet is disconnected and no cloud LLM is reachable, DocuMind still
    synthesizes an accurate, citation-grounded response directly from top chunk sentences.
    """
    if not chunks:
        return "I couldn't find enough information in the uploaded documents to answer this."

    # Extract most relevant sentences from top chunks
    query_words = set(query.lower().split())
    answer_sentences = []
    
    for idx, c in enumerate(chunks[:2]):
        citation_num = idx + 1
        sentences = [s.strip() for s in c["content"].split(".") if len(s.strip()) > 15]
        
        # Rank sentence by query overlap
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

    return " ".join(answer_sentences)

async def generate_rag_response(prompt: str, context_chunks: List[Dict[str, Any]], raw_query: str) -> Dict[str, Any]:
    """
    Circuit Breaker Dispatcher:
    1. PRIMARY:  Mistral Large API
    2. FALLBACK: Groq API
    3. OFFLINE:  Deterministic Heuristic Synthesizer
    """
    # 1. Primary: Mistral Large
    res = await call_mistral_api(prompt, context_chunks)
    if res:
        return {"response": res, "model": f"Mistral ({settings.MISTRAL_MODEL})"}

    # 2. Fallback: Groq
    res = await call_groq_api(prompt, context_chunks)
    if res:
        return {"response": res, "model": f"Groq ({settings.GROQ_MODEL})"}

    # 3. Offline Fallback
    res = offline_heuristic_synthesizer(raw_query, context_chunks)
    return {"response": res, "model": "Offline Semantic Synthesizer"}
