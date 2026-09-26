import time
import numpy as np
import logging
from typing import List, Dict, Any, Optional
from rank_bm25 import BM25Okapi
from app.rag.embeddings import embedding_service
from app.rag.clip_embeddings import clip_service

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
    Tri-brid Multimodal Retriever:
      Lane 1 — Sparse Keyword Search (BM25Okapi)
      Lane 2 — Dense Text Vector Similarity (SentenceTransformer MiniLM)
      Lane 3 — Visual Cross-Modal Semantic Search (CLIP ViT-B/32)
    Merged via 3-Way Reciprocal Rank Fusion (RRF).
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

        # Apply document filter if specified (supports single doc or comma-separated multiple docs)
        if doc_filter:
            import urllib.parse
            unquoted_filter = urllib.parse.unquote(doc_filter)
            filter_terms = [
                t.strip().lower()
                for raw in [doc_filter, unquoted_filter]
                for t in raw.split(",")
                if t.strip()
            ]
            filter_terms = list(dict.fromkeys(filter_terms))

            def _doc_matches(c: Dict[str, Any]) -> bool:
                c_name = c.get("doc_name", "").lower()
                c_id = c.get("doc_id", "").lower()
                c_name_unquoted = urllib.parse.unquote(c_name)
                for term in filter_terms:
                    term_clean = term.strip()
                    if not term_clean:
                        continue
                    if (
                        term_clean == c_name
                        or term_clean == c_id
                        or term_clean == c_name_unquoted
                        or term_clean in c_name
                        or term_clean in c_name_unquoted
                        or c_name in term_clean
                        or c_name_unquoted in term_clean
                    ):
                        return True
                return False

            filtered_chunks = [c for c in chunks if _doc_matches(c)]
            if filtered_chunks:
                logger.info(f"[Retriever] Doc filter '{doc_filter}': {len(filtered_chunks)}/{len(chunks)} chunks selected")
                chunks = filtered_chunks
            else:
                logger.warning(f"[Retriever] Doc filter '{doc_filter}' matched 0 chunks — using full corpus")

        n = len(chunks)
        logger.info(f"[Retriever] Query: '{query[:60]}...' | Corpus: {n} chunks | top_k: {top_k}")

        # ── Lane 1: Sparse BM25 Keyword Scoring ──────────────────────────────
        t1 = time.monotonic()
        corpus_tokenized = [c["content"].lower().split() for c in chunks]
        bm25 = BM25Okapi(corpus_tokenized)
        query_tokens = query.lower().split()
        bm25_scores = bm25.get_scores(query_tokens)
        bm25_ranked_indices = np.argsort(bm25_scores)[::-1]
        t1_elapsed = time.monotonic() - t1

        top_bm25_score = float(bm25_scores[bm25_ranked_indices[0]]) if n > 0 else 0.0
        logger.info(
            f"[Retriever] Lane 1/3 BM25 Sparse — top score: {top_bm25_score:.4f} | "
            f"elapsed: {t1_elapsed*1000:.1f}ms"
        )

        # ── Lane 2: Dense Text Vector Cosine Scoring ─────────────────────────
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
            f"[Retriever] Lane 2/3 Dense Vector — top cosine: {top_dense_score:.4f} | "
            f"elapsed: {t2_elapsed*1000:.1f}ms"
        )

        # ── Lane 3: Multimodal Visual CLIP Scoring ───────────────────────────
        t3_clip = time.monotonic()
        has_clip_chunks = any(bool(c.get("clip_embedding")) for c in chunks)
        clip_scores = [0.0] * n
        clip_ranked_indices = []

        if has_clip_chunks:
            query_clip_emb = clip_service.embed_text(query)
            for idx, c in enumerate(chunks):
                c_emb = c.get("clip_embedding", [])
                if c_emb:
                    clip_scores[idx] = clip_service.compute_similarity(query_clip_emb, c_emb)
                else:
                    clip_scores[idx] = 0.0
            clip_ranked_indices = np.argsort(clip_scores)[::-1]
            top_clip_score = float(clip_scores[clip_ranked_indices[0]])
            t3_clip_elapsed = time.monotonic() - t3_clip
            logger.info(
                f"[Retriever] Lane 3/3 Visual CLIP — top cosine: {top_clip_score:.4f} | "
                f"elapsed: {t3_clip_elapsed*1000:.1f}ms"
            )

        # ── Fusion: 3-Way Reciprocal Rank Fusion (RRF) ───────────────────────
        t_fuse = time.monotonic()
        rrf_scores: Dict[int, float] = {}

        for rank, idx in enumerate(bm25_ranked_indices):
            rrf_scores[idx] = rrf_scores.get(idx, 0.0) + (1.0 / (self.k_rrf + rank + 1))

        for rank, idx in enumerate(dense_ranked_indices):
            rrf_scores[idx] = rrf_scores.get(idx, 0.0) + (1.0 / (self.k_rrf + rank + 1))

        if has_clip_chunks and len(clip_ranked_indices) > 0:
            for rank, idx in enumerate(clip_ranked_indices):
                if clip_scores[idx] > 0.15:  # Only fuse meaningful visual matches
                    rrf_scores[idx] = rrf_scores.get(idx, 0.0) + (1.2 / (self.k_rrf + rank + 1))

        sorted_indices = sorted(rrf_scores.keys(), key=lambda i: rrf_scores[i], reverse=True)
        t_fuse_elapsed = time.monotonic() - t_fuse

        # Build result list
        results = []
        for pos, idx in enumerate(sorted_indices[:top_k]):
            item = dict(chunks[idx])
            raw_dense = max(0.0, min(1.0, dense_scores[idx]))
            raw_clip = max(0.0, min(1.0, clip_scores[idx]))
            has_bm25 = 1 if bm25_scores[idx] > 0 else 0

            # Dynamic multi-lane weighted relevance percentage
            relevance_pct = int(min(99, max(58, (
                raw_dense * 0.45 +
                has_bm25 * 0.25 +
                raw_clip * 0.30 +
                0.25
            ) * 100)))

            item["relevance"] = relevance_pct
            item["dense_score"] = float(dense_scores[idx])
            item["bm25_score"] = float(bm25_scores[idx])
            item["clip_score"] = float(clip_scores[idx])
            item["rrf_score"] = round(rrf_scores[idx], 6)
            results.append(item)

        total_elapsed = time.monotonic() - t_start
        logger.info(
            f"[Retriever] Tri-brid RRF COMPLETE — {len(results)} items retrieved in {total_elapsed*1000:.1f}ms"
        )
        for r in results:
            logger.info(
                f"  [{r.get('relevance', 0)}%] '{r['doc_name']}' p.{r['page_number']} — "
                f"dense={r['dense_score']:.3f} bm25={r['bm25_score']:.3f} "
                f"clip={r.get('clip_score', 0):.3f} rrf={r['rrf_score']:.5f}"
            )

        return results


hybrid_retriever = HybridRetriever()
