from datetime import datetime, timezone
import re
import numpy as np
import pandas as pd
from pymongo import UpdateOne
from analytics.preprocessing import parse_binary_label, parse_gpa_label
from core.db import datasets_log_col, ensure_indexes, invalidate_cache, student_records_col

REQUIRED_COLUMNS = ("student_id",)
MAX_UPLOAD_BYTES = 25 * 1024 * 1024
NUMERIC_COLUMNS = ("attendance_pct", "internal_marks", "assignment_score", "lms_hours_weekly", "previous_gpa")
CATEGORICAL_COLUMNS = ("batch", "course_code", "full_name")
NUMERIC_DEFAULTS = {"attendance_pct": 80.0, "internal_marks": 70.0, "assignment_score": 75.0, "lms_hours_weekly": 8.0, "previous_gpa": 3.0}
CATEGORICAL_DEFAULTS = {"batch": "2026-A", "course_code": "CS-101", "full_name": "Unknown Student"}
COLUMN_ALIASES = {
    "marks": "internal_marks", "mark": "internal_marks", "score": "internal_marks",
    "internal_mark": "internal_marks", "total_marks": "internal_marks", "obtained_marks": "internal_marks",
    "class_marks": "internal_marks", "exam_marks": "internal_marks", "test_score": "internal_marks",
    "exam_score": "internal_marks", "quiz_marks": "internal_marks",
    "attendance": "attendance_pct", "att": "attendance_pct", "att_pct": "attendance_pct",
    "attpct": "attendance_pct", "pct_attendance": "attendance_pct", "attendance_rate": "attendance_pct",
    "attendance_percentage": "attendance_pct",
    "roll_no": "student_id", "roll_number": "student_id", "enrollment": "student_id",
    "enrollment_no": "student_id", "reg_no": "student_id", "registration_no": "student_id",
    "id": "student_id", "std_id": "student_id", "student": "student_id", "student_id_number": "student_id",
    "name": "full_name", "student_name": "full_name",
    "dob": "birth_date", "date_of_birth": "birth_date", "birthdate": "birth_date",
    "birthday": "birth_date", "birth_day": "birth_date", "bdate": "birth_date",
    "course": "course_code", "course_id": "course_code", "subject": "course_code", "class": "course_code",
    "batch_name": "batch", "section": "batch",
    "assignment": "assignment_score", "assignments": "assignment_score",
    "lms_hours": "lms_hours_weekly", "study_hours": "lms_hours_weekly", "hours": "lms_hours_weekly",
    "gpa": "previous_gpa", "prev_gpa": "previous_gpa", "cgpa": "previous_gpa",
    "actual_dropout": "dropout_label", "dropped_out": "dropout_label", "is_dropout": "dropout_label",
    "dropout": "dropout_label", "dropout_status": "dropout_label", "target_dropout": "dropout_label",
    "final_gpa": "actual_gpa", "next_gpa": "actual_gpa", "target_gpa": "actual_gpa",
    "semester_gpa": "actual_gpa", "earned_gpa": "actual_gpa",
    "actual_anomaly": "anomaly_label", "is_anomaly_label": "anomaly_label", "anomaly_target": "anomaly_label",
}
FIRST_NAMES = ("Ayesha", "Bilal", "Zainab", "Hamza", "Fatima", "Usman", "Hira", "Saad", "Mariam", "Omar", "Sana", "Tariq", "Noor", "Imran", "Amina", "Danish", "Kiran", "Faisal", "Iqra", "Salman")
LAST_NAMES = ("Khan", "Ahmed", "Malik", "Raza", "Siddiqui", "Hussain", "Farooq", "Butt", "Chaudhry", "Qureshi", "Iqbal", "Sheikh")


def _normalize_column_name(col):
    name = re.sub(r"_+", "_", str(col).strip().lower().replace("%", "pct").replace(" ", "_").replace("-", "_").replace(".", "_")).strip("_")
    return COLUMN_ALIASES.get(name, name)


