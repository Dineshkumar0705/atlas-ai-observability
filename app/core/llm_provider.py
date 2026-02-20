import os
import math
from typing import List, Optional

# Optional imports
try:
    import google.generativeai as genai
except Exception:
    genai = None

try:
    from openai import OpenAI
except Exception:
    OpenAI = None


class BaseEmbeddingProvider:
    def embed(self, texts: List[str]) -> List[List[float]]:
        raise NotImplementedError


# ==========================================================
# 🔵 Gemini Provider
# ==========================================================

class GeminiEmbeddingProvider(BaseEmbeddingProvider):

    DEFAULT_MODEL = "models/embedding-001"

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.model = os.getenv("GEMINI_EMBED_MODEL", self.DEFAULT_MODEL)

        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not configured.")

        if genai is None:
            raise ImportError("google-generativeai not installed.")

        genai.configure(api_key=self.api_key)

    def embed(self, texts: List[str]) -> List[List[float]]:
        embeddings = []

        for text in texts:
            response = genai.embed_content(
                model=self.model,
                content=text,
                task_type="retrieval_document"
            )
            embeddings.append(response["embedding"])

        return embeddings


# ==========================================================
# 🟢 OpenAI Provider
# ==========================================================

class OpenAIEmbeddingProvider(BaseEmbeddingProvider):

    DEFAULT_MODEL = "text-embedding-3-small"

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("OPENAI_EMBED_MODEL", self.DEFAULT_MODEL)

        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not configured.")

        if OpenAI is None:
            raise ImportError("openai not installed.")

        self.client = OpenAI(api_key=self.api_key)

    def embed(self, texts: List[str]) -> List[List[float]]:
        response = self.client.embeddings.create(
            model=self.model,
            input=texts
        )

        return [item.embedding for item in response.data]


# ==========================================================
# 🧠 Provider Factory
# ==========================================================

def get_embedding_provider() -> BaseEmbeddingProvider:
    provider = os.getenv("EMBEDDING_PROVIDER", "gemini").lower()

    if provider == "gemini":
        return GeminiEmbeddingProvider()

    elif provider == "openai":
        return OpenAIEmbeddingProvider()

    else:
        raise ValueError(f"Unsupported EMBEDDING_PROVIDER: {provider}")