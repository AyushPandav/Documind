import hashlib
import time
import numpy as np
import logging
from typing import List
from app.config import settings

logger = logging.getLogger("DocuMind.Embeddings")

class EmbeddingModel:
    def __init__(self, dim: int = settings.EMBEDDING_DIM):
        self.dim = dim
        self._model = None
        self._load_model()

    def _load_model(self):
        logger.info("[Embeddings] Loading local embedding model...")
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("[Embeddings] ✓ SentenceTransformer 'all-MiniLM-L6-v2' loaded successfully (384d neural embeddings)")
        except Exception as e:
            logger.warning(
                f"[Embeddings] SentenceTransformer unavailable: {e}\n"
                f"[Embeddings] ⚡ Falling back to deterministic semantic hash projection ({self.dim}d)"
            )
            self._model = None

    def embed_text(self, text: str) -> List[float]:
        """
        Embeds a single string into a normalized 384-dimensional vector.
        Uses SentenceTransformer if available, else deterministic hash projection.
        """
        if self._model is not None:
            try:
                emb = self._model.encode(text, normalize_embeddings=True)
                return emb.tolist()
            except Exception as e:
                logger.warning(f"[Embeddings] SentenceTransformer encode error: {e}, falling back to projection")

        # Deterministic offline semantic projection via word + bigram hashing
        vec = np.zeros(self.dim, dtype=np.float32)
        words = text.lower().split()
        if not words:
            return vec.tolist()

        for idx, w in enumerate(words):
            h = int(hashlib.md5(w.encode("utf-8")).hexdigest(), 16)
            pos = h % self.dim
            weight = 1.0 / (1.0 + 0.05 * idx)
            sign = 1.0 if (h >> 4) % 2 == 0 else -1.0
            vec[pos] += sign * weight

            if idx > 0:
                bigram = f"{words[idx-1]}_{w}"
                h_bi = int(hashlib.sha256(bigram.encode("utf-8")).hexdigest(), 16)
                pos_bi = h_bi % self.dim
                vec[pos_bi] += (1.0 if (h_bi >> 4) % 2 == 0 else -1.0) * (weight * 1.2)

        norm = np.linalg.norm(vec)
        if norm > 1e-6:
            vec = vec / norm
        return vec.tolist()

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Batch embeds a list of texts with timing log.
        """
        t_start = time.monotonic()
        results = [self.embed_text(t) for t in texts]
        elapsed = time.monotonic() - t_start
        model_type = "SentenceTransformer" if self._model else "Deterministic Projection"
        logger.info(
            f"[Embeddings] Batch embedded {len(texts)} texts in {elapsed:.3f}s "
            f"via {model_type} ({self.dim}d)"
        )
        return results

embedding_service = EmbeddingModel()
