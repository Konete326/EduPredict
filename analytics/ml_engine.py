from datetime import datetime, timezone
import numpy as np
import pandas as pd
from pymongo import UpdateOne
from analytics.evaluation import DEFAULT_TEST_SIZE, evaluate_model_suite
from analytics.preprocessing import (
    DEFAULT_RANDOM_STATE, FEATURE_COLUMNS, FEATURE_DEFAULTS, build_anomaly_pipeline,
    build_dropout_pipeline, build_gpa_pipeline, parse_binary_label, parse_gpa_label,
    prepare_feature_frame, validate_eval_params,
)
from core.db import invalidate_cache, notifications_col, predictions_col, student_records_col

MODEL_VERSION = "sklearn-rf-ridge-if-v1.1"
DEFAULT_RUNTIME_SETTINGS = {
    "high_risk_threshold": 70, "medium_risk_threshold": 35, "anomaly_drop_pct": 25,
    "min_attendance_pct": 75, "passing_gpa": 2.0,
    "auto_student_alerts": True, "auto_teacher_alerts": True,
}
ANCHOR_SAMPLES = np.array([
    [96.0, 92.0, 94.0, 18.0, 3.90], [90.0, 84.0, 86.0, 14.0, 3.60],
    [85.0, 78.0, 80.0, 11.0, 3.25], [82.0, 74.0, 78.0, 12.0, 3.10],
    [76.0, 68.0, 72.0, 8.5, 2.85], [75.0, 66.0, 70.0, 8.0, 2.80],
    [71.0, 62.0, 66.0, 7.0, 2.60], [70.0, 61.0, 65.0, 6.8, 2.55],
    [66.0, 56.0, 60.0, 5.8, 2.40], [65.0, 55.0, 59.0, 5.5, 2.35],
    [54.0, 42.0, 46.0, 3.8, 1.95], [48.0, 36.0, 40.0, 2.8, 1.65],
    [42.0, 30.0, 34.0, 2.0, 1.40], [35.0, 24.0, 28.0, 1.5, 1.20],
    [48.0, 36.0, 42.0, 3.0, 3.55], [55.0, 40.0, 46.0, 4.0, 3.40],
], dtype=float)
ANCHOR_RISK_LABELS = np.array(
    [0, 0, 0, 0, 0, 1, 0, 1, 0, 1, 1, 1, 1, 1, 1, 1],
    dtype=int,
)
ANCHOR_GPA_TARGETS = np.array([
    3.88, 3.55, 3.28, 3.12, 2.82, 2.75, 2.55, 2.50,
    2.32, 2.28, 1.82, 1.55, 1.32, 1.15, 2.05, 2.25,
], dtype=float)


def classify_dropout_risk(score, high_threshold=0.70, medium_threshold=0.35):
    if score >= high_threshold:
        return "HIGH"
    if score >= medium_threshold:
        return "MEDIUM"
    return "LOW"


def compute_course_demand(df):
    if df is None or df.empty or "course_code" not in df.columns:
        return []
    work = df.copy()
    work["previous_gpa"] = (
        pd.to_numeric(work.get("previous_gpa"), errors="coerce")
        .replace([np.inf, -np.inf], np.nan)
        .fillna(3.0)
        .clip(0.0, 4.0)
    )
    work["attendance_pct"] = (
        pd.to_numeric(work.get("attendance_pct"), errors="coerce")
        .replace([np.inf, -np.inf], np.nan)
        .fillna(80.0)
        .clip(0.0, 100.0)
    )
    demand_rows = []
    for course_code, group in work.groupby("course_code"):
        enrolled = int(len(group))
        avg_gpa = round(float(group["previous_gpa"].mean()), 2)
        avg_att = float(group["attendance_pct"].mean())
        factor = 1.0 + max(-0.08, min(0.35, (avg_gpa - 2.4) * 0.14 + (avg_att - 70.0) * 0.002))
        projected = max(1, int(round(enrolled * factor)))
        growth = round(((projected - enrolled) / max(enrolled, 1)) * 100.0, 1)
        demand_rows.append({
            "course_code": str(course_code),
            "current_enrolled": enrolled,
            "avg_gpa": avg_gpa,
            "projected_demand": projected,
            "growth_pct": growth,
        })
    demand_rows.sort(key=lambda item: item["projected_demand"], reverse=True)
    return demand_rows


