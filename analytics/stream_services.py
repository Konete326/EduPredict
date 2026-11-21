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
                "course_code": str(rec.get("course_code") or "CS-101").upper(),
                "event_type": event_type,
                "attendance_pct": new_att,
                "attendance": new_att,
                "internal_marks": new_marks,
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
    if events:
        try:
            sids = [ev["student_id"] for ev in events]
            pred_map = {
                str(p.get("student_id") or ""): p
                for p in predictions_col().find({"student_id": {"$in": sids}}, {"_id": 0, "student_id": 1, "risk_level": 1, "is_anomaly": 1})
            }
            for ev in events:
                pred = pred_map.get(ev["student_id"])
                if pred:
                    ev["risk_level"] = str(pred.get("risk_level") or ev["risk_level"]).upper()
                    ev["is_anomaly"] = bool(pred.get("is_anomaly", ev["is_anomaly"]))
        except Exception:
            pass

    invalidate_cache()
    preds_gen = ml_res.get("predictions_generated", 0)
    return {
        "ok": True,
        "status": "COMPLETED",
        "events_pushed": len(events),
        "events": events,
        "predictions_generated": preds_gen,
        "high_risk_count": ml_res.get("high_risk_count", 0),
        "anomalies_count": ml_res.get("anomalies_count", 0),
        "message": f"Streamed {len(events)} live LMS events and refreshed {preds_gen} predictions.",
    }
