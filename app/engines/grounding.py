import re
from typing import List, Dict
from collections import Counter


class GroundingEngine:
    """
    Deterministic grounding evaluator.
    Measures how much response is supported by retrieved context.
    """

    STOPWORDS = {
        "the", "is", "are", "a", "an", "to", "of", "and",
        "in", "for", "on", "with", "that", "this", "it",
        "as", "at", "by", "from", "or", "be"
    }

    def _tokenize(self, text: str) -> List[str]:
        tokens = re.findall(r"\b\w+\b", text.lower())
        return [t for t in tokens if t not in self.STOPWORDS]

    def score(self, context: List[str], response: str) -> Dict:
        """
        Returns:
        {
            grounding_score: float,
            overlap_ratio: float,
            context_coverage: float
        }
        """

        if not context:
            return {
                "grounding_score": 0.0,
                "overlap_ratio": 0.0,
                "context_coverage": 0.0
            }

        # Combine context into single string
        full_context = " ".join(context)

        response_tokens = self._tokenize(response)
        context_tokens = self._tokenize(full_context)

        if not response_tokens or not context_tokens:
            return {
                "grounding_score": 0.0,
                "overlap_ratio": 0.0,
                "context_coverage": 0.0
            }

        response_counter = Counter(response_tokens)
        context_counter = Counter(context_tokens)

        # Token overlap
        common_tokens = set(response_counter.keys()) & set(context_counter.keys())
        overlap_count = sum(min(response_counter[t], context_counter[t]) for t in common_tokens)

        overlap_ratio = overlap_count / len(response_tokens)

        # Context coverage
        coverage_ratio = len(common_tokens) / len(set(context_tokens))

        # Weighted grounding score
        grounding_score = round(
            (0.7 * overlap_ratio + 0.3 * coverage_ratio),
            2
        )

        return {
            "grounding_score": grounding_score,
            "overlap_ratio": round(overlap_ratio, 2),
            "context_coverage": round(coverage_ratio, 2)
        }