def _prepare_dataframe(records):
    df = prepare_feature_frame(records)
    if df.empty:
        return df
    if "student_id" not in df.columns:
        raise ValueError("Each student record must include a non-empty 'student_id'.")
    cleaned_sids = []
    for raw_sid in df["student_id"].tolist():
        if pd.isna(raw_sid):
            cleaned_sids.append("")
        else:
            text = str(raw_sid).strip()
            cleaned_sids.append("" if text.lower() in ("nan", "none", "null") else text)
    df["student_id"] = cleaned_sids
    df = df[df["student_id"] != ""].copy()
    if df.empty:
        raise ValueError("No valid student records found after checking 'student_id'.")

    if "course_code" in df.columns:
        df["course_code"] = (
            df["course_code"]
            .fillna("CS-101")
            .astype(str)
            .str.strip()
            .replace("", "CS-101")
            .str.upper()
        )
    else:
        df["course_code"] = "CS-101"

    if "full_name" in df.columns:
        df["full_name"] = (
            df["full_name"]
            .fillna("Student")
            .astype(str)
            .str.strip()
            .replace("", "Student")
        )
    else:
        df["full_name"] = "Student"
    return df


def _derive_weak_targets(features):
    finite_mask = np.isfinite(features).all(axis=1)
    safe = np.where(np.isfinite(features), features, 0.0)
    att, marks, assign, lms, gpa = [safe[:, i] for i in range(5)]
    risk_signal = (
        0.38 * (1.0 - att / 100.0)
        + 0.28 * (1.0 - marks / 100.0)
        + 0.14 * (1.0 - assign / 100.0)
        + 0.10 * np.clip(1.0 - lms / 15.0, 0.0, 1.0)
        + 0.10 * (1.0 - gpa / 4.0)
    )
    confident_mask = finite_mask & ((risk_signal >= 0.48) | (risk_signal <= 0.24))
    risk_labels = (risk_signal >= 0.48).astype(int)
    gpa_targets = np.clip(
        0.45 * gpa + 0.30 * (marks / 25.0) + 0.15 * (assign / 25.0) + 0.10 * (att / 25.0),
        0.0, 4.0,
    )
    return finite_mask, confident_mask, risk_labels, gpa_targets


def _positive_class_probs(pipeline, features):
    probs = pipeline.predict_proba(features)
    model = pipeline.named_steps["model"]
    classes = list(model.classes_)
    if 1 in classes:
        return np.clip(probs[:, classes.index(1)], 0.0, 1.0)
    return np.zeros(len(features), dtype=float)


def _build_anomaly_reason(att, marks, gpa, iso_flag, drop_limit=25.0):
    reasons = []
    if att < 60.0:
        reasons.append("Attendance below 60%")
    if marks < 45.0:
        reasons.append("Internal marks below 45%")
    if (gpa * 25.0 - marks) > drop_limit:
        reasons.append(f"Sudden >{int(round(drop_limit))}% score drop vs previous GPA")
    if iso_flag == -1 and not reasons:
        reasons.append("Outlier pattern flagged by Isolation Forest")
    return "; ".join(reasons)


def _resolve_runtime_settings(portal_settings=None, persist=True):
    cfg = dict(DEFAULT_RUNTIME_SETTINGS)
    source = portal_settings if isinstance(portal_settings, dict) else None
    if source is None and persist:
        try:
            from panels.admin_audit_services import get_portal_settings
            loaded = get_portal_settings()
            source = loaded.get("settings_data") if isinstance(loaded, dict) else None
        except Exception:
            source = None
    if isinstance(source, dict):
        for key in ("high_risk_threshold", "medium_risk_threshold", "anomaly_drop_pct", "min_attendance_pct"):
            if key in source:
                try:
                    cfg[key] = int(source[key])
                except (TypeError, ValueError):
                    pass
        if "passing_gpa" in source:
            try:
                cfg["passing_gpa"] = float(source["passing_gpa"])
            except (TypeError, ValueError):
                pass
        for key in ("auto_student_alerts", "auto_teacher_alerts"):
            if key in source:
                cfg[key] = bool(source[key])
    return cfg


