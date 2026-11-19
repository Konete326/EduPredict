from datetime import datetime, timezone
from pymongo import DESCENDING
from core.db import get_cached, invalidate_cache, notifications_col, support_tickets_col


def _format_alert_doc(doc):
    if not doc:
        return None
    created = doc.get("created_at")
    severity = str(doc.get("severity") or "INFO").upper()
    status_map = {"DANGER": "danger", "WARNING": "warning"}
    return {
        "id": str(doc.get("_id") or ""),
        "title": str(doc.get("title") or "Notice"),
        "message": str(doc.get("message") or ""),
        "severity": severity,
        "is_read": bool(doc.get("is_read")),
        "created": created.strftime("%Y-%m-%d %H:%M") if hasattr(created, "strftime") else "-",
        "status": status_map.get(severity, "info"),
    }


def _alert_targets(student_id, user_id, role):
    targets = [{"target_user_id": tid} for tid in dict.fromkeys(x for x in (student_id, user_id) if x)]
    for target_role in dict.fromkeys(r for r in (role, "ALL") if r):
        targets.append({"target_role": target_role, "target_user_id": {"$in": [None, ""]}})
        targets.append({"target_role": target_role, "target_user_id": {"$exists": False}})
    return targets


def _load_recent_alerts(student_id, user_id, role, limit=5):
    cursor = notifications_col().find({"$or": _alert_targets(student_id, user_id, role)}).sort("created_at", DESCENDING).limit(int(limit))
    return [a for a in (_format_alert_doc(doc) for doc in cursor) if a]


def _build_student_alerts(student_id, user_id, role):
    items = _load_recent_alerts(student_id, user_id, role, limit=30)
    my_tickets = []
    for t in support_tickets_col().find({"$or": [{"user_id": user_id}, {"user_id": student_id}]}, {"_id": 0}).sort("created_at", DESCENDING).limit(10):
        created = t.get("created_at")
        status = str(t.get("status") or "OPEN").upper()
        my_tickets.append({
            "ticket_id": str(t.get("ticket_id") or ""),
            "subject": str(t.get("subject") or ""),
            "message": str(t.get("message") or ""),
            "status": status,
            "status_badge": {"text": "Resolved" if status == "RESOLVED" else "Open", "status": "success" if status == "RESOLVED" else "warning"},
            "created": created.strftime("%Y-%m-%d %H:%M") if hasattr(created, "strftime") else "-",
        })
    unread = sum(1 for a in items if not a["is_read"])
    return {"alerts": items, "my_tickets": my_tickets, "unread": unread, "total": len(items)}


def get_student_alerts_context(student_id, user_id, role):
    key = f"student:alerts:{student_id}:{user_id}:{role}"
    return get_cached(key, lambda: _build_student_alerts(student_id, user_id, role), ttl=20.0)


def mark_alert_read(alert_id, student_id, user_id, role):
    try:
        oid = __import__("bson").ObjectId(str(alert_id).strip())
    except Exception:
        return False, "This alert no longer exists."
    targets = _alert_targets(student_id, user_id, role)
    updated = notifications_col().update_one({"_id": oid, "is_read": False, "$or": targets}, {"$set": {"is_read": True, "read_at": datetime.now(timezone.utc)}})
    invalidate_cache()
    if updated.modified_count:
        return True, None
    return False, "Alert not found or already read."
