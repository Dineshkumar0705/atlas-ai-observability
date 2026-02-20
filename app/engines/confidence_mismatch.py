from typing import Dict, List


class ConfidenceMismatchEngine:
    """
    Detects when LLM response tone expresses strong certainty
    despite weak grounding evidence.
    Deterministic rule-based implementation.
    """

    # High-confidence phrases
    HIGH_CONFIDENCE_PHRASES = [
        "absolutely",
        "definitely",
        "guaranteed",
        "100%",
        "certainly",
        "without a doubt",
        "no doubt",
        "always",
        "never",
        "completely",
        "fully assured"
    ]

    # Moderate confidence phrases
    MEDIUM_CONFIDENCE_PHRASES = [
        "clearly",
        "obviously",
        "undoubtedly",
        "surely",
        "confident",
        "will happen",
        "must be"
    ]

    # Hedging / uncertainty phrases
    UNCERTAINTY_PHRASES = [
        "may",
        "might",
        "could",
        "possibly",
        "likely",
        "suggests",
        "approximately",
        "around",
        "estimated"
    ]

    def _count_matches(self, phrases: List[str], text: str) -> int:
        return sum(1 for phrase in phrases if phrase in text)

    def evaluate(self, response: str, grounding_score: float) -> Dict:
        """
        Returns:
        {
            confidence_score: float (0-1),
            mismatch: bool,
            severity: str,
            explanation: str
        }
        """

        text = response.lower()

        high_count = self._count_matches(self.HIGH_CONFIDENCE_PHRASES, text)
        medium_count = self._count_matches(self.MEDIUM_CONFIDENCE_PHRASES, text)
        uncertainty_count = self._count_matches(self.UNCERTAINTY_PHRASES, text)

        # Confidence intensity calculation
        confidence_score = min(
            (high_count * 0.4) + (medium_count * 0.2) - (uncertainty_count * 0.2),
            1.0
        )

        confidence_score = max(confidence_score, 0.0)

        mismatch = False
        severity = "NONE"
        explanation = None

        # Rule: Strong tone + weak grounding
        if grounding_score < 0.5 and confidence_score > 0.5:
            mismatch = True
            severity = "HIGH"
            explanation = (
                f"Strong confidence tone detected (score={confidence_score}) "
                f"despite weak grounding (score={grounding_score})."
            )

        elif grounding_score < 0.6 and confidence_score > 0.3:
            mismatch = True
            severity = "MEDIUM"
            explanation = (
                f"Moderate confidence tone with limited grounding."
            )

        return {
            "confidence_score": round(confidence_score, 2),
            "mismatch": mismatch,
            "severity": severity,
            "explanation": explanation
        }