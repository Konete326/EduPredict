from datetime import datetime, timezone
from analytics.data_pipeline import ingest_dataset
from analytics.ml_engine import run_prediction_pipeline
from core.db import datasets_log_col, invalidate_cache, predictions_col, student_records_col


def _safe_float(val, default=0.0):
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _fetch_student_pool(records_col, limit=6):
    cursor = records_col.find({}, {"_id": 0})
    if hasattr(cursor, "sort"):
        cursor = cursor.sort("student_id", 1)
    if hasattr(cursor, "limit"):
        cursor = cursor.limit(limit)
    return list(cursor)[:limit]


def _build_stream_metrics(records_col, pred_map):
    risk_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2, "PENDING": 3}
    rows, gpas = [], []
    records = list(records_col.find({}, {"_id": 0, "student_id": 1, "full_name": 1, "attendance_pct": 1, "previous_gpa": 1}))
    for rec in records:
        sid = str(rec.get("student_id") or "").strip()
        if not sid:
            continue
        pred = pred_map.get(sid) or {}
        risk_level = str(pred.get("risk_level") or "PENDING").strip().upper()
        raw_pred_gpa = pred.get("predicted_gpa")
        parsed_gpa = _safe_float(raw_pred_gpa, None) if raw_pred_gpa is not None else None
        if parsed_gpa is not None:
            pred_gpa = parsed_gpa
            gpas.append(pred_gpa)
        else:
            pred_gpa = _safe_float(rec.get("previous_gpa"), 0.0)
        att = _safe_float(rec.get("attendance_pct"), 0.0)
        full_name = str(rec.get("full_name") or sid)
        rows.append((
            risk_order.get(risk_level, 4),
            -_safe_float(pred.get("dropout_risk_score"), 0.0),
            {"x": round(att, 1), "y": round(pred_gpa, 2), "label": f"{sid} ({full_name})", "risk": risk_level},
        ))
    rows.sort(key=lambda item: (item[0], item[1]))
    avg_predicted_gpa = f"{(sum(gpas) / len(gpas)):.2f}" if gpas else "0.00"
    return avg_predicted_gpa, [item[2] for item in rows[:60]]


