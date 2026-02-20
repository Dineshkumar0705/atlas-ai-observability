import re
from typing import List, Dict
from collections import Counter


class HallucinationEngine:
    """
    Deterministic hallucination risk estimator.
    Measures divergence between response and retrieved context.
    """

    STOPWORDS = {
        "the", "is", "are", "a", "an", "to", "of", "and",
        "in", "for", "on", "with", "that", "this", "it",
        "as", "at", "by", "from", "or", "be"
    }

    def _tokenize(self, text: str) -> List[str]:
        tokens = re.findall(r"\b\w+\b", text.lower())
        return [t for t in tokens if t not in self.STOPWORDS]

    def score(
        self,
        context: List[str],
        response: str,
        number_conflict: bool = False
    ) -> Dict:
        """
        Returns:
        {
            hallucination_score: float,
            divergence_score: float,
            unsupported_ratio: float,
            context_absence_penalty: float
        }
        """

        # No context → inherently risky
        if not context:
            return {
                "hallucination_score": 0.7,
                "divergence_score": 0.7,
                "unsupported_ratio": 0.0,
                "context_absence_penalty": 0.7
            }

        full_context = " ".join(context)

        response_tokens = self._tokenize(response)
        context_tokens = self._tokenize(full_context)

        if not response_tokens:
            return {
                "hallucination_score": 0.0,
                "divergence_score": 0.0,
                "unsupported_ratio": 0.0,
                "context_absence_penalty": 0.0
            }

        response_counter = Counter(response_tokens)
        context_counter = Counter(context_tokens)

        # Tokens in response not supported by context
        unsupported_tokens = [
            t for t in response_counter if t not in context_counter
        ]

        unsupported_ratio = len(unsupported_tokens) / len(response_tokens)

        # Divergence score (penalize unsupported claims heavily)
        divergence_score = min(unsupported_ratio * 1.2, 1.0)

        # Context absence penalty (if weak overlap)
        common_tokens = set(response_tokens) & set(context_tokens)
        overlap_ratio = len(common_tokens) / len(response_tokens)

        context_absence_penalty = 1 - overlap_ratio

        # Aggregate risk
        hallucination_score = (
            0.6 * divergence_score +
            0.4 * context_absence_penalty
        )

        # Boost if numeric contradiction detected
        if number_conflict:
            hallucination_score = min(hallucination_score + 0.2, 1.0)

        hallucination_score = round(hallucination_score, 2)

        return {
            "hallucination_score": hallucination_score,
            "divergence_score": round(divergence_score, 2),
            "unsupported_ratio": round(unsupported_ratio, 2),
            "context_absence_penalty": round(context_absence_penalty, 2)
        }