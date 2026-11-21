from datetime import datetime, timezone
from pymongo import DESCENDING
from analytics.ml_engine import _resolve_runtime_settings
from core.db import get_cached, invalidate_cache, notifications_col
from panels.admin_audit_services import system_settings_col
from panels.teacher_services import _alert_attrs, _load_joined_students


def _load_alert_history(limit=30):
    rows = []
    for doc in notifications_col().find(
        {"target_role": "STUDENT", "title": {"$regex": "^Teacher Alert"}},
        {"_id": 0},
    ).sort("created_at", DESCENDING).limit(limit):
        created = doc.get("created_at")
        severity = str(doc.get("severity") or "INFO").upper()
        status_map = {"DANGER": "danger", "WARNING": "warning"}
        rows.append({
            "title": str(doc.get("title") or "Teacher Alert"),
            "student_id": str(doc.get("student_id") or doc.get("target_user_id") or "-"),
            "message": str(doc.get("message") or ""),
            "severity": severity,
            "severity_badge": {"text": severity, "status": status_map.get(severity, "info")},
            "is_read": bool(doc.get("is_read")),
            "read_badge": {"text": "Read ✓✓" if doc.get("is_read") else "Unread", "status": "success" if doc.get("is_read") else "warning"},
            "created": created.strftime("%Y-%m-%d %H:%M") if hasattr(created, "strftime") else "-",
        })
    return rows


def _load_teacher_alerts_context():
    students = _load_joined_students()
    at_risk = [s for s in students if s["badge"]["text"] in ("High Risk", "Needs Help")]
    at_risk.sort(key=lambda x: (0 if x["badge"]["text"] == "High Risk" else 1, x["attendance_pct"]))
    history = _load_alert_history()

    roster_headers = ["Student ID", "Name", "Course", "Attendance", "Marks", "Status", "Actions"]
    roster_rows = []
    for s in at_risk:
        roster_rows.append([
            s["student_id"],
            s["full_name"],
            s["course_code"],
            f"{s['attendance_pct']:.1f}%",
            f"{s['internal_marks']:.1f}",
            s["badge"],
            {"actions": [{
                "label": "Send Alert",
                "icon": "fa-solid fa-bell",
                "variant": "primary",
                "title": f"Send alert to {s['full_name']}",
                "onclick": "openSendAlertModal(this)",
                "attrs": _alert_attrs(s),
            }]},
        ])

    history_headers = ["Title", "Student", "Message", "Level", "Read", "Date"]
    history_rows = [
        [a["title"], a["student_id"], a["message"], a["severity_badge"], a["read_badge"], a["created"]]
        for a in history
    ]

    kpis = {
        "at_risk_count": len(at_risk),
        "high_risk_count": sum(1 for s in students if s["risk_level"] == "HIGH"),
        "medium_risk_count": sum(1 for s in students if s["risk_level"] == "MEDIUM"),
        "alerts_sent": len(history),
        "unread_alerts": sum(1 for a in history if not a["is_read"]),
    }
    return {
        "kpis": kpis,
        "roster_headers": roster_headers,
        "roster_rows": roster_rows,
        "history_headers": history_headers,
        "history_rows": history_rows,
        "students_picker": [
            {"student_id": s["student_id"], "full_name": s["full_name"], "course_code": s["course_code"]}
            for s in students
        ],
        "auto_alerts_enabled": bool(_resolve_runtime_settings(persist=True).get("auto_student_alerts", True)),
        "high_risk_only_count": sum(1 for s in students if s["risk_level"] == "HIGH" or s["badge"]["text"] == "High Risk"),
    }


def get_teacher_alerts_context():
    return get_cached("teacher:alerts", _load_teacher_alerts_context, ttl=30.0)


def notify_all_high_risk_students(sender_name="Teacher"):
    students = _load_joined_students()
    targets = [
        s for s in students
        if s["risk_level"] == "HIGH" or s["badge"]["text"] in ("High Risk", "Needs Help") or s["attendance_pct"] < 75.0
    ]
    if not targets:
        return 0, "No high-risk or low-attendance students found."

    now = datetime.now(timezone.utc)
    sender_lbl = str(sender_name or "Teacher").strip() or "Teacher"
    col = notifications_col()
    for s in targets:
        sid = s["student_id"]
        course = str(s.get("course_code") or "Class").strip().upper() or "Class"
        is_high = s["risk_level"] == "HIGH" or s["badge"]["text"] == "High Risk"
        col.insert_one({
            "target_role": "STUDENT",
            "target_user_id": sid,
            "student_id": sid,
            "title": f"Teacher Alert ({course})",
            "message": f"Academic follow-up required in {course}: attendance {s['attendance_pct']:.1f}%, marks {s['internal_marks']:.1f}. - {sender_lbl}",
            "severity": "DANGER" if is_high else "WARNING",
            "is_read": False,
            "created_at": now,
        })
    invalidate_cache()
    return len(targets), None


def toggle_teacher_auto_alerts(enabled_flag, actor_name="Teacher"):
    enabled = bool(enabled_flag)
    actor = str(actor_name or "Teacher").strip() or "Teacher"
    system_settings_col().update_one(
        {"setting_key": "portal_config"},
        {"$set": {"auto_student_alerts": enabled, "auto_teacher_alerts": enabled, "updated_by": actor, "updated_at": datetime.now(timezone.utc)}},
        upsert=True,
    )
    invalidate_cache()
    return enabled, None
