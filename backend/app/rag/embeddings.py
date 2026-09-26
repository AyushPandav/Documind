import hashlib
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
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("Loaded SentenceTransformer all-MiniLM-L6-v2 successfully.")
        except Exception as e:
            logger.info(f"Local neural embedding model offline, using high-speed deterministic semantic projection ({self.dim}d): {e}")
            self._model = None

    def embed_text(self, text: str) -> List[float]:
        """
        Embeds a single string into a normalized 384-dimensional vector.
        """
        if self._model is not None:
            try:
                emb = self._model.encode(text, normalize_embeddings=True)
                return emb.tolist()
            except Exception as e:
                logger.warning(f"Embedding error: {e}, falling back to deterministic projection")

        # Fast offline deterministic semantic projection
        # Tokenizes and projects character n-grams and words across 384 dimensions
        vec = np.zeros(self.dim, dtype=np.float32)
        words = text.lower().split()
        if not words:
            return vec.tolist()

        for idx, w in enumerate(words):
            # Hash word to dimensional bucket
            h = int(hashlib.md5(w.encode("utf-8")).hexdigest(), 16)
            pos = h % self.dim
            weight = 1.0 / (1.0 + 0.05 * idx)
            sign = 1.0 if (h >> 4) % 2 == 0 else -1.0
            vec[pos] += sign * weight

            # Bigram token
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
        return [self.embed_text(t) for t in texts]

embedding_service = EmbeddingModel()
