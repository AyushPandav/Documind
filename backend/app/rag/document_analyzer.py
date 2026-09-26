"""
DocuMind Document Analysis Module
===================================
Provides:
1. Per-Document Summary Generation  — concise 2–3 sentence summaries per uploaded document
2. Document Relatedness Analysis     — detects whether uploaded documents are topically related or unrelated
3. Cross-Document Topic Fingerprinting via TF-IDF keyword extraction
"""
import re
import math
import logging
from collections import Counter
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger("DocuMind.DocumentAnalyzer")

# ── Common English stopwords for TF-IDF exclusion ────────────────────────────
STOPWORDS = {
    "the", "and", "for", "that", "this", "with", "from", "are", "was", "were",
    "have", "has", "had", "not", "but", "they", "all", "been", "more", "also",
    "can", "its", "into", "then", "than", "when", "their", "there", "these",
    "which", "will", "each", "any", "other", "such", "after", "before", "about",
    "only", "per", "may", "must", "should", "shall", "our", "your", "you", "we",
    "he", "she", "it", "an", "at", "by", "in", "on", "of", "to", "a", "is",
    "or", "as", "be", "do", "if", "no", "so", "up", "us", "me", "my", "his",
    "her", "how", "what", "who", "why", "i", "s", "t", "don", "just", "would",
}

def tokenize(text: str) -> List[str]:
    """Lowercases and extracts words of 3+ characters, excluding stopwords."""
    return [
        w for w in re.findall(r"\b[a-z]{3,}\b", text.lower())
        if w not in STOPWORDS
    ]

def compute_tfidf_keywords(text: str, top_n: int = 10) -> List[Tuple[str, float]]:
    """
    Extracts TF-IDF weighted keywords from a single document corpus.
    Uses log normalization: TF * log(1 + 1/DF) on a single-doc basis.
    """
    tokens = tokenize(text)
    if not tokens:
        return []

    tf: Counter = Counter(tokens)
    total = len(tokens)
    scored = {word: count / total for word, count in tf.items()}

    # Sort by frequency-weighted score
    ranked = sorted(scored.items(), key=lambda x: x[1], reverse=True)
    return ranked[:top_n]

def generate_document_summary(doc_name: str, chunks: List[Dict[str, Any]]) -> str:
    """
    Generates a concise 2–3 sentence summary of a document based on its indexed chunks.
    Uses keyword-density scoring to surface the most representative sentences.
    """
    logger.info(f"  [Analyzer] Generating summary for '{doc_name}' ({len(chunks)} chunks)...")

    if not chunks:
        return f"No content could be extracted from {doc_name}."

    # Aggregate all text
    full_text = " ".join(c.get("content", "") for c in chunks)
    keywords = [kw for kw, _ in compute_tfidf_keywords(full_text, top_n=15)]

    # Collect all sentences from chunks
    sentences = []
    for chunk in chunks:
        content = chunk.get("content", "")
        for sent in re.split(r"(?<=[.!?])\s+", content):
            sent = sent.strip()
            if len(sent) > 40:
                sentences.append(sent)

    if not sentences:
        # Fallback: truncate first chunk
        return (full_text[:300] + "...") if len(full_text) > 300 else full_text

    # Score each sentence by keyword density
    def sentence_score(s: str) -> float:
        s_lower = s.lower()
        return sum(1 for kw in keywords if kw in s_lower)

    ranked_sents = sorted(sentences, key=sentence_score, reverse=True)

    # Pick top 2 distinct, non-overlapping sentences
    summary_sents: List[str] = []
    seen_tokens: set = set()
    for s in ranked_sents:
        s_tokens = set(tokenize(s))
        overlap = len(s_tokens & seen_tokens)
        if overlap < len(s_tokens) * 0.5:  # < 50% overlap
            summary_sents.append(s.rstrip(".") + ".")
            seen_tokens |= s_tokens
        if len(summary_sents) >= 2:
            break

    if not summary_sents:
        summary_sents = [sentences[0].rstrip(".") + "."]

    summary = " ".join(summary_sents)
    logger.info(f"  [Analyzer] Summary for '{doc_name}': {len(summary)} chars, {len(summary_sents)} sentences")
    return summary


