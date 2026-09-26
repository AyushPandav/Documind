import time
import numpy as np
import logging
from typing import List, Dict, Any, Optional
from rank_bm25 import BM25Okapi
from app.rag.embeddings import embedding_service

logger = logging.getLogger("DocuMind.Retriever")


def compute_cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    v1 = np.array(vec1, dtype=np.float32)
    v2 = np.array(vec2, dtype=np.float32)
    dot = np.dot(v1, v2)
    norm1 = np.linalg.norm(v1)
    norm2 = np.linalg.norm(v2)
    if norm1 < 1e-6 or norm2 < 1e-6:
        return 0.0
    return float(dot / (norm1 * norm2))


class HybridRetriever:
    """
    Hybrid Sparse (BM25) + Dense (Vector Cosine Similarity) Retriever
    with Reciprocal Rank Fusion (RRF).

    Logs each retrieval stage:
      Step 1 — BM25 sparse keyword scoring
      Step 2 — Dense cosine similarity scoring
      Step 3 — Reciprocal Rank Fusion (RRF) score merging
    """
    def __init__(self, k_rrf: int = 60):
        self.k_rrf = k_rrf

    def retrieve(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        top_k: int = 4,
        doc_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        t_start = time.monotonic()

        if not chunks:
            logger.warning("[Retriever] No chunks available for retrieval — corpus is empty")
            return []

        # Apply document filter if specified
        if doc_filter:
            filtered_chunks = [
                c for c in chunks
                if c.get("doc_name") == doc_filter or c.get("doc_id") == doc_filter
            ]
            if filtered_chunks:
                logger.info(f"[Retriever] Doc filter '{doc_filter}': {len(filtered_chunks)}/{len(chunks)} chunks selected")
                chunks = filtered_chunks
            else:
                logger.warning(f"[Retriever] Doc filter '{doc_filter}' matched 0 chunks — using full corpus")

        n = len(chunks)
        logger.info(f"[Retriever] Query: '{query[:60]}...' | Corpus: {n} chunks | top_k: {top_k}")

        # ── Step 1: Sparse BM25 Keyword Scoring ──────────────────────────────
        t1 = time.monotonic()
        corpus_tokenized = [c["content"].lower().split() for c in chunks]
        bm25 = BM25Okapi(corpus_tokenized)
        query_tokens = query.lower().split()
        bm25_scores = bm25.get_scores(query_tokens)
        bm25_ranked_indices = np.argsort(bm25_scores)[::-1]
        t1_elapsed = time.monotonic() - t1

        top_bm25_score = float(bm25_scores[bm25_ranked_indices[0]]) if n > 0 else 0.0
        logger.info(
            f"[Retriever] Step 1/3 BM25 Sparse — top score: {top_bm25_score:.4f} | "
            f"elapsed: {t1_elapsed*1000:.1f}ms"
        )

        # ── Step 2: Dense Vector Cosine Scoring ──────────────────────────────
        t2 = time.monotonic()
        query_embedding = embedding_service.embed_text(query)
        dense_scores = []
        for c in chunks:
            emb = c.get("embedding", [])
            if not emb:
                emb = embedding_service.embed_text(c["content"])
            sim = compute_cosine_similarity(query_embedding, emb)
            dense_scores.append(sim)
        dense_ranked_indices = np.argsort(dense_scores)[::-1]
        t2_elapsed = time.monotonic() - t2

        top_dense_score = float(dense_scores[dense_ranked_indices[0]]) if n > 0 else 0.0
        logger.info(
            f"[Retriever] Step 2/3 Dense Vector — top cosine: {top_dense_score:.4f} | "
            f"elapsed: {t2_elapsed*1000:.1f}ms"
        )

        # ── Step 3: Reciprocal Rank Fusion (RRF) ─────────────────────────────
        t3 = time.monotonic()
        rrf_scores: Dict[int, float] = {}
        for rank, idx in enumerate(bm25_ranked_indices):
            rrf_scores[idx] = rrf_scores.get(idx, 0.0) + (1.0 / (self.k_rrf + rank + 1))
        for rank, idx in enumerate(dense_ranked_indices):
            rrf_scores[idx] = rrf_scores.get(idx, 0.0) + (1.0 / (self.k_rrf + rank + 1))

        sorted_indices = sorted(rrf_scores.keys(), key=lambda i: rrf_scores[i], reverse=True)
        t3_elapsed = time.monotonic() - t3

        # Build result list
        results = []
        for pos, idx in enumerate(sorted_indices[:top_k]):
            item = dict(chunks[idx])
            raw_dense = max(0.0, min(1.0, dense_scores[idx]))
            relevance_pct = int(min(98, max(55, (raw_dense * 0.7 + (bm25_scores[idx] > 0) * 0.25 + 0.3) * 100)))
            item["relevance"] = relevance_pct
            item["dense_score"] = float(dense_scores[idx])
            item["bm25_score"] = float(bm25_scores[idx])
            item["rrf_score"] = round(rrf_scores[idx], 6)
            results.append(item)

        total_elapsed = time.monotonic() - t_start
        logger.info(
            f"[Retriever] Step 3/3 RRF Fusion — {len(results)} results returned | "
            f"elapsed: {t3_elapsed*1000:.1f}ms | total: {total_elapsed*1000:.1f}ms"
        )
        for r in results:
            logger.info(
                f"  [{r.get('relevance', 0)}%] '{r['doc_name']}' p.{r['page_number']} — "
                f"dense={r['dense_score']:.4f} bm25={r['bm25_score']:.4f} "
                f"rrf={r['rrf_score']:.6f}"
            )

        return results


hybrid_retriever = HybridRetriever()
