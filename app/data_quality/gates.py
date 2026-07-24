from typing import Dict, Tuple
from great_expectations.core.expectation_validation_result import ExpectationSuiteValidationResult


class QualityGate:
    """
    Evaluates Validation Results against Data Contracts and severities.
    Calculates Dataset Health Score.
    """

    @staticmethod
    def evaluate(results: ExpectationSuiteValidationResult) -> Tuple[bool, float, Dict[str, int]]:
        """
        Returns:
        - should_halt (bool): True if any CRITICAL failures exist.
        - health_score (float): 0.0 to 100.0
        - counts (dict): Count of failures by severity
        """
        counts = {
            "critical": 0,
            "error": 0,
            "warning": 0,
            "info": 0
        }

        total_expectations = len(results.results)
        if total_expectations == 0:
            return False, 100.0, counts

        success_count = 0
        weighted_penalty = 0.0

        # Base penalty weights
        penalties = {
            "CRITICAL": 20.0,
            "ERROR": 10.0,
            "WARNING": 2.5,
            "INFO": 0.0
        }

        for result in results.results:
            if result.success:
                success_count += 1
                continue

            # It failed
            meta = result.expectation_config.meta if result.expectation_config else {}
            severity = meta.get("severity", "ERROR").upper()

            if severity.lower() in counts:
                counts[severity.lower()] += 1
            else:
                counts["error"] += 1

            weighted_penalty += penalties.get(severity, 10.0)

        # Health score calculation
        # Start at 100, subtract weighted penalties, floor at 0
        health_score = max(0.0, 100.0 - weighted_penalty)

        # Gate Decision: Block ONLY on CRITICAL failures
        should_halt = (counts["critical"] > 0)

        return should_halt, health_score, counts
