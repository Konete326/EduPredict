from datetime import datetime, timezone
import numpy as np
import pandas as pd
from pymongo import UpdateOne
from core.db import datasets_log_col, ensure_indexes, student_records_col

REQUIRED_COLUMNS = (
    "student_id", "attendance_pct", "internal_marks",
    "lms_hours_weekly", "previous_gpa", "course_code",
)
NUMERIC_COLUMNS = (
    "attendance_pct", "internal_marks", "assignment_score",
    "lms_hours_weekly", "previous_gpa",
)
CATEGORICAL_COLUMNS = ("batch", "course_code", "full_name")
NUMERIC_DEFAULTS = {
    "attendance_pct": 80.0, "internal_marks": 70.0,
    "assignment_score": 75.0, "lms_hours_weekly": 8.0, "previous_gpa": 3.0,
}
CATEGORICAL_DEFAULTS = {
    "batch": "2026-A", "course_code": "CS-101", "full_name": "Unknown Student",
}
FIRST_NAMES = (
    "Ayesha", "Bilal", "Zainab", "Hamza", "Fatima", "Usman", "Hira", "Saad",
    "Mariam", "Omar", "Sana", "Tariq", "Noor", "Imran", "Amina", "Danish",
    "Kiran", "Faisal", "Iqra", "Salman",
)
LAST_NAMES = (
    "Khan", "Ahmed", "Malik", "Raza", "Siddiqui", "Hussain",
    "Farooq", "Butt", "Chaudhry", "Qureshi", "Iqbal", "Sheikh",
)


def _normalize_column_name(col):
    name = str(col).strip().lower().replace(" ", "_")
    return "lms_hours_weekly" if name == "lms_hours" else name


def validate_dataset_columns(columns):
    present = {_normalize_column_name(col) for col in columns}
    missing = [col for col in REQUIRED_COLUMNS if col not in present]
    return {"valid": len(missing) == 0, "missing_columns": missing}


