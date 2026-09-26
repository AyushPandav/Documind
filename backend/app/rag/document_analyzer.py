"""
DocuMind Multimodal Cross-Document Intelligence & Relatedness Analyzer
======================================================================
Provides:
1. Multi-Format Ingestion Analysis (PDF, Word, Excel, Images, Text, Presentations).
2. Tri-Brid Cross-Document Correlation:
   - Dense Semantic Vector Cosine Similarity (SentenceTransformer)
   - Visual Multimodal Cosine Similarity (CLIP ViT-B-32)
   - Lexical TF-IDF & Named Entity Jaccard Overlap
3. AI Cross-Document Relationship Synthesis:
   - Detects whether uploaded documents are related, complementary, or independent.
   - Generates an explanation of why and how they correlate.
4. Per-Document Concise Executive Summaries.
"""
import re
import math
import logging
import asyncio
import numpy as np
from collections import Counter
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger("DocuMind.DocumentAnalyzer")

# ── Common English stopwords ──────────────────────────────────────────────────
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


def compute_tfidf_keywords(text: str, top_n: int = 15) -> List[Tuple[str, float]]:
    """Extracts TF-IDF weighted keywords from a single document corpus."""
    tokens = tokenize(text)
    if not tokens:
        return []

    tf: Counter = Counter(tokens)
    total = len(tokens)
    scored = {word: count / total for word, count in tf.items()}
    ranked = sorted(scored.items(), key=lambda x: x[1], reverse=True)
    return ranked[:top_n]


def generate_document_summary(doc_name: str, chunks: List[Dict[str, Any]]) -> str:
    """
    Generates a concise 2–3 sentence executive summary of a document
    based on its indexed chunks using sentence keyword-density ranking.
    """
    if not chunks:
        return f"Document '{doc_name}' has been uploaded and registered."

    full_text = " ".join(c.get("content", "") for c in chunks)
    keywords = [kw for kw, _ in compute_tfidf_keywords(full_text, top_n=20)]

    sentences = []
    for chunk in chunks:
        content = chunk.get("content", "")
        # Clean markdown headers
        cleaned = re.sub(r"#+\s*", "", content)
        for sent in re.split(r"(?<=[.!?])\s+", cleaned):
            sent = sent.strip()
            if len(sent) > 40 and not sent.startswith("[Document Type:"):
                sentences.append(sent)

    if not sentences:
        preview = full_text.strip()[:240]
        return f"{preview}..." if len(preview) >= 240 else preview

    def sentence_score(s: str) -> float:
        s_lower = s.lower()
        return sum(1 for kw in keywords if kw in s_lower)

    ranked_sents = sorted(sentences, key=sentence_score, reverse=True)

    summary_sents: List[str] = []
    seen_tokens: set = set()
    for s in ranked_sents:
        s_tokens = set(tokenize(s))
        overlap = len(s_tokens & seen_tokens)
        if overlap < len(s_tokens) * 0.45:
            summary_sents.append(s.rstrip(".") + ".")
            seen_tokens |= s_tokens
        if len(summary_sents) >= 2:
            break

    if not summary_sents:
        summary_sents = [sentences[0].rstrip(".") + "."]

    return " ".join(summary_sents)


def _compute_cosine(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    """Calculates cosine similarity between two 1D numpy vectors."""
    norm_a = np.linalg.norm(vec_a)
    norm_b = np.linalg.norm(vec_b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(vec_a, vec_b) / (norm_a * norm_b))


async def _generate_ai_relationship_synthesis(
    doc_names: List[str],
    pairwise_info: List[Dict[str, Any]],
    shared_themes: List[str],
    summaries: Dict[str, str],
    is_related: bool,
    avg_score: float
) -> str:
    """
    Generates a human-readable AI explanation of how the documents correlate.
    Attempts local Ollama first; gracefully falls back to deterministic synthesis.
    """
    if len(doc_names) == 1:
        return f"Only '{doc_names[0]}' is loaded. Upload additional documents to analyze cross-document relationships."

    # Try local Ollama Qwen 2.5 3B for ultra-crisp synthesis
    try:
        from app.config import settings
        import httpx

        prompt = (
            f"Analyze the relationship between these {len(doc_names)} documents:\n"
        )
        for name in doc_names[:4]:
            prompt += f"- {name}: {summaries.get(name, '')[:150]}\n"
        prompt += f"Shared themes/keywords: {', '.join(shared_themes[:8])}\n"
        prompt += f"Overall similarity score: {int(avg_score * 100)}%\n\n"
        prompt += (
            "In 2 concise sentences, explain whether these documents are related to each other, "
            "how they connect or complement one another, or why they are independent."
        )

        async with httpx.AsyncClient(timeout=4.0) as client:
            resp = await client.post(
                f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/generate",
                json={
                    "model": settings.OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.2, "num_predict": 90}
                }
            )
            if resp.status_code == 200:
                answer = resp.json().get("response", "").strip()
                if len(answer) > 20:
                    return answer
    except Exception as ollama_err:
        logger.debug(f"[Analyzer] Fast Ollama synthesis bypassed: {ollama_err}")

    # Deterministic high-quality heuristic synthesis
    if is_related:
        theme_str = ", ".join(f"'{t}'" for t in shared_themes[:4]) if shared_themes else "overlapping subject matter"
        if avg_score >= 0.70:
            return (
                f"These documents are highly correlated around {theme_str}. "
                f"They appear to belong to the same project or operational domain, sharing core terminology, structural context, and business rules."
            )
        else:
            return (
                f"These documents exhibit moderate topical overlap regarding {theme_str}. "
                f"While addressing distinct sections or workflows, they reference compatible background concepts and complementary data."
            )
    else:
        return (
            f"These documents appear to be largely independent and originate from distinct contexts. "
            f"They share minimal keyword or semantic overlap (similarity {int(avg_score * 100)}%), covering separated operational or technical domains."
        )


