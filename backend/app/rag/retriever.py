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
        if not chunks:
            return []

        # Filter by document if specified
        if doc_filter:
            filtered_chunks = [c for c in chunks if c.get("doc_name") == doc_filter or c.get("doc_id") == doc_filter]
            if filtered_chunks:
                chunks = filtered_chunks

        if not chunks:
            return []

        # 1. Sparse BM25 Keyword Scoring
        corpus_tokenized = [c["content"].lower().split() for c in chunks]
        bm25 = BM25Okapi(corpus_tokenized)
        query_tokens = query.lower().split()
        bm25_scores = bm25.get_scores(query_tokens)
        bm25_ranked_indices = np.argsort(bm25_scores)[::-1]

        # 2. Dense Vector Scoring
        query_embedding = embedding_service.embed_text(query)
        dense_scores = []
        for c in chunks:
            emb = c.get("embedding", [])
            if not emb:
                emb = embedding_service.embed_text(c["content"])
            sim = compute_cosine_similarity(query_embedding, emb)
            dense_scores.append(sim)

        dense_ranked_indices = np.argsort(dense_scores)[::-1]

        # 3. Reciprocal Rank Fusion (RRF)
        rrf_scores: Dict[int, float] = {}

        for rank, idx in enumerate(bm25_ranked_indices):
            rrf_scores[idx] = rrf_scores.get(idx, 0.0) + (1.0 / (self.k_rrf + rank + 1))

        for rank, idx in enumerate(dense_ranked_indices):
            rrf_scores[idx] = rrf_scores.get(idx, 0.0) + (1.0 / (self.k_rrf + rank + 1))

        # Sort chunks by fused RRF score
        sorted_indices = sorted(rrf_scores.keys(), key=lambda i: rrf_scores[i], reverse=True)

        results = []
        for idx in sorted_indices[:top_k]:
            item = dict(chunks[idx])
            # Normalize relevance to 0-100%
            raw_dense = max(0.0, min(1.0, dense_scores[idx]))
            relevance_pct = int(min(98, max(55, (raw_dense * 0.7 + (bm25_scores[idx] > 0) * 0.25 + 0.3) * 100)))
            item["relevance"] = relevance_pct
            item["dense_score"] = float(dense_scores[idx])
            item["bm25_score"] = float(bm25_scores[idx])
            results.append(item)

        return results

hybrid_retriever = HybridRetriever()
