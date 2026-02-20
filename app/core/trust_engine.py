from dataclasses import dataclass
from typing import Dict, Optional


# =====================================================
# CONFIGURABLE TRUST WEIGHTS
# =====================================================

@dataclass
class TrustWeights:
    """
    Configurable weight configuration for trust computation.
    Allows dynamic tuning without modifying engine logic.
    """

    base_score: float = 100.0

    hallucination_weight: float = 50.0
    grounding_weight: float = 30.0

    high_risk_penalty: float = 15.0
    medium_risk_penalty: float = 8.0
    critical_risk_penalty: float = 25.0

    number_conflict_penalty: float = 15.0
    confidence_mismatch_penalty: float = 12.0
    semantic_risk_penalty: float = 15.0


# =====================================================
# TRUST ENGINE
# =====================================================

class TrustEngine:
    """
    Deterministic Trust Aggregation Engine.

    Aggregates:
    - Hallucination probability
    - Grounding strength
    - Business risk
    - Numeric contradictions
    - Tone confidence mismatch
    - Semantic contradiction risk

    Produces:
    - Final trust score (0–100)
    - Detailed penalty breakdown
    """

    def __init__(self, weights: Optional[TrustWeights] = None):
        self.weights = weights if weights else TrustWeights()

    # -----------------------------------------------------
    # Utility: Clamp values to safe range
    # -----------------------------------------------------

    def _clamp_probability(self, value: float) -> float:
        return max(0.0, min(1.0, value))

    # -----------------------------------------------------
    # Core Computation
    # -----------------------------------------------------

    def compute(
        self,
        hallucination: float,
        grounding: float,
        risk: str,
        number_conflict: bool = False,
        confidence_mismatch: bool = False,
        semantic_risk: bool = False,
    ) -> Dict:

        # Safety clamp
        hallucination = self._clamp_probability(hallucination)
        grounding = self._clamp_probability(grounding)

        breakdown: Dict[str, float] = {}

        # =====================================================
        # 1️⃣ Hallucination Penalty
        # =====================================================

        hallucination_penalty = hallucination * self.weights.hallucination_weight
        breakdown["hallucination_penalty"] = round(hallucination_penalty, 2)

        # =====================================================
        # 2️⃣ Grounding Penalty
        # =====================================================

        grounding_penalty = (1 - grounding) * self.weights.grounding_weight
        breakdown["grounding_penalty"] = round(grounding_penalty, 2)

        # =====================================================
        # 3️⃣ Business Risk Penalty
        # =====================================================

        risk_penalty = 0.0

        risk_normalized = str(risk).upper()

        if risk_normalized == "CRITICAL":
            risk_penalty = self.weights.critical_risk_penalty
        elif risk_normalized == "HIGH":
            risk_penalty = self.weights.high_risk_penalty
        elif risk_normalized == "MEDIUM":
            risk_penalty = self.weights.medium_risk_penalty

        breakdown["risk_penalty"] = risk_penalty

        # =====================================================
        # 4️⃣ Numeric Conflict Penalty
        # =====================================================

        number_penalty = (
            self.weights.number_conflict_penalty
            if number_conflict else 0.0
        )

        breakdown["number_conflict_penalty"] = number_penalty

        # =====================================================
        # 5️⃣ Confidence Mismatch Penalty
        # =====================================================

        confidence_penalty = (
            self.weights.confidence_mismatch_penalty
            if confidence_mismatch else 0.0
        )

        breakdown["confidence_mismatch_penalty"] = confidence_penalty

        # =====================================================
        # 6️⃣ Semantic Risk Penalty
        # =====================================================

        semantic_penalty = (
            self.weights.semantic_risk_penalty
            if semantic_risk else 0.0
        )

        breakdown["semantic_risk_penalty"] = semantic_penalty

        # =====================================================
        # 7️⃣ Total Penalty Calculation
        # =====================================================

        total_penalty = (
            hallucination_penalty
            + grounding_penalty
            + risk_penalty
            + number_penalty
            + confidence_penalty
            + semantic_penalty
        )

        breakdown["total_penalty"] = round(total_penalty, 2)

        # =====================================================
        # 8️⃣ Final Trust Score
        # =====================================================

        final_score = max(int(self.weights.base_score - total_penalty), 0)

        breakdown["final_score"] = final_score

        return {
            "trust_score": final_score,
            "breakdown": breakdown
        }