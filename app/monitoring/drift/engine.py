import numpy as np
from typing import Dict, Any, List
from datetime import datetime, timezone
from threading import Lock
from collections import deque
from app.monitoring.drift.metadata import DriftReport, DriftSeverity
from app.utils.logger import get_logger

logger = get_logger(__name__)

def calculate_psi(expected: List[float], actual: List[float], buckets: int = 10) -> float:
    """Calculates Population Stability Index (PSI)."""
    if len(expected) == 0 or len(actual) == 0:
        return 0.0
        
    expected_arr = np.array(expected)
    actual_arr = np.array(actual)
    
    # Calculate quantiles based on expected
    breakpoints = np.percentile(expected_arr, np.linspace(0, 100, buckets + 1))
    # Add slight noise to avoid duplicate bins
    breakpoints[0] -= 0.001
    breakpoints[-1] += 0.001
    
    # Count frequencies
    expected_counts = np.histogram(expected_arr, bins=breakpoints)[0]
    actual_counts = np.histogram(actual_arr, bins=breakpoints)[0]
    
    # Convert to fractions
    expected_fractions = expected_counts / len(expected_arr)
    actual_fractions = actual_counts / len(actual_arr)
    
    # Add epsilon to prevent division by zero or log(0)
    epsilon = 0.0001
    expected_fractions = np.where(expected_fractions == 0, epsilon, expected_fractions)
    actual_fractions = np.where(actual_fractions == 0, epsilon, actual_fractions)
    
    psi_values = (actual_fractions - expected_fractions) * np.log(actual_fractions / expected_fractions)
    return float(np.sum(psi_values))

class DriftEngine:
    """
    Manages live prediction distributions and calculates drift against baselines.
    """
    def __init__(self, window_size: int = 1000, psi_threshold_warning: float = 0.1, psi_threshold_critical: float = 0.2):
        self.window_size = window_size
        self.psi_threshold_warning = psi_threshold_warning
        self.psi_threshold_critical = psi_threshold_critical
        
        self._lock = Lock()
        # Structure: { model_id: { feature_name: deque() } }
        self._live_data: Dict[str, Dict[str, deque]] = {}
        self._predictions: Dict[str, deque] = {}

    def ingest(self, model_id: str, features: Dict[str, Any], prediction: Any) -> None:
        with self._lock:
            if model_id not in self._live_data:
                self._live_data[model_id] = {}
                self._predictions[model_id] = deque(maxlen=self.window_size)
                
            self._predictions[model_id].append(prediction)
            
            for k, v in features.items():
                if k not in self._live_data[model_id]:
                    self._live_data[model_id][k] = deque(maxlen=self.window_size)
                # Filter out nulls/None for statistical math, or store them if tracking missing shift
                if v is not None:
                    self._live_data[model_id][k].append(float(v) if isinstance(v, (int, float)) else v)

    def generate_report(self, model_id: str, baseline_profile: Dict[str, Any]) -> DriftReport:
        with self._lock:
            live = self._live_data.get(model_id, {})
            preds = list(self._predictions.get(model_id, []))
            
        if not live or not baseline_profile:
            return DriftReport(
                model_id=model_id,
                timestamp=datetime.now(timezone.utc),
                overall_drift_score=0.0,
                severity=DriftSeverity.NONE,
                drifted_features=[],
                recommendations=["Insufficient data to calculate drift."]
            )

        drifted_features = []
        max_psi = 0.0
        
        for feature, baseline_stats in baseline_profile.items():
            if feature == "_target": continue
            if feature not in live: continue
            
            live_vals = list(live[feature])
            if len(live_vals) < 50:
                continue # Need minimum sample size
                
            if baseline_stats.get("type") == "numeric":
                # To compute exact PSI we'd need original raw expected arrays, which we don't have.
                # Since we only saved baseline stats, we can generate a normal distribution approximation 
                # from baseline mean/std as a fast proxy, or use mean shift.
                # For a full PSI we'll simulate the expected distribution.
                b_mean = baseline_stats["mean"]
                b_std = baseline_stats["std"]
                if b_std == 0: b_std = 0.0001
                
                simulated_expected = np.random.normal(b_mean, b_std, 1000).tolist()
                psi = calculate_psi(simulated_expected, live_vals)
                
                live_mean = float(np.mean(live_vals))
                live_std = float(np.std(live_vals))
                
                severity = DriftSeverity.NONE
                if psi >= self.psi_threshold_critical:
                    severity = DriftSeverity.CRITICAL
                elif psi >= self.psi_threshold_warning:
                    severity = DriftSeverity.WARNING
                    
                max_psi = max(max_psi, psi)
                
                if severity != DriftSeverity.NONE:
                    drifted_features.append({
                        "feature": feature,
                        "drift_score": psi,
                        "severity": severity.value,
                        "metric": "PSI",
                        "baseline_mean": b_mean,
                        "live_mean": live_mean,
                        "baseline_std": b_std,
                        "live_std": live_std
                    })
                    # Log drift event to application logs.
                    # PostgreSQL persistence happens asynchronously via the drift API endpoint.
                    logger.warning(f"FEATURE_DRIFT detected: feature={feature}, psi_score={psi:.4f}, severity={severity.value}")
            
        overall_severity = DriftSeverity.NONE
        if max_psi >= self.psi_threshold_critical:
            overall_severity = DriftSeverity.CRITICAL
        elif max_psi >= self.psi_threshold_warning:
            overall_severity = DriftSeverity.WARNING
            
        if overall_severity != DriftSeverity.NONE:
            # Log drift event to application logs.
            # PostgreSQL persistence happens asynchronously via the drift API endpoint.
            logger.warning(f"DRIFT_DETECTED: model_id={model_id}, max_psi={max_psi:.4f}, severity={overall_severity.value}")
            
        recs = []
        if overall_severity == DriftSeverity.CRITICAL:
            recs.append("CRITICAL: Immediate model retraining required. Live data distribution has significantly diverged from training baseline.")
        elif overall_severity == DriftSeverity.WARNING:
            recs.append("WARNING: Data drift detected. Schedule a model retraining run soon.")
        else:
            recs.append("Data distributions are stable. No action required.")
            
        return DriftReport(
            model_id=model_id,
            timestamp=datetime.now(timezone.utc),
            overall_drift_score=max_psi,
            severity=overall_severity,
            drifted_features=drifted_features,
            recommendations=recs,
            model_drift={
                "prediction_count": len(preds)
            }
        )

# Global Instance
global_drift_engine = DriftEngine()
