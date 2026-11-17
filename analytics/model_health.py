from pymongo import DESCENDING
import pandas as pd
from analytics.ml_engine import FEATURE_COLUMNS, compute_course_demand
from core.db import datasets_log_col, get_cached, predictions_col, student_records_col


def _safe_float(val, default=0.0):
    try:
        return float(val)
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
    for p in preds:
        sid = str(p.get("student_id") or "").strip()
        if not sid:
            continue
        pred_map[sid] = p
        gen = p.get("generated_at")
        if hasattr(gen, "strftime") and (latest_generated is None or gen > latest_generated):
            latest_generated = gen
    model_version = str(preds[-1].get("model_version") or "untrained") if preds else "untrained"

    total_records = len(record_map)
    coverage = round(len(pred_map) / total_records * 100.0, 1) if total_records else 0.0

    risk_counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
    anomaly_count = 0
    errors = []
    for sid, p in pred_map.items():
        level = str(p.get("risk_level") or "").upper()
        if level in risk_counts:
            risk_counts[level] += 1
        if p.get("is_anomaly"):
            anomaly_count += 1
        prev = record_map.get(sid, {}).get("previous_gpa")
        if prev is not None and p.get("predicted_gpa") is not None:
            errors.append(abs(_safe_float(p["predicted_gpa"]) - _safe_float(prev)))

    total_preds = len(pred_map)
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

    low_att_total, low_att_flagged = 0, 0
    for sid, rec in record_map.items():
        att = _safe_float(rec.get("attendance_pct"), 100.0)
        if att >= 75.0:
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

    return {
        "kpis": {
            "total_predictions": total_preds,
            "coverage_pct": coverage,
            "anomaly_count": anomaly_count,
            "anomaly_rate": anomaly_rate,
            "gpa_mae": mae,
            "stable_share": stable_share,
            "risk_agreement": risk_agreement,
            "low_att_total": low_att_total,
        },
        "model_info": {
            "version": model_version,
            "generated": latest_generated.strftime("%Y-%m-%d %H:%M") if hasattr(latest_generated, "strftime") else "Never",
            "features": list(FEATURE_COLUMNS),
        },
        "risk_counts": risk_counts,
        "error_buckets": buckets,
        "demand": demand,
        "uploads": {"count": upload_count, "rows_processed": rows_processed},
    }


def get_model_health_context():
    return get_cached("analyst:model_health", _load_model_health, ttl=45.0)


def get_analyst_accuracy_page_context():
    data = {
        "kpis": {"total_predictions": 0, "coverage_pct": 0.0, "anomaly_count": 0, "anomaly_rate": 0.0,
                 "gpa_mae": None, "stable_share": None, "risk_agreement": None, "low_att_total": 0},
        "model_info": {"version": "untrained", "generated": "Never", "features": []},
        "risk_counts": {"LOW": 0, "MEDIUM": 0, "HIGH": 0},
        "error_buckets": {"excellent": 0, "acceptable": 0, "large": 0},
        "demand": [],
        "uploads": {"count": 0, "rows_processed": 0},
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

    display = {
        "gpa_mae": f"{data['kpis']['gpa_mae']:.2f}" if data['kpis']['gpa_mae'] is not None else "N/A",
        "stable_share": f"{data['kpis']['stable_share']:.1f}%" if data['kpis']['stable_share'] is not None else "N/A",
        "risk_agreement": f"{data['kpis']['risk_agreement']:.1f}%" if data['kpis']['risk_agreement'] is not None else "N/A",
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
        "chart_data": data,
        "display": display,
        "db_error": db_error,
    }
