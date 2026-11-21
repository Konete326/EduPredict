from datetime import datetime, timezone
from pymongo import DESCENDING
from core.db import invalidate_cache, notifications_col, predictions_col, student_records_col, users_col
from panels.admin_audit_services import record_audit_log
from panels.notification_services import create_notification


def _safe_float(val, default=0.0):
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _initials(name, fallback="S"):
    parts = [p[0] for p in str(name or "").split() if p]
    return "".join(parts[:2]).upper() or fallback


def _format_alert(doc):
    created = doc.get("created_at")
    created_str = created.strftime("%Y-%m-%d %H:%M") if hasattr(created, "strftime") else (str(created) if created else "-")
    return {
        "title": str(doc.get("title") or "Notice"),
        "message": str(doc.get("message") or ""),
        "severity": str(doc.get("severity") or "INFO").upper(),
        "created": created_str,
        "is_read": bool(doc.get("is_read")),
    }


def _build_risk_reasons(records, avg_att, avg_marks, prev_gpa, pred_gpa, risk_score, risk_level, anomaly_reason, recommendation):
    if not records:
        return [
            "No academic course records have been uploaded yet for this student.",
            "Attendance and marks risk insights will populate once records are ingested.",
        ]
    reasons = []
    if avg_att < 60.0:
        reasons.append(f"Critical attendance at {avg_att:.1f}% (below 60% minimum threshold).")
    elif avg_att < 75.0:
        reasons.append(f"Attendance is {avg_att:.1f}%, below the 75% target.")
    else:
        reasons.append(f"Strong attendance at {avg_att:.1f}% across enrolled courses.")

    if avg_marks < 50.0:
        reasons.append(f"Low internal marks averaging {avg_marks:.1f}/100.")
    elif avg_marks < 65.0:
        reasons.append(f"Internal marks average {avg_marks:.1f}/100 with room for improvement.")
    else:
        reasons.append(f"Solid internal assessment average of {avg_marks:.1f}/100.")

    if anomaly_reason:
        reasons.append(f"Anomaly flagged: {anomaly_reason}.")
    elif pred_gpa is not None:
        if pred_gpa < prev_gpa - 0.2:
            reasons.append(f"Predicted GPA ({pred_gpa:.2f}) trails previous GPA ({prev_gpa:.2f}).")
        else:
            reasons.append(f"Predicted GPA is {pred_gpa:.2f} compared to previous {prev_gpa:.2f}.")
    elif risk_score is not None:
        reasons.append(f"ML dropout risk score estimated at {round(risk_score * 100)}% ({risk_level}).")

    if len(reasons) < 4 and recommendation:
        reasons.append(recommendation)
    elif len(reasons) < 4 and risk_score is not None and not any("dropout risk" in r.lower() for r in reasons):
        reasons.append(f"ML model classified risk as {risk_level} ({round(risk_score * 100)}%).")
    return reasons[:4]


def reject_teacher_account(user_id, reason, actor_user_id=None, actor_email="", actor_name="System Admin"):
    clean_uid, clean_reason = str(user_id or "").strip(), str(reason or "").strip()
    if len(clean_reason) < 3:
        return False, "Please provide a clear rejection reason."
    col = users_col()
    existing = col.find_one({"user_id": clean_uid})
    if existing is None:
        return False, "User record not found."
    clean_actor_id = str(actor_user_id or "").strip()
    clean_actor_email = str(actor_email or "").strip().lower()
    target_email = str(existing.get("email") or "").strip().lower()
    if (clean_actor_id and clean_uid == clean_actor_id) or (clean_actor_email and target_email == clean_actor_email):
        return False, "You cannot reject your own active admin account."
    clean_actor = str(actor_name or "System Admin").strip() or "System Admin"
    col.update_one({"user_id": clean_uid}, {"$set": {"is_active": False, "approval_status": "REJECTED", "rejection_reason": clean_reason, "rejected_by": clean_actor, "rejected_at": datetime.now(timezone.utc)}})
    try:
        record_audit_log(clean_actor, "ADMIN", "USERS", "REJECT_USER", f"Rejected teacher account {clean_uid}: {clean_reason}", severity="DANGER", source="SYSTEM")
    except Exception:
        pass
    create_notification("Teacher Application Rejected", f"Your teacher registration was rejected by Admin. Reason: {clean_reason}", severity="DANGER", target_user_id=clean_uid, category="APPROVAL")
    invalidate_cache()
    return True, None


