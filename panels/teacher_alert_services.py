import re
from datetime import datetime, timezone
from pymongo import DESCENDING
from analytics.ml_engine import _resolve_runtime_settings
from core.db import courses_col, get_cached, invalidate_cache, notifications_col, users_col
from panels.admin_audit_services import system_settings_col
from panels.teacher_services import _alert_attrs, _load_joined_students


def _build_teacher_alert_query(teacher_user=None):
    base = {"target_role": "STUDENT", "title": {"$regex": "^Teacher Alert"}}
    if not isinstance(teacher_user, dict):
        return base
    uid = str(teacher_user.get("user_id") or "").strip()
    tname = str(teacher_user.get("full_name") or "").strip()
    temail = str(teacher_user.get("email") or "").strip()
    clauses = []
    if uid:
        clauses.append({"sender_user_id": uid})
    for label in {v for v in (tname, temail) if v}:
        esc = re.escape(label)
        clauses.append({"sender_name": {"$regex": f"^{esc}$", "$options": "i"}})
        clauses.append({
            "sender_user_id": {"$exists": False},
            "sender_name": {"$exists": False},
            "message": {"$regex": f" - {esc}$", "$options": "i"},
        })
    if not clauses:
        return base
    return {**base, "$or": clauses}


def _load_alert_history(limit=30, teacher_user=None):
    rows = []
    query = _build_teacher_alert_query(teacher_user)
    for doc in notifications_col().find(query, {"_id": 0}).sort("created_at", DESCENDING).limit(limit):
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
            "created": created.strftime("%b %d, %H:%M") if hasattr(created, "strftime") else "-",
        })
    return rows


def _load_teacher_alerts_context(teacher_user=None):
    students = _load_joined_students()
    at_risk = [s for s in students if s["badge"]["text"] in ("High Risk", "Needs Help")]
    at_risk.sort(key=lambda x: (0 if x["badge"]["text"] == "High Risk" else 1, x["attendance_pct"]))
    history = _load_alert_history(teacher_user=teacher_user)

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


def get_teacher_alerts_context(teacher_user=None):
    uid = str((teacher_user or {}).get("user_id") or "").strip()
    tname = str((teacher_user or {}).get("full_name") or "").strip()
    key = f"teacher:alerts:{uid or tname or 'all'}"
    return get_cached(key, lambda: _load_teacher_alerts_context(teacher_user), ttl=30.0)


def notify_all_high_risk_students(sender_name="Teacher", sender_user_id=""):
    students = _load_joined_students()
    targets = [
        s for s in students
        if s["risk_level"] == "HIGH" or s["badge"]["text"] in ("High Risk", "Needs Help") or s["attendance_pct"] < 75.0
    ]
    if not targets:
        return 0, "No high-risk or low-attendance students found."

    now = datetime.now(timezone.utc)
    sender_lbl = str(sender_name or "Teacher").strip() or "Teacher"
    sender_uid = str(sender_user_id or "").strip()
    col = notifications_col()
    for s in targets:
        sid = s["student_id"]
        course = str(s.get("course_code") or "Class").strip().upper() or "Class"
        is_high = s["risk_level"] == "HIGH" or s["badge"]["text"] == "High Risk"
        doc = {
            "target_role": "STUDENT",
            "target_user_id": sid,
            "student_id": sid,
            "title": f"Teacher Alert ({course})",
            "message": f"Academic follow-up required in {course}: attendance {s['attendance_pct']:.1f}%, marks {s['internal_marks']:.1f}. - {sender_lbl}",
            "sender_name": sender_lbl,
            "severity": "DANGER" if is_high else "WARNING",
            "is_read": False,
            "created_at": now,
        }
        if sender_uid:
            doc["sender_user_id"] = sender_uid
        col.insert_one(doc)
    invalidate_cache()
    return len(targets), None


def _load_teacher_portal_meta(teacher_user=None, course_scope="AUTO"):
    user = teacher_user if isinstance(teacher_user, dict) else {}
    uid = str(user.get("user_id") or "").strip()
    tname = str(user.get("full_name") or "").strip().lower()
    temail = str(user.get("email") or "").strip().lower()
    all_courses = []
    for c in courses_col().find({}, {"_id": 0}).sort("course_code", 1):
        code = str(c.get("course_code") or "").strip().upper()
        if not code:
            continue
        inst = str(c.get("instructor") or "TBA").strip()
        inst_id = str(c.get("instructor_id") or "").strip()
        inst_email = str(c.get("instructor_email") or "").strip().lower()
        is_mine = bool(
            (uid and inst_id and inst_id == uid)
            or (tname and inst.lower() == tname)
            or (temail and inst_email and inst_email == temail)
        )
        all_courses.append({
            "course_code": code,
            "title": str(c.get("title") or code),
            "batch": str(c.get("batch") or "2026-A"),
            "department": str(c.get("department") or "General"),
            "instructor": inst,
            "credits": int(c.get("credits") or 3),
            "status": str(c.get("status") or "ACTIVE").upper(),
            "is_mine": is_mine,
        })
    my_count = sum(1 for c in all_courses if c["is_mine"])
    scope = str(course_scope or "AUTO").strip().upper()
    if scope not in ("MY", "ALL"):
        scope = "MY" if my_count > 0 else "ALL"
    visible = [c for c in all_courses if c["is_mine"]] if scope == "MY" else all_courses
    admin_doc = users_col().find_one({"role": "ADMIN", "is_active": True}, {"_id": 0, "full_name": 1, "email": 1}) or {}
    return {
        "assigned_courses": visible,
        "course_scope": scope,
        "my_courses_count": my_count,
        "all_courses_count": len(all_courses),
        "admin_contact": {
            "name": str(admin_doc.get("full_name") or "Portal Admin"),
            "email": str(admin_doc.get("email") or "admin@edupredict.edu"),
        },
    }


def get_teacher_portal_meta(teacher_user=None, course_scope="AUTO"):
    uid = str((teacher_user or {}).get("user_id") or "").strip()
    tname = str((teacher_user or {}).get("full_name") or "").strip()
    scope = str(course_scope or "AUTO").strip().upper()
    key = f"teacher:meta:{uid or tname or 'all'}:{scope}"
    return get_cached(key, lambda: _load_teacher_portal_meta(teacher_user, scope), ttl=30.0)


def clean_teacher_student_cards(cards):
    cleaned = []
    for card in cards or []:
        item = dict(card)
        item["subtitle"] = ""
        cleaned.append(item)
    return cleaned


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
