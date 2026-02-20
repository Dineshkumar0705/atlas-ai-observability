from typing import Dict, List


class BusinessRiskEngine:
    """
    Deterministic risk classification engine.
    Evaluates query for business-sensitive domains.
    """

    # Keyword risk registry with weights
    RISK_REGISTRY: Dict[str, int] = {
        # Financial
        "investment": 2,
        "stock": 2,
        "crypto": 2,
        "guarantee": 3,
        "loan": 2,

        # Legal
        "legal": 3,
        "lawsuit": 3,
        "contract": 2,
        "compliance": 2,

        # Medical
        "medical": 3,
        "diagnose": 4,
        "prescribe": 4,
        "treatment": 2,

        # Refund / Policy
        "refund": 2,
        "return": 1,
        "policy": 1,
    }

    def assess(self, query: str) -> Dict:
        query_lower = query.lower()

        triggered_keywords: List[str] = []
        risk_score = 0

        # Calculate weighted risk score
        for keyword, weight in self.RISK_REGISTRY.items():
            if keyword in query_lower:
                risk_score += weight
                triggered_keywords.append(keyword)

        # Classify risk level
        if risk_score >= 5:
            risk_level = "CRITICAL"
        elif risk_score >= 3:
            risk_level = "HIGH"
        elif risk_score >= 1:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        return {
            "risk_level": risk_level,
            "risk_score": risk_score,
            "triggered_keywords": triggered_keywords,
        }