def get_student_360_summary(student_id):
    sid = str(student_id or "").strip()
    if not sid:
        return None
    records = list(student_records_col().find({"student_id": sid}, {"_id": 0}))
    pred = predictions_col().find_one({"student_id": sid}, {"_id": 0})
    user_doc = users_col().find_one({"student_id": sid}, {"_id": 0, "password_hash": 0})
    if not records and user_doc is None:
        return None

    courses = []
    for rec in records:
        marks = round(_safe_float(rec.get("internal_marks"), 0.0), 1)
        courses.append({"course_code": str(rec.get("course_code") or "CS-101").strip().upper(), "attendance_pct": round(_safe_float(rec.get("attendance_pct"), 0.0), 1), "internal_marks": marks, "assignment_score": round(_safe_float(rec.get("assignment_score"), marks), 1)})

    primary, user_info = (records[0] if records else {}), (user_doc or {})
    full_name = str(primary.get("full_name") or user_info.get("full_name") or sid)
    batch = str(primary.get("batch") or user_info.get("batch") or "2026-A")
    count = len(courses)
    avg_attendance = round(sum(c["attendance_pct"] for c in courses) / count, 1) if count else 0.0
    avg_marks = round(sum(c["internal_marks"] for c in courses) / count, 1) if count else 0.0
    avg_assign = round(sum(c["assignment_score"] for c in courses) / count, 1) if count else 0.0
    lms_hours = round(_safe_float(primary.get("lms_hours_weekly"), 8.0), 1)
    previous_gpa = round(_safe_float(primary.get("previous_gpa"), 0.0), 2)

    pred_info = pred or {}
    raw_pred_gpa = pred_info.get("predicted_gpa")
    predicted_gpa = round(_safe_float(raw_pred_gpa), 2) if raw_pred_gpa is not None else None
    raw_score = pred_info.get("dropout_risk_score") if pred_info.get("dropout_risk_score") is not None else pred_info.get("risk_score")
    dropout_risk_score = round(_safe_float(raw_score), 4) if raw_score is not None else None
    is_anomaly = bool(pred_info.get("is_anomaly"))
    anomaly_reason, recommendation = str(pred_info.get("anomaly_reason") or ""), str(pred_info.get("recommendation") or "")

    raw_level = str(pred_info.get("risk_level") or "").strip().upper()
    if raw_level:
        risk_level = raw_level
    elif records:
        risk_level = "HIGH" if avg_attendance < 60.0 else ("MEDIUM" if avg_attendance < 75.0 or avg_marks < 60.0 else "LOW")
    else:
        risk_level = "PENDING"
    risk_status = {"HIGH": "danger", "MEDIUM": "warning", "LOW": "success", "PENDING": "info"}.get(risk_level, "info")

    notif_targets = [{"target_user_id": sid}, {"student_id": sid}]
    uid = str(user_info.get("user_id") or "").strip()
    if uid and uid != sid:
        notif_targets.append({"target_user_id": uid})
    recent_alerts = [_format_alert(n) for n in notifications_col().find({"$or": notif_targets}, {"_id": 0}).sort("created_at", DESCENDING).limit(5)]

    return {
        "student_id": sid, "full_name": full_name, "batch": batch,
        "email": str(user_info.get("email") or ""), "avatar_url": str(user_info.get("avatar_url") or ""), "initials": _initials(full_name, "S"),
        "avg_attendance": avg_attendance, "avg_marks": avg_marks, "previous_gpa": previous_gpa, "predicted_gpa": predicted_gpa,
        "risk_level": risk_level, "risk_status": risk_status, "dropout_risk_score": dropout_risk_score,
        "is_anomaly": is_anomaly, "anomaly_reason": anomaly_reason, "recommendation": recommendation,
        "risk_reasons": _build_risk_reasons(records, avg_attendance, avg_marks, previous_gpa, predicted_gpa, dropout_risk_score, risk_level, anomaly_reason, recommendation),
        "courses": courses, "recent_alerts": recent_alerts,
        "edit_attrs": {
            "student_id": sid, "full_name": full_name, "batch": batch, "course_code": str(primary.get("course_code") or "CS-101").strip().upper(),
            "attendance_pct": f"{avg_attendance:.1f}", "internal_marks": f"{avg_marks:.1f}",
            "assignment_score": f"{avg_assign:.1f}", "lms_hours_weekly": f"{lms_hours:.1f}", "previous_gpa": f"{previous_gpa:.2f}",
        },
    }
