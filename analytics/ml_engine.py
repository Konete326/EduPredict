from datetime import datetime, timezone
import numpy as np
import pandas as pd
from pymongo import UpdateOne
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.linear_model import Ridge
from core.db import notifications_col, predictions_col, student_records_col

MODEL_VERSION = "sklearn-rf-ridge-if-v1.0"
FEATURE_COLUMNS = (
    "attendance_pct", "internal_marks", "assignment_score",
    "lms_hours_weekly", "previous_gpa",
)
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


def classify_dropout_risk(score):
    if score >= 0.70:
        return "HIGH"
    if score >= 0.35:
        return "MEDIUM"
    return "LOW"


def compute_course_demand(df):
    if df is None or df.empty or "course_code" not in df.columns:
        return []
    work = df.copy()
    work["previous_gpa"] = pd.to_numeric(work.get("previous_gpa"), errors="coerce").fillna(3.0)
    work["attendance_pct"] = pd.to_numeric(work.get("attendance_pct"), errors="coerce").fillna(80.0)
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
    df = pd.DataFrame(records)
    defaults = {
        "attendance_pct": 80.0, "internal_marks": 70.0,
        "assignment_score": 75.0, "lms_hours_weekly": 8.0, "previous_gpa": 3.0,
    }
    for col, fallback in defaults.items():
        if col not in df.columns:
            df[col] = fallback
        df[col] = pd.to_numeric(df[col], errors="coerce")
        median_val = df[col].median()
        df[col] = df[col].fillna(float(median_val) if pd.notna(median_val) else fallback)
    df["course_code"] = (
        df.get("course_code", pd.Series("CS-101", index=df.index))
        .fillna("CS-101").astype(str).str.strip().str.upper()
    )
    df["full_name"] = (
        df.get("full_name", pd.Series("Student", index=df.index))
        .fillna("Student").astype(str).str.strip()
    )
    df["student_id"] = df["student_id"].astype(str).str.strip()
    return df


def _derive_weak_targets(features):
    att, marks, assign, lms, gpa = [features[:, i] for i in range(5)]
    risk_signal = (
        0.38 * (1.0 - att / 100.0)
        + 0.28 * (1.0 - marks / 100.0)
        + 0.14 * (1.0 - assign / 100.0)
        + 0.10 * np.clip(1.0 - lms / 15.0, 0.0, 1.0)
        + 0.10 * (1.0 - gpa / 4.0)
    )
    confident_mask = (risk_signal >= 0.48) | (risk_signal <= 0.24)
    risk_labels = (risk_signal >= 0.48).astype(int)
    gpa_targets = np.clip(
        0.45 * gpa + 0.30 * (marks / 25.0) + 0.15 * (assign / 25.0) + 0.10 * (att / 25.0),
        0.0, 4.0,
    )
    return confident_mask, risk_labels, gpa_targets


def _build_anomaly_reason(att, marks, gpa, iso_flag):
    reasons = []
    if att < 60.0:
        reasons.append("Attendance below 60%")
    if marks < 45.0:
        reasons.append("Internal marks below 45%")
    if (gpa * 25.0 - marks) > 25.0:
        reasons.append("Sudden >25% score drop vs previous GPA")
    if iso_flag == -1 and not reasons:
        reasons.append("Outlier pattern flagged by Isolation Forest")
    return "; ".join(reasons)


def _build_recommendation(risk_level, is_anomaly, att, marks, assign, lms):
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
        if att < 75.0:
            return "Attend the next 4 consecutive lectures to lift attendance above 80%."
        if marks < 65.0 or assign < 65.0:
            return "Focus on upcoming internal quizzes and assignment submissions to boost GPA."
        if lms < 7.0:
            return "Increase weekly LMS study hours above 8 hrs/week for steady progress."
        return "Maintain consistent study schedule and monitor upcoming quiz scores."
    return "Strong academic trajectory. Keep up regular attendance and LMS engagement."


