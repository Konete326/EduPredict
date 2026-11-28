from datetime import datetime, timezone
from pymongo import DESCENDING
from analytics.ml_engine import _resolve_runtime_settings
from analytics.model_health import get_analyst_accuracy_page_context
from core.db import courses_col, datasets_log_col, invalidate_cache, notifications_col, student_records_col, users_col


def _normalize_severity(raw_value):
    val = str(raw_value or "WARNING").strip().upper()
    if val in ("HIGH", "DANGER", "CRITICAL", "ERROR"):
        return "DANGER"
    if val in ("LOW", "INFO"):
        return "INFO"
    return "WARNING"


def _resolve_course_teacher(course_code):
    code = str(course_code or "").strip().upper()
    if not code or code == "GENERAL":
        return "", ""
    course = courses_col().find_one({"course_code": code}, {"_id": 0, "instructor_id": 1, "instructor_email": 1, "instructor": 1}) or {}
    teacher_id = str(course.get("instructor_id") or "").strip()
    teacher_email = str(course.get("instructor_email") or "").strip().lower()
    teacher_name = str(course.get("instructor") or "").strip()
    if not teacher_id and teacher_email:
        u_doc = users_col().find_one({"role": "TEACHER", "email": teacher_email}, {"_id": 0, "user_id": 1, "full_name": 1}) or {}
        teacher_id = str(u_doc.get("user_id") or "").strip()
        teacher_name = teacher_name or str(u_doc.get("full_name") or "").strip()
    if not teacher_id and teacher_name:
        u_doc = users_col().find_one({"role": "TEACHER", "full_name": teacher_name}, {"_id": 0, "user_id": 1}) or {}
        teacher_id = str(u_doc.get("user_id") or "").strip()
    return teacher_id, teacher_name


def send_teacher_risk_alert(student_id, course_code, severity, message, actor_name, actor_role, actor_user_id=""):
    sid = str(student_id or "").strip()
    if not sid:
        return None, "", "Student ID is required."
    rec = student_records_col().find_one({"student_id": sid}, {"_id": 0, "student_id": 1, "full_name": 1, "course_code": 1}) or {}
    full_name = str(rec.get("full_name") or sid).strip()
    clean_course = str(course_code or rec.get("course_code") or "GENERAL").strip().upper()
    clean_msg = str(message or "").strip() or f"{full_name} ({sid}) in {clean_course} was flagged for early teacher follow-up."
    clean_sev = _normalize_severity(severity)
    teacher_id, teacher_name = _resolve_course_teacher(clean_course)
    doc = {
        "title": f"Risk Alert: {full_name} ({sid}) · {clean_course}",
        "message": clean_msg,
        "severity": clean_sev,
        "category": "RISK_ALERT",
        "target_role": "TEACHER",
        "target_user_id": teacher_id,
        "student_id": sid,
        "course_code": clean_course,
        "teacher_name": teacher_name,
        "sender_name": str(actor_name or "Analyst").strip(),
        "sender_role": str(actor_role or "ANALYST").strip().upper(),
        "sender_user_id": str(actor_user_id or "").strip(),
        "is_read": False,
        "created_at": datetime.now(timezone.utc),
    }
    notifications_col().insert_one(doc)
    invalidate_cache()
    recipient_label = teacher_name or (f"{clean_course} Teacher" if clean_course != "GENERAL" else "Course Teachers")
    return doc, recipient_label, None


def get_analyst_health_context():
    try:
        base = get_analyst_accuracy_page_context()
    except Exception as exc:
        base = {
            "kpis": {"total_students": 0, "total_predictions": 0, "coverage_pct": 0.0, "anomaly_count": 0},
            "model_info": {"version": "untrained", "generated": "Never", "features": []},
            "risk_counts": {"LOW": 0, "MEDIUM": 0, "HIGH": 0},
            "error_buckets": {"excellent": 0, "acceptable": 0, "large": 0},
            "demand_headers": ["Course", "Joined Now", "Next Term Need", "Change"],
            "demand_rows": [],
            "chart_data": {},
            "portal_settings": _resolve_runtime_settings(persist=False),
            "db_error": str(exc),
        }

    logs = []
    db_error = base.get("db_error")
    try:
        logs = list(datasets_log_col().find({}, {"_id": 0}).sort("uploaded_at", DESCENDING).limit(50))
    except Exception as exc:
        db_error = db_error or str(exc)

    total_uploads = len(logs)
    total_rows = 0
    total_fixed = 0
    failed_uploads = 0
    dataset_rows = []
    for log in logs:
        rows_cnt = int(log.get("rows_processed") or 0)
        fixed_cnt = int(log.get("missing_values_fixed") or 0)
        status_val = str(log.get("status") or "COMPLETED").strip().upper()
        total_rows += rows_cnt
        total_fixed += fixed_cnt
        if status_val != "COMPLETED":
            failed_uploads += 1
        uploaded_at = log.get("uploaded_at")
        uploaded_text = uploaded_at.strftime("%Y-%m-%d %H:%M") if hasattr(uploaded_at, "strftime") else "-"
        dataset_rows.append([
            str(log.get("filename") or "dataset.csv"),
            rows_cnt,
            fixed_cnt,
            {"text": status_val, "status": "success" if status_val == "COMPLETED" else "danger"},
            str(log.get("uploaded_by") or "Analyst"),
            uploaded_text,
        ])

    impute_rate = round((total_fixed / total_rows) * 100.0, 1) if total_rows else 0.0
    health_kpis = {
        "total_uploads": total_uploads,
        "total_rows": total_rows,
        "total_fixed": total_fixed,
        "failed_uploads": failed_uploads,
        "impute_rate_pct": impute_rate,
        "coverage_pct": base["kpis"].get("coverage_pct", 0.0),
        "anomaly_count": base["kpis"].get("anomaly_count", 0),
    }
    return {
        "kpis": base["kpis"],
        "health_kpis": health_kpis,
        "model_info": base["model_info"],
        "risk_counts": base["risk_counts"],
        "error_buckets": base["error_buckets"],
        "demand_headers": base["demand_headers"],
        "demand_rows": base["demand_rows"],
        "dataset_headers": ["File Name", "Rows", "Fixed Cells", "Status", "Uploaded By", "Date"],
        "dataset_rows": dataset_rows,
        "chart_data": base["chart_data"],
        "portal_settings": base["portal_settings"],
        "db_error": db_error,
    }