async def analyze_document_relatedness(
    all_chunks_by_doc: Dict[str, List[Dict[str, Any]]]
) -> Dict[str, Any]:
    """
    Multimodal Hybrid Cross-Document Relatedness Analysis:
    Combines:
    1. Dense Semantic Embeddings (Cosine Sim)
    2. Visual Multimodal Vectors (CLIP ViT-B-32)
    3. Lexical TF-IDF Keyword Fingerprints (Jaccard Overlap)
    """
    doc_names = list(all_chunks_by_doc.keys())
    n_docs = len(doc_names)

    logger.info(f"[DocumentAnalyzer] ═══ Starting Multimodal Correlation Analysis ({n_docs} documents) ═══")

    # ── Step 1: Compute Per-Document Representations ──────────────────────────
    fingerprints: Dict[str, set] = {}
    summaries: Dict[str, str] = {}
    dense_vectors: Dict[str, Optional[np.ndarray]] = {}
    clip_vectors: Dict[str, Optional[np.ndarray]] = {}

    for doc_name, chunks in all_chunks_by_doc.items():
        # Text aggregation & TF-IDF
        full_text = " ".join(c.get("content", "") for c in chunks)
        keywords = {kw for kw, _ in compute_tfidf_keywords(full_text, top_n=25)}
        fingerprints[doc_name] = keywords
        summaries[doc_name] = generate_document_summary(doc_name, chunks)

        # Dense text embeddings mean vector
        valid_dense = [c["embedding"] for c in chunks if c.get("embedding") and len(c["embedding"]) > 0]
        if valid_dense:
            dense_vectors[doc_name] = np.mean(valid_dense, axis=0)
        else:
            dense_vectors[doc_name] = None

        # CLIP visual embeddings mean vector
        valid_clip = [c["clip_embedding"] for c in chunks if c.get("clip_embedding") and len(c["clip_embedding"]) > 0]
        if valid_clip:
            clip_vectors[doc_name] = np.mean(valid_clip, axis=0)
        else:
            clip_vectors[doc_name] = None

        logger.info(
            f"  [Analyzer] '{doc_name}': {len(chunks)} chunks | "
            f"DenseVector={'✓' if dense_vectors[doc_name] is not None else '✗'} | "
            f"CLIPVector={'✓' if clip_vectors[doc_name] is not None else '✗'} | "
            f"Keywords: {list(keywords)[:4]}"
        )

    # ── Step 2: Pairwise Multimodal Similarity ────────────────────────────────
    pairwise: List[Dict[str, Any]] = []
    all_composite_scores: List[float] = []

    for i in range(n_docs):
        for j in range(i + 1, n_docs):
            doc_a = doc_names[i]
            doc_b = doc_names[j]

            # 1. Lexical Jaccard Overlap
            set_a = fingerprints[doc_a]
            set_b = fingerprints[doc_b]
            intersection = len(set_a & set_b)
            union = len(set_a | set_b)
            lexical_sim = intersection / union if union > 0 else 0.0

            # 2. Dense Semantic Cosine Similarity
            vec_a = dense_vectors.get(doc_a)
            vec_b = dense_vectors.get(doc_b)
            dense_sim = _compute_cosine(vec_a, vec_b) if (vec_a is not None and vec_b is not None) else lexical_sim

            # Normalize dense cosine [-1, 1] to [0, 1]
            dense_sim_norm = max(0.0, (dense_sim + 1.0) / 2.0) if dense_sim < 0 else dense_sim

            # 3. Visual CLIP Cosine Similarity (if present)
            c_vec_a = clip_vectors.get(doc_a)
            c_vec_b = clip_vectors.get(doc_b)
            clip_sim: Optional[float] = None
            if c_vec_a is not None and c_vec_b is not None:
                raw_clip_sim = _compute_cosine(c_vec_a, c_vec_b)
                clip_sim = max(0.0, min(1.0, (raw_clip_sim + 1.0) / 2.0))

            # 4. Composite Score Formulation
            if clip_sim is not None:
                composite = (0.55 * dense_sim_norm) + (0.30 * lexical_sim) + (0.15 * clip_sim)
            else:
                composite = (0.65 * dense_sim_norm) + (0.35 * lexical_sim)

            composite = max(0.0, min(1.0, composite))
            percentage = int(round(composite * 100))

            # Labeling
            if percentage >= 70:
                rel_label = "Highly Related"
            elif percentage >= 45:
                rel_label = "Moderately Related"
            elif percentage >= 25:
                rel_label = "Loosely Related"
            else:
                rel_label = "Unrelated / Independent"

            pairwise.append({
                "doc_a": doc_a,
                "doc_b": doc_b,
                "composite_score": round(composite, 4),
                "similarity_percentage": percentage,
                "semantic_score": round(dense_sim_norm, 4),
                "lexical_score": round(lexical_sim, 4),
                "visual_score": round(clip_sim, 4) if clip_sim is not None else None,
                "shared_keywords": sorted(set_a & set_b)[:10],
                "relationship": rel_label,
            })
            all_composite_scores.append(composite)

            logger.info(
                f"  [Analyzer] '{doc_a}' ↔ '{doc_b}': {percentage}% ({rel_label}) | "
                f"Dense={dense_sim_norm:.2f}, Lexical={lexical_sim:.2f}, "
                f"CLIP={'N/A' if clip_sim is None else f'{clip_sim:.2f}'}"
            )

    # ── Step 3: Shared Themes Across Documents ────────────────────────────────
    shared_themes: List[str] = []
    if len(fingerprints) >= 2:
        all_sets = list(fingerprints.values())
        common = all_sets[0]
        for s in all_sets[1:]:
            common = common & s
        shared_themes = sorted(common)[:10]

    # If common intersection is empty, pick top most frequent keywords across docs
    if not shared_themes and len(fingerprints) >= 2:
        all_kw_counter: Counter = Counter()
        for kw_set in fingerprints.values():
            all_kw_counter.update(kw_set)
        shared_themes = [k for k, count in all_kw_counter.most_common(8) if count >= 2]

    # ── Final Verdict ─────────────────────────────────────────────────────────
    avg_score = float(np.mean(all_composite_scores)) if all_composite_scores else 0.0
    overall_percentage = int(round(avg_score * 100))
    is_related = overall_percentage >= 45

    if n_docs == 1:
        relationship_label = "Single Document"
        recommendation = "Upload more documents from any format (PDF, DOCX, CSV, Image) to compare relatedness."
        is_related = True
        overall_percentage = 100
    elif overall_percentage >= 70:
        relationship_label = "Highly Related"
        recommendation = "These documents share strong topical alignment. You can query across them seamlessly."
    elif overall_percentage >= 45:
        relationship_label = "Moderately Related"
        recommendation = "These documents share common subjects but cover distinct aspects or policies."
    elif overall_percentage >= 25:
        relationship_label = "Loosely Related"
        recommendation = "These documents share minimal context. Inquiries should be targeted to individual documents."
    else:
        relationship_label = "Unrelated / Independent"
        recommendation = "These documents are from separate domains. Cross-document synthesis may yield unrelated findings."

    # ── Step 4: AI Relationship Narrative Synthesis ──────────────────────────
    explanation = await _generate_ai_relationship_synthesis(
        doc_names=doc_names,
        pairwise_info=pairwise,
        shared_themes=shared_themes,
        summaries=summaries,
        is_related=is_related,
        avg_score=avg_score
    )

    logger.info(
        f"[DocumentAnalyzer] ═══ VERDICT: {relationship_label} ({overall_percentage}%) ═══"
    )

    return {
        "is_related": is_related,
        "similarity_percentage": overall_percentage,
        "relationship_label": relationship_label,
        "relationship_explanation": explanation,
        "document_count": n_docs,
        "shared_themes": shared_themes,
        "doc_summaries": summaries,
        "keyword_fingerprints": {k: sorted(v)[:10] for k, v in fingerprints.items()},
        "pairwise_similarity": pairwise,
        "recommendation": recommendation,
    }


async def analyze_uploaded_batch(
    doc_ids: List[str],
    get_chunks_fn,
    get_doc_fn
) -> Dict[str, Any]:
    """
    High-level async wrapper: fetches chunks and metadata per doc_id,
    and runs the multimodal cross-document analysis.
    """
    logger.info(f"[DocumentAnalyzer] Batch analysis requested for {len(doc_ids)} document(s)")
    all_chunks_by_doc: Dict[str, List[Dict[str, Any]]] = {}

    for doc_id in doc_ids:
        doc = await get_doc_fn(doc_id)
        if not doc:
            continue
        chunks = await get_chunks_fn(doc_id)
        doc_name = doc.get("name", doc_id)
        all_chunks_by_doc[doc_name] = chunks

    if not all_chunks_by_doc:
        return {
            "error": "No documents found for analysis",
            "is_related": False,
            "similarity_percentage": 0,
            "relationship_label": "N/A",
            "relationship_explanation": "No documents available for analysis.",
            "doc_summaries": {},
            "pairwise_similarity": [],
            "shared_themes": []
        }

    return await analyze_document_relatedness(all_chunks_by_doc)
