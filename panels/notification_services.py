from datetime import datetime, timezone
from bson import ObjectId
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


def _user_identity(current_user):
    user = current_user if isinstance(current_user, dict) else {}
    return (
        str(user.get("user_id") or "").strip(),
        str(user.get("student_id") or "").strip(),
        str(user.get("role") or "").strip().upper(),
    )


def _user_notification_targets(user_id, role_key, student_id=""):
    targets = [{"target_user_id": tid} for tid in dict.fromkeys(x for x in (user_id, student_id) if x)]
    for target_role in dict.fromkeys(r for r in (role_key, "ALL") if r):
        targets.append({"target_role": target_role, "target_user_id": {"$in": [None, ""]}})
        targets.append({"target_role": target_role, "target_user_id": {"$exists": False}})
    return targets


def _resolve_notification_target(doc, role_key=""):
    role = str(role_key or "").strip().upper()
    item = doc if isinstance(doc, dict) else {}
    category = str(item.get("category") or "").strip().upper()
    severity = str(item.get("severity") or "").strip().upper()
    title = str(item.get("title") or "").strip()
    message = str(item.get("message") or "").strip()
    cat_title = f"{category} {title}".upper()
    text_blob = f"{title} {message}".upper()
    if role == "ADMIN":
        if any(kw in cat_title or kw in text_blob for kw in ("TICKET", "FEEDBACK", "REPLY")):
            return "/admin-panel/tickets/"
        if any(kw in cat_title or kw in text_blob for kw in ("APPROVAL", "TEACHER", "USER")):
            return "/admin-panel/users/"
        if any(kw in cat_title for kw in ("LOG", "AUDIT", "BACKUP")):
            return "/admin-panel/logs/"
        return "/admin-panel/"
    if role == "TEACHER":
        if severity in ("WARNING", "DANGER") or any(kw in cat_title or kw in text_blob for kw in ("ALERT", "DROP", "RISK", "ATTENDANCE")):
            return "/teacher-panel/alerts/"
        if any(kw in text_blob for kw in ("MARKS", "CSV", "GPA", "STUDENT")):
            return "/teacher-panel/students/"
        return "/teacher-panel/"
    if role == "STUDENT":
        if any(kw in text_blob for kw in ("GPA", "MARKS", "PREDICTION", "RISK", "REPORT", "GRADE", "ATTENDANCE")):
            return "/student-panel/report/"
        if any(kw in text_blob for kw in ("TIP", "STUDY", "GOAL")):
            return "/student-panel/tips/"
        if category == "FEEDBACK_REPLY" or any(kw in cat_title for kw in ("TICKET", "REPLY")):
            return "/student-panel/notifications/"
        return "/student-panel/"
    if role == "ANALYST":
        if any(kw in text_blob for kw in ("ACCURACY", "MODEL", "HEALTH", "MAE", "ANOMALY")):
            return "/analyst-panel/accuracy/"
        return "/analyst-panel/"
    return "/student-panel/"


def create_notification(title, message, severity="INFO", target_role="", target_user_id="", category="SYSTEM", ticket_id="", feedback_text="", reply_text=""):
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


def _serialize_notification(doc, role_key=""):
    return {
        "id": str(doc.get("_id") or ""),
        "title": str(doc.get("title") or ""),
        "message": str(doc.get("message") or ""),
        "severity": str(doc.get("severity") or "INFO").upper(),
        "category": str(doc.get("category") or "SYSTEM").upper(),
        "ticket_id": str(doc.get("ticket_id") or ""),
        "feedback_text": str(doc.get("feedback_text") or ""),
        "reply_text": str(doc.get("reply_text") or ""),
        "is_read": bool(doc.get("is_read", False)),
        "target_url": _resolve_notification_target(doc, role_key),
        "created_at_str": _format_dt(doc.get("created_at")),
    }


def get_live_notifications_feed(current_user, limit=8):
    user_id, student_id, role_key = _user_identity(current_user)
    if not user_id and not student_id and not role_key:
        return [], 0

    safe_limit = max(1, min(20, int(limit or 8)))

    def _loader():
        col = notifications_col()
        query = _build_notification_query(user_id, role_key, student_id=student_id)
        unread_count = int(col.count_documents(query))
        cursor = col.find(query).sort("created_at", DESCENDING).limit(safe_limit)
        return [_serialize_notification(doc, role_key) for doc in cursor], unread_count

    return get_cached(f"notifs:live:{user_id}:{student_id}:{role_key}:{safe_limit}", _loader, ttl=10.0)


