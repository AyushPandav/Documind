"""
DocuMind Bilingual Language Service
Handles:
  - Language detection (Hindi vs English)
  - Cross-language query translation for retrieval
  - Language-aware LLM response instructions
"""

import re
import logging
from typing import Optional, Tuple

logger = logging.getLogger("DocuMind.LanguageService")


# ── Hindi Unicode character ranges ───────────────────────────────────────────
# Devanagari script: U+0900–U+097F
# Extended Devanagari: U+A8E0–U+A8FF
DEVANAGARI_PATTERN = re.compile(r'[\u0900-\u097F\uA8E0-\uA8FF]')


def detect_language(text: str) -> str:
    """
    Detects if text is predominantly Hindi (Devanagari) or English.
    Returns: "hi" for Hindi, "en" for English.
    """
    if not text or not text.strip():
        return "en"

    words = text.strip().split()
    if not words:
        return "en"

    devanagari_words = sum(
        1 for w in words if DEVANAGARI_PATTERN.search(w)
    )
    ratio = devanagari_words / len(words)

    lang = "hi" if ratio >= 0.3 else "en"
    logger.info(
        f"[LanguageService] Detected: '{lang}' "
        f"(Devanagari words: {devanagari_words}/{len(words)}, ratio: {ratio:.2f})"
    )
    return lang


def detect_query_and_doc_language(
    query: str,
    doc_name: Optional[str] = None
) -> Tuple[str, str]:
    """
    Returns (query_lang, doc_lang) tuple.
    """
    query_lang = detect_language(query)
    doc_lang = "hi" if doc_name and DEVANAGARI_PATTERN.search(doc_name) else "en"
    return query_lang, doc_lang


def get_language_label(lang_code: str) -> str:
    """Returns human-readable language label."""
    return "Hindi (हिंदी)" if lang_code == "hi" else "English"


def get_response_language_instruction(query_lang: str) -> str:
    """
    Returns an LLM instruction string telling it what language to respond in.
    """
    if query_lang == "hi":
        return (
            "LANGUAGE INSTRUCTION: The user's query is in Hindi. "
            "You MUST respond in Hindi (Devanagari script). "
            "Use clear, conversational Hindi. "
            "If evidence from documents is in English, translate the key facts into Hindi in your answer. "
            "Maintain bracketed citation numbers like [1], [2] regardless of language."
        )
    else:
        return (
            "LANGUAGE INSTRUCTION: The user's query is in English. "
            "Respond in English. "
            "If evidence from documents is in Hindi, translate the key facts into English in your answer. "
            "Maintain bracketed citation numbers like [1], [2]."
        )


def translate_query_for_retrieval(query: str, query_lang: str) -> str:
    """
    For BM25 keyword matching across languages, adds both the original query
    terms and transliterated/translated keywords when mixing languages.

    For now we use a simple keyword expansion approach since we cannot call
    a translation API without internet dependency. The multilingual embedding
    model handles cross-language semantic matching automatically.
    """
    # The multilingual sentence-transformer handles cross-language similarity natively.
    # BM25 is enhanced by adding Devanagari ↔ Latin transliterations for common terms.

    HINDI_TO_ENGLISH_KEYWORDS = {
        "क्या": "what",
        "कब": "when",
        "कहाँ": "where",
        "कैसे": "how",
        "कौन": "who",
        "क्यों": "why",
        "दस्तावेज़": "document",
        "फ़ाइल": "file",
        "पृष्ठ": "page",
        "सारांश": "summary",
        "रिपोर्ट": "report",
        "नीति": "policy",
        "राजस्व": "revenue",
        "कीमत": "price",
        "मूल्य": "value",
        "डेटा": "data",
        "तालिका": "table",
        "परिणाम": "result",
        "नाम": "name",
        "सूची": "list",
    }

    ENGLISH_TO_HINDI_KEYWORDS = {v: k for k, v in HINDI_TO_ENGLISH_KEYWORDS.items()}

    words = query.split()
    expansion_terms = []

    if query_lang == "hi":
        for w in words:
            clean_w = re.sub(r'[^\w\u0900-\u097F]', '', w.lower())
            if clean_w in HINDI_TO_ENGLISH_KEYWORDS:
                expansion_terms.append(HINDI_TO_ENGLISH_KEYWORDS[clean_w])
    else:
        for w in words:
            clean_w = re.sub(r'[^\w]', '', w.lower())
            if clean_w in ENGLISH_TO_HINDI_KEYWORDS:
                expansion_terms.append(ENGLISH_TO_HINDI_KEYWORDS[clean_w])

    if expansion_terms:
        augmented = f"{query} {' '.join(expansion_terms)}"
        logger.info(
            f"[LanguageService] Query augmented with {len(expansion_terms)} cross-language keywords: "
            f"'{query}' → '{augmented[:80]}'"
        )
        return augmented

    return query


language_service = None  # Imported directly by modules that need it
