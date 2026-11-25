import math
from pymongo import DESCENDING
import pandas as pd
from analytics.ml_engine import FEATURE_COLUMNS, _resolve_runtime_settings, compute_course_demand
from analytics.preprocessing import parse_gpa_label
from core.db import datasets_log_col, get_cached, predictions_col, student_records_col


def _safe_float(val, default=0.0):
    try:
        num = float(val)
        return num if math.isfinite(num) else default
    except (TypeError, ValueError):
        return default


def _load_model_health():
    records = list(student_records_col().find({}, {"_id": 0}))
    preds = list(predictions_col().find({}, {"_id": 0}))
    record_map = {}
    for rec in records:
        sid = str(rec.get("student_id") or "").strip()
        if sid:
            record_map[sid] = rec
    pred_map = {}
    latest_generated = None
    model_version = "untrained"
    for p in preds:
        sid = str(p.get("student_id") or "").strip()
        if not sid or sid not in record_map:
            continue
        gen = p.get("generated_at")
        prev_pred = pred_map.get(sid)
        prev_gen = prev_pred.get("generated_at") if prev_pred else None
        if prev_pred is None or (hasattr(gen, "strftime") and (not hasattr(prev_gen, "strftime") or gen >= prev_gen)):
            pred_map[sid] = p
        if hasattr(gen, "strftime") and (latest_generated is None or gen >= latest_generated):
            latest_generated = gen
            model_version = str(p.get("model_version") or "untrained")
    if model_version == "untrained" and pred_map:
        last_pred = next(reversed(pred_map.values()))
        model_version = str(last_pred.get("model_version") or "untrained")

    total_records = len(record_map)
    total_preds = len(pred_map)
    coverage = min(100.0, round(total_preds / total_records * 100.0, 1)) if total_records else 0.0

    genuine_gpa_labels = sum(
        1 for rec in record_map.values() if parse_gpa_label(rec.get("actual_gpa")) is not None
    )
    use_actual = genuine_gpa_labels > 0

    risk_counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
    anomaly_count = 0
    errors = []
    for sid, p in pred_map.items():
        level = str(p.get("risk_level") or "").upper()
        if level in risk_counts:
            risk_counts[level] += 1
        if p.get("is_anomaly"):
            anomaly_count += 1
        rec = record_map.get(sid, {})
        target_val = parse_gpa_label(rec.get("actual_gpa")) if use_actual else rec.get("previous_gpa")
        if target_val is not None and p.get("predicted_gpa") is not None:
            errors.append(abs(_safe_float(p["predicted_gpa"]) - _safe_float(target_val)))

    gpa_metric_mode = "genuine" if use_actual else "proxy_previous_gpa"
    gpa_metric_note = (
        f"Verified MAE across {len(errors)} genuine actual_gpa labels."
        if use_actual
        else "0 genuine actual_gpa labels: MAE & Stable Share compare Predicted vs Previous GPA as a proxy drift check, while Model Evaluation hides real-world test scores."
    )
    mae = round(sum(errors) / len(errors), 3) if errors else None
    stable_share = round(sum(1 for e in errors if e <= 0.25) / len(errors) * 100.0, 1) if errors else None

    buckets = {"excellent": 0, "acceptable": 0, "large": 0}
    for e in errors:
        if e <= 0.25:
            buckets["excellent"] += 1
        elif e <= 0.50:
            buckets["acceptable"] += 1
        else:
            buckets["large"] += 1

    portal_settings = _resolve_runtime_settings(persist=True)
    min_att = float(portal_settings.get("min_attendance_pct", 75))
    low_att_total, low_att_flagged = 0, 0
    for sid, rec in record_map.items():
        att = _safe_float(rec.get("attendance_pct"), 100.0)
        if att >= min_att:
            continue
        p = pred_map.get(sid)
        if not p:
            continue
        low_att_total += 1
        if str(p.get("risk_level") or "").upper() in ("MEDIUM", "HIGH"):
            low_att_flagged += 1
    risk_agreement = round(low_att_flagged / low_att_total * 100.0, 1) if low_att_total else None

    upload_count = int(datasets_log_col().count_documents({}))
    rows_processed = 0
    for log in datasets_log_col().find({}, {"_id": 0, "rows_processed": 1}):
        rows_processed += int(log.get("rows_processed") or 0)

    anomaly_rate = round(anomaly_count / total_preds * 100.0, 1) if total_preds else 0.0
    demand = compute_course_demand(pd.DataFrame(records)) if records else []
    course_stats = {}
    for rec in records:
        code = str(rec.get("course_code") or "").strip().upper()
        if not code:
            continue
        bucket = course_stats.setdefault(code, {"att": 0.0, "marks": 0.0, "count": 0})
        bucket["att"] += max(0.0, min(100.0, _safe_float(rec.get("attendance_pct"))))
        bucket["marks"] += max(0.0, min(100.0, _safe_float(rec.get("internal_marks"))))
        bucket["count"] += 1
    if len(course_stats) >= 2:
        c_labels, c_values, c_att, c_marks = [], [], [], []
        for code in sorted(course_stats):
            bucket = course_stats[code]
            avg_att = round(bucket["att"] / bucket["count"], 1)
            avg_marks = round(bucket["marks"] / bucket["count"], 1)
            c_labels.append(code)
            c_att.append(avg_att)
            c_marks.append(avg_marks)
            c_values.append(round((avg_att + avg_marks) / 2.0, 1))
        contour_series = {"labels": c_labels, "values": c_values, "attendance": c_att, "marks": c_marks}
    else:
        contour_series = {"labels": [], "values": []}

    return {
        "kpis": {
            "total_students": total_records,
            "total_predictions": total_preds,
            "coverage_pct": coverage,
            "anomaly_count": anomaly_count,
            "anomaly_rate": anomaly_rate,
            "gpa_mae": mae,
            "stable_share": stable_share,
            "risk_agreement": risk_agreement,
            "low_att_total": low_att_total,
            "genuine_gpa_labels": genuine_gpa_labels,
            "gpa_metric_mode": gpa_metric_mode,
            "gpa_metric_note": gpa_metric_note,
        },
        "model_info": {
            "version": model_version,
            "generated": latest_generated.strftime("%Y-%m-%d %H:%M") if hasattr(latest_generated, "strftime") else "Never",
            "features": list(FEATURE_COLUMNS),
        },
        "risk_counts": risk_counts,
        "error_buckets": buckets,
        "demand": demand,
        "contour_series": contour_series,
        "uploads": {"count": upload_count, "rows_processed": rows_processed},
        "portal_settings": portal_settings,
    }