def _build_recommendation(risk_level, is_anomaly, att, marks, assign, lms, min_att=75.0):
    if risk_level == "HIGH":
        return (
            "Schedule immediate advisor check-in, target >=80% class attendance, "
            "and complete weekly remedial practice in LMS."
        )
    if is_anomaly:
        return (
            "Review recent attendance and assessment shifts with course instructor "
            "to stabilize current term trajectory."
        )
    if risk_level == "MEDIUM":
        if att < float(min_att):
            boost_target = min(100, int(round(float(min_att))) + 5)
            return f"Attend the next 4 consecutive lectures to lift attendance above {boost_target}%."
        if marks < 65.0 or assign < 65.0:
            return "Focus on upcoming internal quizzes and assignment submissions to boost GPA."
        if lms < 7.0:
            return "Increase weekly LMS study hours above 8 hrs/week for steady progress."
        return "Maintain consistent study schedule and monitor upcoming quiz scores."
    return "Strong academic trajectory. Keep up regular attendance and LMS engagement."


def evaluate_models(records=None, test_size=DEFAULT_TEST_SIZE, random_state=DEFAULT_RANDOM_STATE):
    ts, rs = validate_eval_params(test_size, random_state)
    raw_records = (
        list(student_records_col().find({}, {"_id": 0}))
        if records is None
        else records
    )
    report = evaluate_model_suite(raw_records, test_size=ts, random_state=rs)
    report["model_version"] = MODEL_VERSION
    return report