def _sort_stamp(val):
    if isinstance(val, datetime):
        dt = val if val.tzinfo is not None else val.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    if isinstance(val, str) and val.strip():
        try:
            dt = datetime.fromisoformat(val.strip().replace("Z", "+00:00"))
            return (dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)).timestamp()
        except ValueError:
            return 0.0
    return 0.0


def list_notifications_history(current_user, filter_tab="ALL"):
    counts = {"ALL": 0, "UNREAD": 0, "READ": 0, "REPLIES": 0}
    user_id, student_id, role_key = _user_identity(current_user)
    if not user_id and not student_id and not role_key:
        return [], counts, None

    tab = str(filter_tab or "ALL").strip().upper()
    if tab not in ("ALL", "UNREAD", "READ", "REPLIES"):
        tab = "ALL"

    try:
        targets = _user_notification_targets(user_id, role_key, student_id=student_id)
        notif_cursor = notifications_col().find({"$or": targets}).sort("created_at", DESCENDING).limit(80)
        entries = []
        seen_reply_tids = set()
        for doc in notif_cursor:
            item = _serialize_notification(doc, role_key)
            tid = item["ticket_id"]
            if tid and (item["category"] == "FEEDBACK_REPLY" or item["reply_text"]):
                seen_reply_tids.add(tid)
            entries.append((_sort_stamp(doc.get("created_at")), item))

        uid_values = [x for x in dict.fromkeys((user_id, student_id)) if x]
        ticket_query = None
        if role_key == "ADMIN":
            ticket_query = {"admin_reply": {"$nin": ["", None]}}
        elif uid_values:
            ticket_query = {"user_id": {"$in": uid_values}, "admin_reply": {"$nin": ["", None]}}

        if ticket_query is not None:
            t_cursor = support_tickets_col().find(ticket_query).sort("replied_at", DESCENDING).limit(80)
            for t in t_cursor:
                reply_text = str(t.get("admin_reply") or "").strip()
                tid = str(t.get("ticket_id") or "").strip()
                if not reply_text or (tid and tid in seen_reply_tids):
                    continue
                if tid:
                    seen_reply_tids.add(tid)
                subject = str(t.get("subject") or "").strip()
                ts = t.get("replied_at") or t.get("updated_at") or t.get("created_at")
                synth = {
                    "_id": "",
                    "title": f"Reply on {tid}: {subject}" if subject else f"Reply on {tid}",
                    "message": reply_text,
                    "severity": "SUCCESS",
                    "category": "FEEDBACK_REPLY",
                    "ticket_id": tid,
                    "feedback_text": str(t.get("message") or "").strip(),
                    "reply_text": reply_text,
                    "is_read": True,
                    "created_at": ts,
                }
                entries.append((_sort_stamp(ts), _serialize_notification(synth, role_key)))

        entries.sort(key=lambda pair: pair[0], reverse=True)
        all_items = [pair[1] for pair in entries[:80]]
        total_unread_db = int(notifications_col().count_documents({"is_read": False, "$or": targets}))
        total_read_db = int(notifications_col().count_documents({"is_read": True, "$or": targets}))
        total_replies = sum(1 for it in all_items if it["category"] == "FEEDBACK_REPLY" or bool(it["reply_text"]))
        counts = {
            "ALL": max(len(all_items), total_unread_db + total_read_db),
            "UNREAD": total_unread_db,
            "READ": max(sum(1 for it in all_items if it["is_read"]), total_read_db),
            "REPLIES": total_replies,
        }
        if tab == "UNREAD":
            filtered = [it for it in all_items if not it["is_read"]]
        elif tab == "READ":
            filtered = [it for it in all_items if it["is_read"]]
        elif tab == "REPLIES":
            filtered = [it for it in all_items if it["category"] == "FEEDBACK_REPLY" or bool(it["reply_text"])]
        else:
            filtered = all_items
        return filtered, counts, None
    except Exception as exc:
        return [], counts, str(exc)


def mark_single_notification_read(notif_id, current_user):
    try:
        oid = ObjectId(str(notif_id or "").strip())
    except Exception:
        return False
    user_id, student_id, role_key = _user_identity(current_user)
    if not user_id and not student_id and not role_key:
        return False
    targets = _user_notification_targets(user_id, role_key, student_id=student_id)
    res = notifications_col().update_one(
        {"_id": oid, "$or": targets},
        {"$set": {"is_read": True, "read_at": datetime.now(timezone.utc)}},
    )
    invalidate_cache()
    return bool(getattr(res, "modified_count", 0) or getattr(res, "matched_count", 0))


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