def run_prediction_pipeline(records=None):
    raw_records = list(student_records_col().find({}, {"_id": 0})) if records is None else list(records)
    if not raw_records:
        return {
            "status": "EMPTY", "model_version": MODEL_VERSION, "predictions_generated": 0,
            "high_risk_count": 0, "medium_risk_count": 0, "low_risk_count": 0,
            "anomalies_count": 0, "course_demand": [],
        }

    df = _prepare_dataframe(raw_records)
    features = df[list(FEATURE_COLUMNS)].to_numpy(dtype=float)
    confident_mask, weak_risk, weak_gpa = _derive_weak_targets(features)
    rf_train_x = np.vstack([ANCHOR_SAMPLES, features[confident_mask]]) if confident_mask.any() else ANCHOR_SAMPLES
    rf_train_y = np.concatenate([ANCHOR_RISK_LABELS, weak_risk[confident_mask]]) if confident_mask.any() else ANCHOR_RISK_LABELS
    ridge_train_x = np.vstack([ANCHOR_SAMPLES, features])
    ridge_train_y = np.concatenate([ANCHOR_GPA_TARGETS, weak_gpa])

    rf_model = RandomForestClassifier(
        n_estimators=50, max_depth=4, min_samples_leaf=2, random_state=42,
    )
    rf_model.fit(rf_train_x, rf_train_y)
    risk_probs = np.clip(rf_model.predict_proba(features)[:, 1], 0.0, 1.0)

    ridge_model = Ridge(alpha=1.0)
    ridge_model.fit(ridge_train_x, ridge_train_y)
    predicted_gpas = np.clip(ridge_model.predict(features), 0.0, 4.0)

    iso_model = IsolationForest(contamination=0.12, random_state=42)
    if len(features) >= 8:
        iso_preds = iso_model.fit_predict(features)
    else:
        iso_model.fit(ridge_train_x)
        iso_preds = iso_model.predict(features)

    now = datetime.now(timezone.utc)
    pred_ops, notif_ops = [], []
    counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    anomaly_count = 0

    for idx, row in enumerate(df.to_dict(orient="records")):
        sid = row["student_id"]
        att, marks = float(row["attendance_pct"]), float(row["internal_marks"])
        assign, lms = float(row["assignment_score"]), float(row["lms_hours_weekly"])
        gpa = float(row["previous_gpa"])

        risk_score = round(float(risk_probs[idx]), 4)
        pred_gpa = round(float(predicted_gpas[idx]), 2)
        risk_level = classify_dropout_risk(risk_score)
        anomaly_reason = _build_anomaly_reason(att, marks, gpa, int(iso_preds[idx]))
        is_anomaly = bool(anomaly_reason)
        recommendation = _build_recommendation(risk_level, is_anomaly, att, marks, assign, lms)

        counts[risk_level] += 1
        if is_anomaly:
            anomaly_count += 1

        pred_ops.append(UpdateOne({"student_id": sid}, {"$set": {
            "student_id": sid, "predicted_gpa": pred_gpa, "dropout_risk_score": risk_score,
            "risk_level": risk_level, "is_anomaly": is_anomaly, "anomaly_reason": anomaly_reason,
            "recommendation": recommendation, "model_version": MODEL_VERSION, "generated_at": now,
        }}, upsert=True))

        if risk_level == "HIGH" or is_anomaly:
            severity = "DANGER" if risk_level == "HIGH" else "WARNING"
            title = f"High Dropout Risk: {sid}" if risk_level == "HIGH" else f"Academic Anomaly Flagged: {sid}"
            detail = anomaly_reason if anomaly_reason else f"Dropout risk score {round(risk_score * 100)}%"
            notif_ops.append(UpdateOne(
                {"target_role": "TEACHER", "target_user_id": sid, "is_read": False},
                {"$set": {
                    "target_role": "TEACHER", "target_user_id": sid, "title": title,
                    "message": f"{row['full_name']} ({row['course_code']}): {detail}.",
                    "severity": severity, "is_read": False, "created_at": now,
                }},
                upsert=True,
            ))

    preds_col = predictions_col()
    for start in range(0, len(pred_ops), 500):
        preds_col.bulk_write(pred_ops[start:start + 500], ordered=False)
    if notif_ops:
        notifs_col = notifications_col()
        for start in range(0, len(notif_ops), 500):
            notifs_col.bulk_write(notif_ops[start:start + 500], ordered=False)

    return {
        "status": "COMPLETED",
        "model_version": MODEL_VERSION,
        "predictions_generated": len(pred_ops),
        "high_risk_count": counts["HIGH"],
        "medium_risk_count": counts["MEDIUM"],
        "low_risk_count": counts["LOW"],
        "anomalies_count": anomaly_count,
        "course_demand": compute_course_demand(df),
    }