def run_prediction_pipeline(records=None, persist=True, test_size=DEFAULT_TEST_SIZE, random_state=DEFAULT_RANDOM_STATE, portal_settings=None):
    ts, rs = validate_eval_params(test_size, random_state)
    cfg = _resolve_runtime_settings(portal_settings=portal_settings, persist=persist)
    raw_records = list(student_records_col().find({}, {"_id": 0})) if records is None else records
    df = _prepare_dataframe(raw_records)
    if df.empty:
        return {
            "status": "EMPTY", "model_version": MODEL_VERSION, "predictions_generated": 0,
            "high_risk_count": 0, "medium_risk_count": 0, "low_risk_count": 0, "anomalies_count": 0,
            "course_demand": [], "applied_settings": cfg,
            "evaluation": evaluate_model_suite(df, test_size=ts, random_state=rs),
        }

    evaluation = evaluate_model_suite(df, test_size=ts, random_state=rs)
    evaluation["model_version"] = MODEL_VERSION
    features = df[list(FEATURE_COLUMNS)].to_numpy(dtype=float)
    finite_mask, confident_mask, weak_risk, weak_gpa = _derive_weak_targets(features)

    rf_pipeline = build_dropout_pipeline(random_state=rs)
    if evaluation["models"]["dropout_classifier"]["status"] == "EVALUATED":
        parsed_drop = df["dropout_label"].apply(parse_binary_label)
        valid_drop = parsed_drop.notna().to_numpy()
        rf_pipeline.fit(features[valid_drop], parsed_drop[valid_drop].astype(int).to_numpy())
        dropout_mode = "genuine_labels"
    else:
        rf_train_x = np.vstack([ANCHOR_SAMPLES, features[confident_mask]]) if confident_mask.any() else ANCHOR_SAMPLES
        rf_train_y = np.concatenate([ANCHOR_RISK_LABELS, weak_risk[confident_mask]]) if confident_mask.any() else ANCHOR_RISK_LABELS
        rf_pipeline.fit(rf_train_x, rf_train_y)
        dropout_mode = "synthetic_anchor_and_heuristic_fallback"
    risk_probs = _positive_class_probs(rf_pipeline, features)

    ridge_pipeline = build_gpa_pipeline()
    if evaluation["models"]["gpa_regressor"]["status"] == "EVALUATED":
        parsed_gpa = df["actual_gpa"].apply(parse_gpa_label)
        valid_gpa = parsed_gpa.notna().to_numpy()
        ridge_pipeline.fit(features[valid_gpa], parsed_gpa[valid_gpa].astype(float).to_numpy())
        gpa_mode = "genuine_labels"
    else:
        ridge_train_x = np.vstack([ANCHOR_SAMPLES, features[finite_mask]]) if finite_mask.any() else ANCHOR_SAMPLES
        ridge_train_y = np.concatenate([ANCHOR_GPA_TARGETS, weak_gpa[finite_mask]]) if finite_mask.any() else ANCHOR_GPA_TARGETS
        ridge_pipeline.fit(ridge_train_x, ridge_train_y)
        gpa_mode = "synthetic_anchor_and_heuristic_fallback"
    predicted_gpas = np.clip(ridge_pipeline.predict(features), 0.0, 4.0)

    iso_pipeline = build_anomaly_pipeline(contamination=0.12, random_state=rs)
    if len(features) >= 8:
        iso_preds = iso_pipeline.fit_predict(features)
    else:
        iso_pipeline.fit(np.vstack([ANCHOR_SAMPLES, features]))
        iso_preds = iso_pipeline.predict(features)

    imputed_features = rf_pipeline.named_steps["imputer"].transform(features)
    now = datetime.now(timezone.utc)
    pred_ops, notif_ops, pred_docs = [], [], []
    counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    anomaly_count = 0

    high_t, med_t = cfg["high_risk_threshold"] / 100.0, cfg["medium_risk_threshold"] / 100.0
    drop_lim, min_att = float(cfg["anomaly_drop_pct"]), float(cfg["min_attendance_pct"])
    for idx, row in enumerate(df.to_dict(orient="records")):
        sid = row["student_id"]
        att, marks, assign, lms, gpa = [float(imputed_features[idx, col_i]) for col_i in range(5)]
        risk_score = round(float(risk_probs[idx]), 4)
        pred_gpa = round(float(predicted_gpas[idx]), 2)
        risk_level = classify_dropout_risk(risk_score, high_t, med_t)
        anomaly_reason = _build_anomaly_reason(att, marks, gpa, int(iso_preds[idx]), drop_limit=drop_lim)
        is_anomaly = bool(anomaly_reason)
        recommendation = _build_recommendation(risk_level, is_anomaly, att, marks, assign, lms, min_att=min_att)

        counts[risk_level] += 1
        if is_anomaly:
            anomaly_count += 1

        pred_doc = {
            "student_id": sid, "predicted_gpa": pred_gpa, "dropout_risk_score": risk_score,
            "risk_level": risk_level, "is_anomaly": is_anomaly, "anomaly_reason": anomaly_reason,
            "recommendation": recommendation, "model_version": MODEL_VERSION, "generated_at": now,
        }
        pred_docs.append(pred_doc)
        pred_ops.append(UpdateOne({"student_id": sid}, {"$set": pred_doc}, upsert=True))

        if risk_level == "HIGH" or is_anomaly:
            severity = "DANGER" if risk_level == "HIGH" else "WARNING"
            title = f"High Dropout Risk: {sid}" if risk_level == "HIGH" else f"Academic Anomaly Flagged: {sid}"
            detail = anomaly_reason if anomaly_reason else f"Dropout risk score {round(risk_score * 100)}%"
            targets = ([("TEACHER", sid)] if cfg["auto_teacher_alerts"] else []) + ([("STUDENT", sid)] if cfg["auto_student_alerts"] else [])
            for target_role, target_uid in targets:
                notif_ops.append(UpdateOne(
                    {"target_role": target_role, "target_user_id": target_uid, "is_read": False},
                    {"$set": {
                        "target_role": target_role, "target_user_id": target_uid, "title": title,
                        "message": f"{row['full_name']} ({row['course_code']}): {detail}.",
                        "severity": severity, "is_read": False, "created_at": now,
                    }},
                    upsert=True,
                ))

    if persist:
        preds_col = predictions_col()
        for start in range(0, len(pred_ops), 500):
            preds_col.bulk_write(pred_ops[start:start + 500], ordered=False)
        if notif_ops:
            notifs_col = notifications_col()
            for start in range(0, len(notif_ops), 500):
                notifs_col.bulk_write(notif_ops[start:start + 500], ordered=False)
        invalidate_cache()

    result = {
        "status": "COMPLETED", "model_version": MODEL_VERSION, "predictions_generated": len(pred_docs),
        "high_risk_count": counts["HIGH"], "medium_risk_count": counts["MEDIUM"],
        "low_risk_count": counts["LOW"], "anomalies_count": anomaly_count,
        "course_demand": compute_course_demand(df), "applied_settings": cfg,
        "training_modes": {
            "dropout_classifier": dropout_mode, "gpa_regressor": gpa_mode,
            "anomaly_detector": "unsupervised_isolation_forest",
        },
        "evaluation": evaluation,
    }
    if not persist:
        result["predictions"] = pred_docs
    return result
