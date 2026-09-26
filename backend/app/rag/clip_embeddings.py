import os
import torch
import logging
import numpy as np
from typing import List, Dict, Any, Union, Optional
from PIL import Image

logger = logging.getLogger("DocuMind.ClipEmbeddings")

_clip_instance = None


class ClipEmbeddingService:
    """
    Multimodal Vision-Language Embedding Engine (CLIP ViT-B/32).
    Generates aligned 512-dimensional joint embeddings for:
      1. Raw document pages & scanned images (charts, tables, invoices, stamps)
      2. Natural language user search queries ("find pages with pie charts", "invoices with stamps")

    Powers Tri-brid RAG (BM25 Keyword + Dense Text Vector + Visual CLIP).
    """

    def __init__(self, model_name: str = "clip-ViT-B-32"):
        self.model_name = model_name
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._model = None
        self._initialized = False

    def _ensure_loaded(self):
        if self._initialized:
            return
        self._initialized = True
        try:
            logger.info(f"[CLIP] 👁 Loading {self.model_name} on {self.device.upper()}...")
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name, device=self.device)
            logger.info(f"[CLIP] ✅ {self.model_name} online on {self.device.upper()} (512-dim visual space)")
        except Exception as e:
            logger.warning(f"[CLIP] ⚠ Failed to load SentenceTransformer CLIP ({e}), trying fallback...")
            self._model = None

    def embed_image(self, image_input: Union[str, Image.Image, np.ndarray]) -> List[float]:
        """
        Embeds a raw image or document page directly into 512-dimensional CLIP space.
        Does not require OCR text extraction.
        """
        self._ensure_loaded()
        if not self._model:
            # Deterministic fallback projection if model unavailable
            return [0.0] * 512

        try:
            pil_img = None
            if isinstance(image_input, str):
                if not os.path.exists(image_input):
                    return [0.0] * 512
                pil_img = Image.open(image_input).convert("RGB")
            elif isinstance(image_input, np.ndarray):
                pil_img = Image.fromarray(image_input).convert("RGB")
            elif isinstance(image_input, Image.Image):
                pil_img = image_input.convert("RGB")

            if pil_img is None:
                return [0.0] * 512

            vec = self._model.encode(pil_img, normalize_embeddings=True)
            return [float(x) for x in vec]
        except Exception as e:
            logger.error(f"[CLIP] ✗ Error embedding image: {e}")
            return [0.0] * 512

    def embed_text(self, text: str) -> List[float]:
        """
        Embeds a user query into the exact same 512-dimensional CLIP space,
        enabling direct cross-modal image-to-text cosine similarity.
        """
        self._ensure_loaded()
        if not self._model or not text.strip():
            return [0.0] * 512

        try:
            vec = self._model.encode(text.strip(), normalize_embeddings=True)
            return [float(x) for x in vec]
        except Exception as e:
            logger.error(f"[CLIP] ✗ Error embedding query text: {e}")
            return [0.0] * 512

    def compute_similarity(self, vec_a: List[float], vec_b: List[float]) -> float:
        """Computes dot product between two normalized 512d CLIP vectors."""
        if not vec_a or not vec_b:
            return 0.0
        va = np.array(vec_a, dtype=np.float32)
        vb = np.array(vec_b, dtype=np.float32)
        if len(va) != 512 or len(vb) != 512:
            return 0.0
        return float(np.dot(va, vb))

    def zero_shot_classify(
        self,
        image_input: Union[str, Image.Image, np.ndarray],
        candidate_labels: List[str]
    ) -> Dict[str, float]:
        """
        Performs zero-shot ViT classification using CLIP joint vision-language alignment.
        Returns a dictionary of label -> confidence probability (summing to 1.0).
        """
        self._ensure_loaded()
        if not self._model:
            return {label: 1.0 / len(candidate_labels) for label in candidate_labels}

        try:
            img_emb = np.array(self.embed_image(image_input), dtype=np.float32)
            if np.all(img_emb == 0):
                return {label: 1.0 / len(candidate_labels) for label in candidate_labels}

            # Embed candidate label prompts
            prompts = [f"a photo or document of {label}" for label in candidate_labels]
            txt_embs = self._model.encode(prompts, normalize_embeddings=True)

            # Cosine similarities scaled for temperature softmax
            similarities = np.dot(txt_embs, img_emb) * 100.0  # CLIP logit scale
            exp_sim = np.exp(similarities - np.max(similarities))
            probs = exp_sim / np.sum(exp_sim)

            return {label: float(prob) for label, prob in zip(candidate_labels, probs)}
        except Exception as e:
            logger.error(f"[CLIP] ✗ Zero-shot classification failed: {e}")
            return {label: 1.0 / len(candidate_labels) for label in candidate_labels}


def get_clip_service() -> ClipEmbeddingService:
    global _clip_instance
    if _clip_instance is None:
        _clip_instance = ClipEmbeddingService()
    return _clip_instance


clip_service = get_clip_service()
