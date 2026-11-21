import math
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

FEATURE_COLUMNS = (
    "attendance_pct",
    "internal_marks",
    "assignment_score",
    "lms_hours_weekly",
    "previous_gpa",
)
FEATURE_DEFAULTS = {
    "attendance_pct": 80.0,
    "internal_marks": 70.0,
    "assignment_score": 75.0,
    "lms_hours_weekly": 8.0,
    "previous_gpa": 3.0,
}
FEATURE_BOUNDS = {
    "attendance_pct": (0.0, 100.0),
    "internal_marks": (0.0, 100.0),
    "assignment_score": (0.0, 100.0),
    "lms_hours_weekly": (0.0, 168.0),
    "previous_gpa": (0.0, 4.0),
}
DEFAULT_RANDOM_STATE = 42


class MedianFallbackImputer(BaseEstimator, TransformerMixin):
    def __init__(self, fallback_values=None):
        self.fallback_values = fallback_values

    def fit(self, X, y=None):
        arr = np.asarray(X, dtype=float)
        if arr.ndim != 2:
            raise ValueError("Input features must be a 2D array.")
        fallbacks = (
            list(self.fallback_values)
            if self.fallback_values is not None
            else [0.0] * arr.shape[1]
        )
        medians = []
        for idx in range(arr.shape[1]):
            col_vals = arr[:, idx]
            finite_vals = col_vals[np.isfinite(col_vals)]
            if finite_vals.size > 0:
                medians.append(float(np.median(finite_vals)))
            else:
                fallback = fallbacks[idx] if idx < len(fallbacks) else 0.0
                medians.append(float(fallback))
        self.statistics_ = np.asarray(medians, dtype=float)
        return self

    def transform(self, X):
        arr = np.asarray(X, dtype=float).copy()
        if arr.ndim != 2 or arr.shape[1] != self.statistics_.shape[0]:
            raise ValueError("Input feature dimensions do not match fitted imputer.")
        for idx in range(arr.shape[1]):
            bad_mask = ~np.isfinite(arr[:, idx])
            if bad_mask.any():
                arr[bad_mask, idx] = self.statistics_[idx]
        return arr


def validate_eval_params(test_size, random_state):
    try:
        ts = float(test_size)
    except (TypeError, ValueError) as exc:
        raise ValueError("test_size must be a float between 0.0 and 1.0.") from exc
    if not math.isfinite(ts) or ts <= 0.0 or ts >= 1.0:
        raise ValueError("test_size must be strictly between 0.0 and 1.0.")
    try:
        rs = int(random_state)
    except (TypeError, ValueError) as exc:
        raise ValueError("random_state must be a non-negative integer.") from exc
    if rs < 0:
        raise ValueError("random_state must be a non-negative integer.")
    return ts, rs


def parse_binary_label(value):
    if value is None or isinstance(value, (list, dict, tuple, set)):
        return None
    if isinstance(value, bool):
        return 1 if value else 0
    if isinstance(value, (int, np.integer)):
        return int(value) if int(value) in (0, 1) else None
    if isinstance(value, (float, np.floating)):
        if not math.isfinite(float(value)):
            return None
        return int(value) if float(value) in (0.0, 1.0) else None
    text = str(value).strip().lower()
    if text in ("", "nan", "none", "null", "na", "n/a"):
        return None
    if text in ("1", "1.0", "true", "yes", "y", "dropout", "dropped", "dropped_out", "anomaly"):
        return 1
    if text in ("0", "0.0", "false", "no", "n", "retained", "active", "normal", "not_dropout"):
        return 0
    return None


def parse_gpa_label(value):
    if value is None or isinstance(value, (bool, list, dict, tuple, set)):
        return None
    try:
        num = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(num) or num < 0.0 or num > 4.0:
        return None
    return round(num, 4)


def prepare_feature_frame(records):
    if isinstance(records, pd.DataFrame):
        df = records.copy()
    elif isinstance(records, (list, tuple)):
        if not records:
            return pd.DataFrame(columns=list(FEATURE_COLUMNS))
        if not all(isinstance(row, dict) for row in records):
            raise ValueError("Each record must be a dictionary of student attributes.")
        df = pd.DataFrame(list(records))
    else:
        raise ValueError("records must be a pandas DataFrame or a list/tuple of dictionaries.")

    if df.empty:
        return df

    recognized = [col for col in FEATURE_COLUMNS if col in df.columns]
    if not recognized:
        raise ValueError(
            "Dataset contains none of the required feature columns: "
            + ", ".join(FEATURE_COLUMNS)
        )

    for col in FEATURE_COLUMNS:
        if col not in df.columns:
            df[col] = np.nan
        numeric = pd.to_numeric(df[col], errors="coerce").astype(float)
        numeric = numeric.replace([np.inf, -np.inf], np.nan)
        low, high = FEATURE_BOUNDS[col]
        df[col] = numeric.clip(low, high)

    return df


def build_dropout_pipeline(random_state=DEFAULT_RANDOM_STATE):
    fallback_list = [FEATURE_DEFAULTS[col] for col in FEATURE_COLUMNS]
    return Pipeline([
        ("imputer", MedianFallbackImputer(fallback_list)),
        ("model", RandomForestClassifier(
            n_estimators=50,
            n_jobs=-1,
            max_depth=4,
            min_samples_leaf=2,
            random_state=random_state,
        )),
    ])


def build_gpa_pipeline():
    fallback_list = [FEATURE_DEFAULTS[col] for col in FEATURE_COLUMNS]
    return Pipeline([
        ("imputer", MedianFallbackImputer(fallback_list)),
        ("scaler", StandardScaler()),
        ("model", Ridge(alpha=1.0)),
    ])


def build_anomaly_pipeline(contamination=0.12, random_state=DEFAULT_RANDOM_STATE):
    fallback_list = [FEATURE_DEFAULTS[col] for col in FEATURE_COLUMNS]
    return Pipeline([
        ("imputer", MedianFallbackImputer(fallback_list)),
        ("scaler", StandardScaler()),
        ("model", IsolationForest(contamination=contamination, random_state=random_state)),
    ])