def generate_sample_dataset_df(count=60):
    rng = np.random.default_rng(42)
    batches = ("2025-A", "2025-B", "2026-A", "2026-B")
    courses = ("CS-101", "CS-101", "DS-204", "DS-204", "AI-301", "SE-210", "DB-115")
    rows = []
    for idx in range(count):
        first = FIRST_NAMES[idx % len(FIRST_NAMES)]
        last = LAST_NAMES[(idx * 3 + idx // 5) % len(LAST_NAMES)]
        bucket = idx % 20
        if bucket in (17, 19):
            ranges = ((40.0, 54.0), (28.0, 42.0), (35.0, 55.0), (2.0, 5.0), (3.35, 3.85))
        elif bucket in (14, 15, 16):
            ranges = ((38.0, 57.0), (25.0, 44.0), (30.0, 50.0), (1.0, 4.5), (1.25, 2.15))
        elif bucket in (9, 10, 11, 12, 13):
            ranges = ((64.0, 79.0), (52.0, 71.0), (55.0, 75.0), (5.0, 10.0), (2.25, 3.05))
        else:
            ranges = ((82.0, 98.0), (73.0, 96.0), (76.0, 97.0), (10.0, 20.0), (3.15, 3.96))
        rows.append({
            "student_id": f"STD-2026-{idx + 1:03d}",
            "full_name": f"{first} {last}",
            "batch": batches[idx % len(batches)],
            "course_code": courses[(idx * 2 + idx // 4) % len(courses)],
            "attendance_pct": round(float(rng.uniform(*ranges[0])), 1),
            "internal_marks": round(float(rng.uniform(*ranges[1])), 1),
            "assignment_score": round(float(rng.uniform(*ranges[2])), 1),
            "lms_hours_weekly": round(float(rng.uniform(*ranges[3])), 1),
            "previous_gpa": round(float(rng.uniform(*ranges[4])), 2),
        })
    df = pd.DataFrame(rows)
    if count >= 20:
        missing_targets = (
            (2, "attendance_pct", np.nan), (7, "attendance_pct", np.nan),
            (11, "internal_marks", np.nan), (18, "internal_marks", np.nan),
            (5, "lms_hours_weekly", np.nan), (13, "previous_gpa", np.nan),
            (16, "assignment_score", np.nan), (9, "batch", None),
        )
        for row_idx, col_name, val in missing_targets:
            if row_idx < len(df):
                df.at[row_idx, col_name] = val
    return df


def _failed_result(filename, uploaded_by, error, missing_fixed=0):
    try:
        datasets_log_col().insert_one({
            "filename": filename,
            "uploaded_by": uploaded_by or "Analyst",
            "rows_processed": 0,
            "missing_values_fixed": int(missing_fixed),
            "status": "FAILED",
            "uploaded_at": datetime.now(timezone.utc),
        })
    except Exception:
        pass
    return {
        "status": "FAILED",
        "error": error,
        "rows_processed": 0,
        "missing_values_fixed": int(missing_fixed),
    }


def _load_dataframe(file_obj, mode):
    if mode == "sample" or file_obj is None:
        return "edupredict_sample_batch.csv", generate_sample_dataset_df(60), None
    filename = str(getattr(file_obj, "name", "") or "uploaded_dataset.csv")
    lower_name = filename.lower()
    if hasattr(file_obj, "seek"):
        file_obj.seek(0)
    try:
        if lower_name.endswith(".csv"):
            return filename, pd.read_csv(file_obj), None
        if lower_name.endswith(".xlsx"):
            return filename, pd.read_excel(file_obj, engine="openpyxl"), None
        return filename, None, "Unsupported file format. Upload a .csv or .xlsx file."
    except Exception as exc:
        return filename, None, f"Failed to read dataset file: {exc}"


def _clean_categorical_series(series):
    cleaned = []
    for val in series.tolist():
        if pd.isna(val):
            cleaned.append(np.nan)
        else:
            text = str(val).strip()
            cleaned.append(np.nan if (not text or text.lower() in ("nan", "none", "null")) else text)
    return pd.Series(cleaned, index=series.index, dtype="object")


def ingest_dataset(file_obj=None, uploaded_by="", mode="upload"):
    filename, df, load_error = _load_dataframe(file_obj, mode)
    if load_error is not None:
        return _failed_result(filename, uploaded_by, load_error)

    df = df.copy()
    df.columns = [_normalize_column_name(col) for col in df.columns]
    df = df.loc[:, ~df.columns.duplicated()]

    validation = validate_dataset_columns(df.columns)
    if not validation["valid"]:
        err = f"Missing required columns: {', '.join(validation['missing_columns'])}"
        return _failed_result(filename, uploaded_by, err)

    df["student_id"] = _clean_categorical_series(df["student_id"])
    df = df.dropna(subset=["student_id"]).copy()
    if df.empty:
        return _failed_result(filename, uploaded_by, "No valid rows found after checking student_id.")

    if "full_name" not in df.columns:
        df["full_name"] = "Student " + df["student_id"].astype(str)
    if "batch" not in df.columns:
        df["batch"] = CATEGORICAL_DEFAULTS["batch"]
    if "assignment_score" not in df.columns:
        df["assignment_score"] = NUMERIC_DEFAULTS["assignment_score"]

    for col in CATEGORICAL_COLUMNS:
        df[col] = _clean_categorical_series(df[col])
    for col in NUMERIC_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    tracked_cols = ["student_id", *CATEGORICAL_COLUMNS, *NUMERIC_COLUMNS]
    missing_values_fixed = int(df[tracked_cols].isna().sum().sum())

    for col in NUMERIC_COLUMNS:
        median_val = df[col].median()
        df[col] = df[col].fillna(float(median_val) if pd.notna(median_val) else NUMERIC_DEFAULTS[col])
    for col in ("attendance_pct", "internal_marks", "assignment_score"):
        df[col] = df[col].clip(0.0, 100.0)
    df["lms_hours_weekly"] = df["lms_hours_weekly"].clip(0.0, 168.0)
    df["previous_gpa"] = df["previous_gpa"].clip(0.0, 4.0)

    for col in CATEGORICAL_COLUMNS:
        modes = df[col].dropna().mode()
        df[col] = df[col].fillna(str(modes.iloc[0]) if not modes.empty else CATEGORICAL_DEFAULTS[col])

    now = datetime.now(timezone.utc)
    operations = []
    for row in df.to_dict(orient="records"):
        sid = str(row["student_id"]).strip()
        doc = {
            "student_id": sid,
            "full_name": str(row["full_name"]).strip(),
            "batch": str(row["batch"]).strip(),
            "course_code": str(row["course_code"]).strip().upper(),
            "attendance_pct": round(float(row["attendance_pct"]), 2),
            "internal_marks": round(float(row["internal_marks"]), 2),
            "assignment_score": round(float(row["assignment_score"]), 2),
            "lms_hours_weekly": round(float(row["lms_hours_weekly"]), 2),
            "previous_gpa": round(float(row["previous_gpa"]), 2),
            "updated_at": now,
        }
        operations.append(UpdateOne({"student_id": sid}, {"$set": doc}, upsert=True))

    try:
        ensure_indexes()
        col = student_records_col()
        for start in range(0, len(operations), 500):
            col.bulk_write(operations[start:start + 500], ordered=False)
        datasets_log_col().insert_one({
            "filename": filename,
            "uploaded_by": uploaded_by or "Analyst",
            "rows_processed": len(operations),
            "missing_values_fixed": missing_values_fixed,
            "status": "COMPLETED",
            "uploaded_at": now,
        })
    except Exception as exc:
        return _failed_result(filename, uploaded_by, f"Database write failed: {exc}", missing_values_fixed)

    return {
        "status": "COMPLETED",
        "filename": filename,
        "rows_processed": len(operations),
        "missing_values_fixed": missing_values_fixed,
    }
