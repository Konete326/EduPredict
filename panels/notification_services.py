from datetime import datetime, timezone
from pymongo import DESCENDING
from core.context_processors import _build_notification_query
from core.db import get_cached, invalidate_cache, notifications_col, support_tickets_col
from panels.admin_audit_services import record_audit_log
from panels.admin_seed import _format_dt


def _safe_audit(actor_name, action, summary, severity="INFO"):
    try:
        record_audit_log(actor_name, "ADMIN", "TICKETS", action, summary, severity=severity, source="SYSTEM")
    except Exception:
        pass


def create_notification(
    title,
    message,
    severity="INFO",
    target_role="",
    target_user_id="",
    category="SYSTEM",
    ticket_id="",
    feedback_text="",
    reply_text="",
):
    doc = {
        "title": str(title or "").strip(),
        "message": str(message or "").strip(),
        "severity": str(severity or "INFO").strip().upper(),
        "category": str(category or "SYSTEM").strip().upper(),
        "target_role": str(target_role or "").strip().upper(),
        "target_user_id": str(target_user_id or "").strip(),
        "ticket_id": str(ticket_id or "").strip(),
        "feedback_text": str(feedback_text or "").strip(),
        "reply_text": str(reply_text or "").strip(),
        "is_read": False,
        "created_at": datetime.now(timezone.utc),
    }
    notifications_col().insert_one(doc)
    invalidate_cache()
    return doc


def _serialize_notification(doc):
    return {
        "id": str(doc.get("_id") or ""),
        "title": str(doc.get("title") or ""),
        "message": str(doc.get("message") or ""),
        "severity": str(doc.get("severity") or "INFO").upper(),
        "category": str(doc.get("category") or "SYSTEM").upper(),
        "ticket_id": str(doc.get("ticket_id") or ""),
        "feedback_text": str(doc.get("feedback_text") or ""),
        "reply_text": str(doc.get("reply_text") or ""),
        "created_at_str": _format_dt(doc.get("created_at")),
    }


def get_live_notifications_feed(current_user, limit=8):
    user = current_user if isinstance(current_user, dict) else {}
    user_id = str(user.get("user_id") or "").strip()
    student_id = str(user.get("student_id") or "").strip()
    role_key = str(user.get("role") or "").strip().upper()
    if not user_id and not student_id and not role_key:
        return [], 0

    safe_limit = max(1, min(20, int(limit or 8)))

    def _loader():
        col = notifications_col()
        query = _build_notification_query(user_id, role_key, student_id=student_id)
        unread_count = int(col.count_documents(query))
        cursor = col.find(query).sort("created_at", DESCENDING).limit(safe_limit)
        return [_serialize_notification(doc) for doc in cursor], unread_count

    return get_cached(f"notifs:live:{user_id}:{student_id}:{role_key}:{safe_limit}", _loader, ttl=10.0)


def reply_to_ticket(ticket_id, reply_text, actor_name="System Admin", resolve_ticket=True):
    clean_tid = str(ticket_id or "").strip()
    clean_reply = str(reply_text or "").strip()
    if not clean_reply:
        return False, "Reply message is required."
    col = support_tickets_col()
    ticket = col.find_one({"ticket_id": clean_tid})
    if ticket is None:
        return False, "Support ticket not found."
    actor = str(actor_name or "System Admin").strip() or "System Admin"
    now = datetime.now(timezone.utc)
    updates = {
        "admin_reply": clean_reply,
        "replied_by": actor,
        "replied_at": now,
        "updated_at": now,
    }
    if resolve_ticket:
        updates["status"] = "RESOLVED"
    col.update_one({"_id": ticket["_id"]}, {"$set": updates})
    target_uid = str(ticket.get("user_id") or "").strip()
    target_role = "" if target_uid else str(ticket.get("role") or "").strip().upper()
    subject = str(ticket.get("subject") or "").strip()
    create_notification(
        title=f"Reply on {clean_tid}: {subject}",
        message=clean_reply,
        severity="SUCCESS",
        target_role=target_role,
        target_user_id=target_uid,
        category="FEEDBACK_REPLY",
        ticket_id=clean_tid,
        feedback_text=str(ticket.get("message") or "").strip(),
        reply_text=clean_reply,
    )
    _safe_audit(actor, "REPLY_TICKET", f"Replied to ticket {clean_tid}.", severity="SUCCESS")
    invalidate_cache()
    return True, None


def delete_ticket_reply(ticket_id, actor_name="System Admin"):
    clean_tid = str(ticket_id or "").strip()
    col = support_tickets_col()
    ticket = col.find_one({"ticket_id": clean_tid})
    if ticket is None:
        return False, "Support ticket not found."
    actor = str(actor_name or "System Admin").strip() or "System Admin"
    col.update_one(
        {"_id": ticket["_id"]},
        {
            "$unset": {"admin_reply": "", "replied_by": "", "replied_at": ""},
            "$set": {"updated_at": datetime.now(timezone.utc)},
        },
    )
    _safe_audit(actor, "DELETE_TICKET_REPLY", f"Deleted reply on ticket {clean_tid}.", severity="WARNING")
    invalidate_cache()
    return True, None
