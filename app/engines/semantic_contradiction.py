import os
import math
import time
from typing import Dict, List, Optional

import google.generativeai as genai
from dotenv import load_dotenv
from sqlalchemy.orm import Session

from app.models.embedding_cache import EmbeddingCache as DBEmbeddingCache

load_dotenv()


class SemanticContradictionEngine:
    """
    Enterprise-grade Gemini semantic grounding engine.

    ✔ Tenant-aware DB cache
    ✔ Lazy Gemini configuration
    ✔ Pure Python cosine similarity
    ✔ Hard timeout protection
    ✔ Fail-safe mode (never crashes ATLAS)
    ✔ Cost optimized
    ✔ Production safe
    """

    DEFAULT_MODEL = "models/embedding-001"
    DEFAULT_TIMEOUT_SECONDS = 8

    def __init__(
        self,
        db: Session,
        tenant_id: Optional[str] = None,
        model: Optional[str] = None,
        high_risk_threshold: float = 0.60,
        medium_risk_threshold: float = 0.75,
    ):
        self.db = db
        self.tenant_id = tenant_id

        self.model = model or os.getenv(
            "GEMINI_EMBED_MODEL",
            self.DEFAULT_MODEL
        )

        self.high_risk_threshold = high_risk_threshold
        self.medium_risk_threshold = medium_risk_threshold

        self.enabled = os.getenv(
            "ENABLE_SEMANTIC_LAYER",
            "true"
        ).lower() == "true"

        self.timeout = int(
            os.getenv("SEMANTIC_TIMEOUT_SECONDS", self.DEFAULT_TIMEOUT_SECONDS)
        )

        self.api_key = os.getenv("GEMINI_API_KEY")
        self._configured = False

    # ==========================================================
    # Gemini Configuration
    # ==========================================================

    def _configure(self) -> None:
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not configured.")

        if not self._configured:
            genai.configure(api_key=self.api_key)
            self._configured = True

    # ==========================================================
    # Cosine Similarity (Pure Python)
    # ==========================================================

    @staticmethod
    def _cosine_similarity(
        vec1: List[float],
        vec2: List[float]
    ) -> float:

        dot = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))

        if norm1 == 0.0 or norm2 == 0.0:
            return 0.0

        return dot / (norm1 * norm2)

    # ==========================================================
    # DB CACHE LOOKUP
    # ==========================================================

    def _get_cached_embedding(self, text: str) -> Optional[List[float]]:
        return DBEmbeddingCache.get_embedding(
            db=self.db,
            text=text,
            tenant_id=self.tenant_id
        )

    def _store_embedding(self, text: str, embedding: List[float]) -> None:
        DBEmbeddingCache.store_embedding(
            db=self.db,
            text=text,
            embedding=embedding,
            tenant_id=self.tenant_id,
            model_used=self.model
        )

    # ==========================================================
    # Embedding Generator
    # ==========================================================

    def _get_embedding(self, text: str) -> List[float]:

        # 1️⃣ Check DB cache
        cached = self._get_cached_embedding(text)
        if cached:
            return cached

        # 2️⃣ Call Gemini
        self._configure()

        response = genai.embed_content(
            model=self.model,
            content=text,
            task_type="retrieval_document"
        )

        embedding = response.get("embedding")

        if not embedding or not isinstance(embedding, list):
            raise ValueError("Invalid embedding response format.")

        # 3️⃣ Persist in DB
        self._store_embedding(text, embedding)

        return embedding

    # ==========================================================
    # Main Evaluation
    # ==========================================================

    def evaluate(
        self,
        context: List[str],
        response: str
    ) -> Dict:

        if not self.enabled:
            return {
                "similarity_score": None,
                "semantic_risk": False,
                "severity": "DISABLED",
                "explanation": "Semantic layer disabled.",
                "model_used": None
            }

        try:
            start_time = time.time()

            # --------------------------------------------
            # No Context Case
            # --------------------------------------------
            if not context:
                return {
                    "similarity_score": 0.0,
                    "semantic_risk": True,
                    "severity": "HIGH",
                    "explanation": "No retrieved context available.",
                    "model_used": self.model
                }

            combined_context = " ".join(context)

            # --------------------------------------------
            # Hard Timeout Guard
            # --------------------------------------------
            if time.time() - start_time > self.timeout:
                raise TimeoutError("Semantic evaluation timeout.")

            # --------------------------------------------
            # Get embeddings (DB cached)
            # --------------------------------------------
            context_embedding = self._get_embedding(combined_context)
            response_embedding = self._get_embedding(response)

            similarity = self._cosine_similarity(
                context_embedding,
                response_embedding
            )

            similarity = round(max(0.0, min(1.0, similarity)), 3)

            semantic_risk = False
            severity = "NONE"
            explanation = None

            # --------------------------------------------
            # Severity Classification
            # --------------------------------------------
            if similarity < self.high_risk_threshold:
                semantic_risk = True
                severity = "HIGH"
                explanation = (
                    f"Low semantic similarity (score={similarity}). "
                    "Response appears ungrounded."
                )

            elif similarity < self.medium_risk_threshold:
                semantic_risk = True
                severity = "MEDIUM"
                explanation = (
                    f"Moderate semantic similarity (score={similarity}). "
                    "Partial grounding detected."
                )

            return {
                "similarity_score": similarity,
                "semantic_risk": semantic_risk,
                "severity": severity,
                "explanation": explanation,
                "model_used": self.model
            }

        except TimeoutError:
            return {
                "similarity_score": None,
                "semantic_risk": False,
                "severity": "TIMEOUT",
                "explanation": "Semantic evaluation timeout.",
                "model_used": self.model
            }

        except Exception as e:
            return {
                "similarity_score": None,
                "semantic_risk": False,
                "severity": "ERROR",
                "explanation": f"Semantic evaluation failed: {str(e)}",
                "model_used": self.model
            }