def simulate_lms_stream_tick(uploaded_by="Analyst"):
    records_col = student_records_col()
    if records_col.count_documents({}) == 0:
        ingest_dataset(mode="sample", uploaded_by=uploaded_by)

    pool = _fetch_student_pool(records_col, limit=6)
    now = datetime.now(timezone.utc)
    events = []

    if pool:
        dip_rec = max(pool, key=lambda r: _safe_float(r.get("attendance_pct"), 0.0))
        dip_sid = str(dip_rec.get("student_id") or "").strip()
        boost_recs = [r for r in pool if str(r.get("student_id") or "").strip() != dip_sid][:2]
        selected = [(dip_rec, True)] + [(rec, False) for rec in boost_recs]

        for rec, is_dip in selected:
            sid = str(rec.get("student_id") or "").strip()
            if not sid:
                continue
            att = _safe_float(rec.get("attendance_pct"), 80.0)
            marks = _safe_float(rec.get("internal_marks"), 70.0)
            lms = _safe_float(rec.get("lms_hours_weekly"), 8.0)
            if is_dip:
                new_att = round(max(0.0, min(55.0, att - 25.0)) if att > 55.0 else max(0.0, att - 8.0), 2)
                new_marks = round(max(0.0, min(44.0, marks - 25.0)) if marks > 44.0 else max(0.0, marks - 6.0), 2)
                new_lms = round(max(0.0, min(168.0, lms - 3.5)), 2)
                event_type = "RISK_DIP"
            else:
                new_att = round(max(0.0, min(100.0, att + 2.0)), 2)
                new_marks = round(max(0.0, min(100.0, marks)), 2)
                new_lms = round(max(0.0, min(168.0, lms + 1.5)), 2)
                event_type = "LMS_ENGAGEMENT"

            records_col.update_one(
                {"student_id": sid},
                {"$set": {"attendance_pct": new_att, "internal_marks": new_marks, "lms_hours_weekly": new_lms, "updated_at": now}},
            )
            events.append({
                "student_id": sid,
                "full_name": str(rec.get("full_name") or sid),
                "batch": str(rec.get("batch") or "2026-A").strip() or "2026-A",
                "course_code": str(rec.get("course_code") or "CS-101").upper(),
                "event_type": event_type,
                "attendance_pct": new_att,
                "attendance": new_att,
                "internal_marks": new_marks,
                "previous_gpa": round(_safe_float(rec.get("previous_gpa"), 3.0), 2),
                "lms_hours_weekly": new_lms,
                "risk_level": "HIGH" if is_dip else "LOW",
                "is_anomaly": is_dip,
            })

    datasets_log_col().insert_one({
        "filename": "live_lms_stream_tick",
        "uploaded_by": uploaded_by or "Analyst",
        "mode": "STREAM_TICK",
        "event_type": "STREAM_TICK",
        "rows_processed": len(events),
        "missing_values_fixed": 0,
        "status": "COMPLETED",
        "uploaded_at": now,
    })

    ml_res = run_prediction_pipeline()
    pred_map = {}
    try:
        pred_map = {
            str(p.get("student_id") or "").strip(): p
            for p in predictions_col().find(
                {},
                {
                    "_id": 0, "student_id": 1, "predicted_gpa": 1, "risk_level": 1,
                    "is_anomaly": 1, "dropout_risk_score": 1, "anomaly_reason": 1, "recommendation": 1,
                },
            )
            if str(p.get("student_id") or "").strip()
        }
    except Exception:
        pred_map = {}
    for ev in events:
        pred = pred_map.get(ev["student_id"])
        if pred:
            ev["risk_level"] = str(pred.get("risk_level") or ev["risk_level"]).upper()
            ev["is_anomaly"] = bool(pred.get("is_anomaly", ev["is_anomaly"]))
        ev["predicted_gpa"] = round(_safe_float(pred.get("predicted_gpa")), 2) if (pred and pred.get("predicted_gpa") is not None) else None
        ev["dropout_risk_score"] = round(_safe_float(pred.get("dropout_risk_score")), 4) if (pred and pred.get("dropout_risk_score") is not None) else None
        ev["risk_text"] = f"{ev['risk_level']} ({int(round(_safe_float(pred.get('dropout_risk_score')) * 100))}%)" if (pred and pred.get("dropout_risk_score") is not None) else ev["risk_level"]
        ev["tip"] = (str(pred.get("anomaly_reason") or "").strip() if (ev["is_anomaly"] and str(pred.get("anomaly_reason") or "").strip()) else str(pred.get("recommendation") or "")) if pred else ""
    try:
        avg_predicted_gpa, scatter_points = _build_stream_metrics(records_col, pred_map)
    except Exception:
        avg_predicted_gpa, scatter_points = "0.00", []

    invalidate_cache()
    preds_gen = ml_res.get("predictions_generated", 0)
    low_cnt, med_cnt, high_cnt = ml_res.get("low_risk_count", 0), ml_res.get("medium_risk_count", 0), ml_res.get("high_risk_count", 0)
    return {
        "ok": True, "status": "COMPLETED", "events_pushed": len(events), "events": events,
        "predictions_generated": preds_gen, "low_risk_count": low_cnt,
        "medium_risk_count": med_cnt, "high_risk_count": high_cnt,
        "anomalies_count": ml_res.get("anomalies_count", 0),
        "avg_predicted_gpa": avg_predicted_gpa, "scatter_points": scatter_points,
        "dropout_counts": {"LOW": low_cnt, "MEDIUM": med_cnt, "HIGH": high_cnt},
        "course_demand": ml_res.get("course_demand", []),
        "dataset_log": {
            "filename": "live_lms_stream_tick",
            "uploaded_by": uploaded_by or "Analyst",
            "mode": "STREAM_TICK",
            "rows_processed": len(events),
            "missing_values_fixed": 0,
            "status": "COMPLETED",
            "uploaded_at": now.strftime("%Y-%m-%d %H:%M"),
        },
        "message": f"Streamed {len(events)} live LMS events and refreshed {preds_gen} predictions.",
    }