def _write_ops(col, ops):
    if hasattr(col, "bulk_write"):
        for start in range(0, len(ops), 500):
            col.bulk_write(ops[start:start + 500], ordered=False)
    else:
        for op in ops:
            col.update_one(op._filter, op._doc, upsert=op._upsert)


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
        first, last, bucket = FIRST_NAMES[idx % len(FIRST_NAMES)], LAST_NAMES[(idx * 3 + idx // 5) % len(LAST_NAMES)], idx % 20
        if bucket in (17, 19):
            ranges = ((40.0, 54.0), (28.0, 42.0), (35.0, 55.0), (2.0, 5.0), (3.35, 3.85))
        elif bucket in (14, 15, 16):
            ranges = ((38.0, 57.0), (25.0, 44.0), (30.0, 50.0), (1.0, 4.5), (1.25, 2.15))
        elif bucket in (9, 10, 11, 12, 13):
            ranges = ((64.0, 79.0), (52.0, 71.0), (55.0, 75.0), (5.0, 10.0), (2.25, 3.05))
        else:
            ranges = ((82.0, 98.0), (73.0, 96.0), (76.0, 97.0), (10.0, 20.0), (3.15, 3.96))
        rows.append({
            "student_id": f"STD-2026-{idx + 1:03d}", "full_name": f"{first} {last}",
            "birth_date": f"{2002 + (idx % 4)}-{(idx % 12) + 1:02d}-{(idx % 25) + 1:02d}",
            "batch": batches[idx % len(batches)], "course_code": courses[(idx * 2 + idx // 4) % len(courses)],
            "attendance_pct": round(float(rng.uniform(*ranges[0])), 1),
            "internal_marks": round(float(rng.uniform(*ranges[1])), 1),
            "assignment_score": round(float(rng.uniform(*ranges[2])), 1),
            "lms_hours_weekly": round(float(rng.uniform(*ranges[3])), 1),
            "previous_gpa": round(float(rng.uniform(*ranges[4])), 2),
        })
    df = pd.DataFrame(rows)
    if count >= 20:
        for row_idx, col_name, val in ((2, "attendance_pct", np.nan), (7, "attendance_pct", np.nan), (11, "internal_marks", np.nan), (18, "internal_marks", np.nan), (5, "lms_hours_weekly", np.nan), (13, "previous_gpa", np.nan), (16, "assignment_score", np.nan), (9, "batch", None)):
            if row_idx < len(df):
                df.at[row_idx, col_name] = val
    return df


def _failed_result(filename, uploaded_by, error, missing_fixed=0):
    try:
        datasets_log_col().insert_one({"filename": filename, "uploaded_by": uploaded_by or "Analyst", "rows_processed": 0, "missing_values_fixed": int(missing_fixed), "status": "FAILED", "uploaded_at": datetime.now(timezone.utc)})
    except Exception:
        pass
    return {"status": "FAILED", "error": error, "rows_processed": 0, "missing_values_fixed": int(missing_fixed)}


def _load_dataframe(file_obj, mode):
    if mode == "sample" or file_obj is None:
        return "edupredict_sample_batch.csv", generate_sample_dataset_df(60), None
    filename = str(getattr(file_obj, "name", "") or "uploaded_dataset.csv")
    lower_name = filename.lower()
    file_size = getattr(file_obj, "size", None)
    if file_size is None and hasattr(file_obj, "seek") and hasattr(file_obj, "tell"):
        try:
            file_obj.seek(0, 2)
            file_size = file_obj.tell()
            file_obj.seek(0)
        except Exception:
            file_size = None
    if file_size is not None and file_size > MAX_UPLOAD_BYTES:
        return filename, None, "Dataset file exceeds the 25 MB upload limit."
    if hasattr(file_obj, "seek"):
        file_obj.seek(0)
    try:
        if lower_name.endswith(".csv"):
            chunks = list(pd.read_csv(file_obj, chunksize=2000))
            return (filename, pd.concat(chunks, ignore_index=True), None) if chunks else (filename, None, "Uploaded CSV file is empty.")
        if lower_name.endswith(".xlsx"):
            return filename, pd.read_excel(file_obj, engine="openpyxl"), None
        return filename, None, "Unsupported file format. Upload a .csv or .xlsx file."
    except pd.errors.EmptyDataError:
        return filename, None, "Uploaded CSV file is empty."
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


def _clean_birth_date(val):
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return ""
    if hasattr(val, "strftime"):
        return val.strftime("%Y-%m-%d")
    text = str(val).strip()
    if not text or text.lower() in ("nan", "none", "null", "nat"):
        return ""
    return text[:10] if (" " in text and len(text) >= 10 and text[4:5] == "-") else text


def _teacher_meta(teacher_user, uploaded_by):
    if not isinstance(teacher_user, dict):
        return {}
    uid = str(teacher_user.get("user_id") or "").strip()
    name = str(teacher_user.get("full_name") or uploaded_by or "").strip()
    email = str(teacher_user.get("email") or "").strip().lower()
    return {"teacher_user_id": uid, "teacher_name": name or "Teacher", "teacher_email": email} if (uid or email or name) else {}


def ingest_dataset(file_obj=None, uploaded_by="", mode="upload", teacher_user=None):
    filename, df, load_error = _load_dataframe(file_obj, mode)
    if load_error is not None:
        return _failed_result(filename, uploaded_by, load_error)

    df = df.copy()
    raw_headers = [str(col) for col in df.columns]
    normalized_headers = [_normalize_column_name(col) for col in raw_headers]
    column_mappings = {raw: norm for raw, norm in zip(raw_headers, normalized_headers)}
    df.columns = normalized_headers
    df = df.loc[:, ~df.columns.duplicated()]

    validation = validate_dataset_columns(df.columns)
    if not validation["valid"]:
        return _failed_result(filename, uploaded_by, f"Missing required columns: {', '.join(validation['missing_columns'])}")

    df["student_id"] = _clean_categorical_series(df["student_id"])
    df = df.dropna(subset=["student_id"]).copy()
    if df.empty:
        return _failed_result(filename, uploaded_by, "No valid rows found after checking student_id.")

    existing_info = {}
    try:
        sids = [str(x).strip() for x in df["student_id"].tolist() if str(x).strip()]
        for rec in student_records_col().find({"student_id": {"$in": sids}}, {"_id": 0, "student_id": 1, "full_name": 1, "course_code": 1, "batch": 1, "birth_date": 1}):
            existing_info[rec["student_id"]] = rec
    except Exception:
        pass

    has_birth_date = "birth_date" in df.columns
    if "full_name" not in df.columns:
        df["full_name"] = df["student_id"].apply(lambda s: existing_info.get(s, {}).get("full_name") or f"Student {s}")
    if "batch" not in df.columns:
        df["batch"] = df["student_id"].apply(lambda s: existing_info.get(s, {}).get("batch") or CATEGORICAL_DEFAULTS["batch"])
    if "course_code" not in df.columns:
        df["course_code"] = df["student_id"].apply(lambda s: existing_info.get(s, {}).get("course_code") or CATEGORICAL_DEFAULTS["course_code"])
    for col in ("attendance_pct", "internal_marks", "lms_hours_weekly", "previous_gpa"):
        if col not in df.columns:
            df[col] = NUMERIC_DEFAULTS[col]
    if "assignment_score" not in df.columns:
        df["assignment_score"] = df["internal_marks"]

    for col in CATEGORICAL_COLUMNS:
        df[col] = _clean_categorical_series(df[col])
    for col in NUMERIC_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="coerce").replace([np.inf, -np.inf], np.nan)

    missing_values_fixed = int(df[["student_id", *CATEGORICAL_COLUMNS, *NUMERIC_COLUMNS]].isna().sum().sum())
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

    has_dropout_label, has_actual_gpa, has_anomaly_label = "dropout_label" in df.columns, "actual_gpa" in df.columns, "anomaly_label" in df.columns
    if has_dropout_label:
        df["dropout_label"] = df["dropout_label"].apply(parse_binary_label)
    if has_actual_gpa:
        df["actual_gpa"] = df["actual_gpa"].apply(parse_gpa_label)
    if has_anomaly_label:
        df["anomaly_label"] = df["anomaly_label"].apply(parse_binary_label)

    now, t_meta = datetime.now(timezone.utc), _teacher_meta(teacher_user, uploaded_by)
    operations, preview_rows, ingested_rows = [], [], []
    label_counts = {"dropout_label": 0, "actual_gpa": 0, "anomaly_label": 0}
    for row in df.to_dict(orient="records"):
        sid = str(row["student_id"]).strip()
        bdate = _clean_birth_date(row.get("birth_date")) if has_birth_date else _clean_birth_date(existing_info.get(sid, {}).get("birth_date"))
        doc = {
            "student_id": sid, "full_name": str(row["full_name"]).strip(), "batch": str(row["batch"]).strip(),
            "course_code": str(row["course_code"]).strip().upper(),
            "attendance_pct": round(float(row["attendance_pct"]), 2), "internal_marks": round(float(row["internal_marks"]), 2),
            "assignment_score": round(float(row["assignment_score"]), 2), "lms_hours_weekly": round(float(row["lms_hours_weekly"]), 2),
            "previous_gpa": round(float(row["previous_gpa"]), 2), "updated_at": now,
        }
        if bdate:
            doc["birth_date"] = bdate
        if t_meta:
            doc.update(t_meta)
        ingested_rows.append({"student_id": sid, "full_name": doc["full_name"], "birth_date": bdate, "course_code": doc["course_code"], "batch": doc["batch"]})
        if len(preview_rows) < 3:
            preview_rows.append({k: doc[k] for k in ("student_id", "full_name", "batch", "course_code", "attendance_pct", "internal_marks", "previous_gpa")})
        for has_flag, key, cast in ((has_dropout_label, "dropout_label", int), (has_actual_gpa, "actual_gpa", float), (has_anomaly_label, "anomaly_label", int)):
            if has_flag:
                val = row.get(key)
                doc[key] = cast(val) if pd.notna(val) else None
                if doc[key] is not None:
                    label_counts[key] += 1
        operations.append(UpdateOne({"student_id": sid}, {"$set": doc}, upsert=True))

    try:
        ensure_indexes()
        _write_ops(student_records_col(), operations)
        log_doc = {"filename": filename, "uploaded_by": uploaded_by or "Analyst", "rows_processed": len(operations), "missing_values_fixed": missing_values_fixed, "status": "COMPLETED", "uploaded_at": now}
        if t_meta.get("teacher_user_id"):
            log_doc["teacher_user_id"] = t_meta["teacher_user_id"]
        datasets_log_col().insert_one(log_doc)
        invalidate_cache("analyst:")
        invalidate_cache("teacher:")
    except Exception as exc:
        return _failed_result(filename, uploaded_by, f"Database write failed: {exc}", missing_values_fixed)

    return {"status": "COMPLETED", "filename": filename, "rows_processed": len(operations), "missing_values_fixed": missing_values_fixed, "labels_detected": label_counts, "column_mappings": column_mappings, "preview_rows": preview_rows, "ingested_rows": ingested_rows}
