from datetime import datetime, timezone
from analytics.ml_engine import _resolve_runtime_settings
from core.db import courses_col, get_cached, invalidate_cache, notifications_col, users_col
from panels.admin_audit_services import system_settings_col
from panels.teacher_services import _load_joined_students


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
