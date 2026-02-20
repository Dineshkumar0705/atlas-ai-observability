import re
from typing import List, Dict


class NumberConflictEngine:
    """
    Deterministic numeric contradiction detector.
    Handles:
    - Direct mismatches
    - Range expansion
    - New numeric claims
    """

    def _extract_numbers(self, text: str) -> List[int]:
        return list(map(int, re.findall(r"\d+", text)))

    def detect_conflict(self, context: List[str], response: str) -> Dict:
        """
        Returns:
        {
            conflict: bool,
            severity: str,
            conflict_type: str,
            context_numbers: list,
            response_numbers: list,
            details: list
        }
        """

        full_context = " ".join(context)

        context_numbers = self._extract_numbers(full_context)
        response_numbers = self._extract_numbers(response)

        result = {
            "conflict": False,
            "severity": "NONE",
            "conflict_type": None,
            "context_numbers": context_numbers,
            "response_numbers": response_numbers,
            "details": []
        }

        if not context_numbers or not response_numbers:
            return result

        context_set = set(context_numbers)
        response_set = set(response_numbers)

        # 1️⃣ New numeric claims
        new_numbers = response_set - context_set
        if new_numbers:
            result["conflict"] = True
            result["conflict_type"] = "new_numeric_claim"
            result["severity"] = "MEDIUM"
            result["details"].append(
                f"Response introduces new numbers: {list(new_numbers)}"
            )

        # 2️⃣ Range expansion detection
        if len(context_numbers) == 1 and len(response_numbers) == 1:
            context_val = context_numbers[0]
            response_val = response_numbers[0]

            if response_val > context_val:
                result["conflict"] = True
                result["conflict_type"] = "range_expansion"
                result["severity"] = "HIGH"
                result["details"].append(
                    f"Response value {response_val} exceeds context value {context_val}"
                )

            elif response_val < context_val:
                result["conflict"] = True
                result["conflict_type"] = "range_reduction"
                result["severity"] = "LOW"
                result["details"].append(
                    f"Response value {response_val} reduces context value {context_val}"
                )

        return result