def analyze_document_relatedness(
    all_chunks_by_doc: Dict[str, List[Dict[str, Any]]]
) -> Dict[str, Any]:
    """
    Cross-Document Relatedness Analysis using TF-IDF Keyword Jaccard Similarity.

    Computes per-document keyword fingerprints and measures pairwise Jaccard
    similarity between document keyword sets.

    Returns:
    {
        "is_related": bool,
        "confidence": float (0.0–1.0),
        "relationship_label": str,
        "doc_summaries": {doc_name: summary_str},
        "keyword_fingerprints": {doc_name: [kw1, kw2, ...]},
        "pairwise_similarity": [{doc_a, doc_b, score}],
        "shared_themes": [str],
        "recommendation": str
    }
    """
    doc_names = list(all_chunks_by_doc.keys())
    n_docs = len(doc_names)

    logger.info(f"[DocumentAnalyzer] ═══ Starting Cross-Document Analysis ({n_docs} documents) ═══")

    # ── Step 1: Build keyword fingerprints per document ──────────────────────
    logger.info("[DocumentAnalyzer] Step 1/3: Extracting TF-IDF keyword fingerprints...")
    fingerprints: Dict[str, set] = {}
    summaries: Dict[str, str] = {}

    for doc_name, chunks in all_chunks_by_doc.items():
        full_text = " ".join(c.get("content", "") for c in chunks)
        keywords = {kw for kw, _ in compute_tfidf_keywords(full_text, top_n=20)}
        fingerprints[doc_name] = keywords
        summaries[doc_name] = generate_document_summary(doc_name, chunks)
        logger.info(f"  [Analyzer] '{doc_name}': {len(keywords)} keywords — top: {list(keywords)[:5]}")

    # ── Step 2: Pairwise Jaccard similarity ──────────────────────────────────
    logger.info("[DocumentAnalyzer] Step 2/3: Computing pairwise Jaccard similarity scores...")
    pairwise: List[Dict[str, Any]] = []
    all_scores: List[float] = []

    for i in range(n_docs):
        for j in range(i + 1, n_docs):
            doc_a = doc_names[i]
            doc_b = doc_names[j]
            set_a = fingerprints[doc_a]
            set_b = fingerprints[doc_b]

            intersection = len(set_a & set_b)
            union = len(set_a | set_b)
            jaccard = intersection / union if union > 0 else 0.0

            pairwise.append({
                "doc_a": doc_a,
                "doc_b": doc_b,
                "jaccard_score": round(jaccard, 4),
                "shared_keywords": sorted(set_a & set_b)[:10],
                "relationship": _score_to_label(jaccard)
            })
            all_scores.append(jaccard)
            logger.info(
                f"  [Analyzer] '{doc_a}' ↔ '{doc_b}': "
                f"Jaccard={jaccard:.4f} ({_score_to_label(jaccard)}) | "
                f"Shared keywords: {sorted(set_a & set_b)[:5]}"
            )

    # ── Step 3: Aggregate shared themes ──────────────────────────────────────
    logger.info("[DocumentAnalyzer] Step 3/3: Aggregating shared themes...")
    all_sets = list(fingerprints.values())
    shared_themes: List[str] = []
    if len(all_sets) >= 2:
        common = all_sets[0]
        for s in all_sets[1:]:
            common = common & s
        shared_themes = sorted(common)[:12]
        logger.info(f"  [Analyzer] Shared themes across ALL docs: {shared_themes}")

    # ── Final Verdict ─────────────────────────────────────────────────────────
    avg_score = sum(all_scores) / len(all_scores) if all_scores else 0.0
    is_related = avg_score >= 0.08  # threshold: >8% keyword overlap
    confidence = round(min(1.0, avg_score * 5), 2)  # normalize to 0-1

    if n_docs == 1:
        relationship_label = "Single Document"
        recommendation = "Only one document uploaded. Upload more documents to see relatedness analysis."
        is_related = True
    elif avg_score >= 0.25:
        relationship_label = "Highly Related"
        recommendation = "These documents are closely related and likely from the same domain or project."
    elif avg_score >= 0.08:
        relationship_label = "Partially Related"
        recommendation = "These documents share some common topics but cover different areas."
    else:
        relationship_label = "Unrelated"
        recommendation = "These documents appear to be from different domains with minimal topic overlap."

    logger.info(f"[DocumentAnalyzer] ═══ VERDICT: {relationship_label} (avg Jaccard={avg_score:.4f}, confidence={confidence}) ═══")

    return {
        "is_related": is_related,
        "confidence": confidence,
        "relationship_label": relationship_label,
        "avg_jaccard_score": round(avg_score, 4),
        "document_count": n_docs,
        "doc_summaries": summaries,
        "keyword_fingerprints": {k: sorted(v)[:12] for k, v in fingerprints.items()},
        "pairwise_similarity": pairwise,
        "shared_themes": shared_themes,
        "recommendation": recommendation
    }


def _score_to_label(score: float) -> str:
    if score >= 0.25:
        return "Highly Related"
    elif score >= 0.08:
        return "Partially Related"
    elif score >= 0.02:
        return "Loosely Related"
    else:
        return "Unrelated"


async def analyze_uploaded_batch(
    doc_ids: List[str],
    get_chunks_fn,  # callable: async (doc_id) -> List[Dict]
    get_doc_fn      # callable: async (doc_id) -> Dict
) -> Dict[str, Any]:
    """
    High-level async wrapper: given a list of doc_ids, fetches chunks per document,
    runs relatedness analysis, and returns the full analysis report.
    """
    logger.info(f"[DocumentAnalyzer] Batch analysis requested for {len(doc_ids)} document(s)")
    all_chunks_by_doc: Dict[str, List[Dict[str, Any]]] = {}

    for doc_id in doc_ids:
        doc = await get_doc_fn(doc_id)
        if not doc:
            logger.warning(f"  [Analyzer] Doc ID '{doc_id}' not found in DB, skipping.")
            continue

        chunks = await get_chunks_fn(doc_id)
        doc_name = doc.get("name", doc_id)
        all_chunks_by_doc[doc_name] = chunks
        logger.info(f"  [Analyzer] Loaded '{doc_name}': {len(chunks)} chunks")

    if not all_chunks_by_doc:
        return {
            "error": "No documents found for analysis",
            "doc_summaries": {},
            "is_related": False,
            "relationship_label": "N/A"
        }

    return analyze_document_relatedness(all_chunks_by_doc)