def get_model_health_context():
    return get_cached("analyst:model_health", _load_model_health, ttl=45.0)


def get_analyst_accuracy_page_context():
    data = {
        "kpis": {
            "total_students": 0, "total_predictions": 0, "coverage_pct": 0.0, "anomaly_count": 0,
            "anomaly_rate": 0.0, "gpa_mae": None, "stable_share": None, "risk_agreement": None,
            "low_att_total": 0, "genuine_gpa_labels": 0, "gpa_metric_mode": "proxy_previous_gpa",
            "gpa_metric_note": "0 genuine actual_gpa labels: MAE & Stable Share compare Predicted vs Previous GPA as a proxy drift check, while Model Evaluation hides real-world test scores.",
        },
        "model_info": {"version": "untrained", "generated": "Never", "features": []},
        "risk_counts": {"LOW": 0, "MEDIUM": 0, "HIGH": 0},
        "error_buckets": {"excellent": 0, "acceptable": 0, "large": 0},
        "demand": [],
        "contour_series": {"labels": [], "values": []},
        "uploads": {"count": 0, "rows_processed": 0},
        "portal_settings": _resolve_runtime_settings(persist=False),
    }
    try:
        data = get_model_health_context()
        db_error = None
    except Exception as exc:
        db_error = str(exc)

    demand_rows = []
    for d in data["demand"]:
        growth = d.get("growth_pct") or 0.0
        demand_rows.append([
            d["course_code"], d["current_enrolled"], d["projected_demand"],
            {"text": f"{growth:+.1f}%", "status": "success" if growth >= 0 else "warning"},
        ])

    use_actual = data["kpis"].get("genuine_gpa_labels", 0) > 0
    display = {
        "gpa_mae": f"{data['kpis']['gpa_mae']:.2f}" if data['kpis']['gpa_mae'] is not None else "N/A",
        "stable_share": f"{data['kpis']['stable_share']:.1f}%" if data['kpis']['stable_share'] is not None else "N/A",
        "risk_agreement": f"{data['kpis']['risk_agreement']:.1f}%" if data['kpis']['risk_agreement'] is not None else "N/A",
        "gpa_mae_title": "GPA Error (MAE)" if use_actual else "GPA Drift (Proxy MAE)",
        "gpa_mae_badge": "Verified vs actual GPA" if use_actual else "Proxy: Pred vs Prev GPA (0 labels)",
        "accuracy_note": data["kpis"].get("gpa_metric_note") or "",
    }
    return {
        "kpis": data["kpis"],
        "model_info": data["model_info"],
        "risk_counts": data["risk_counts"],
        "error_buckets": data["error_buckets"],
        "demand_headers": ["Course", "Joined Now", "Next Term Need", "Change"],
        "demand_rows": demand_rows,
        "upload_headers": ["Uploads", "Rows Processed", "Model Version", "Last Run"],
        "upload_rows": [[
            data["uploads"]["count"], data["uploads"]["rows_processed"],
            data["model_info"]["version"], data["model_info"]["generated"],
        ]],
        "total_uploads_count": data["uploads"]["count"],
        "accuracy_note": display["accuracy_note"],
        "chart_data": data,
        "display": display,
        "portal_settings": data.get("portal_settings") or _resolve_runtime_settings(persist=False),
        "db_error": db_error,
    }
