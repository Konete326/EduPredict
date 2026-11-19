from pymongo import DESCENDING
from core.db import check_db_health, get_cached, notifications_col
from core.theme_services import get_theme_studio_catalog, get_user_theme_prefs


def _build_notification_query(user_id, active_role, student_id=None):
    targets = [{"target_user_id": tid} for tid in dict.fromkeys(x for x in (user_id, student_id) if x)]
    for target_role in dict.fromkeys(r for r in (active_role, "ALL") if r):
        targets.append({"target_role": target_role, "target_user_id": {"$in": [None, ""]}})
        targets.append({"target_role": target_role, "target_user_id": {"$exists": False}})
    return {"is_read": False, "$or": targets}


def _fetch_unread_notifications(current_user, active_role):
    user_id = str(current_user.get("user_id") or "").strip()
    student_id = str(current_user.get("student_id") or "").strip()
    role_key = str(active_role or "").strip().upper()
    if not user_id and not student_id and not role_key:
        return [], 0

    def _loader():
        col = notifications_col()
        query = _build_notification_query(user_id, role_key, student_id=student_id)
        total_count = int(col.count_documents(query))
        cursor = col.find(query).sort("created_at", DESCENDING).limit(5)

        items = []
        for doc in cursor:
            item = dict(doc)
            if "_id" in item:
                item["id"] = str(item["_id"])
                del item["_id"]
            items.append(item)
        return items, total_count

    return get_cached(f"notifs:{user_id}:{student_id}:{role_key}", 20.0, _loader)


def global_context(request):
    session = getattr(request, "session", None)
    raw_user = session.get("user") if session is not None else None
    current_user = raw_user if isinstance(raw_user, dict) and raw_user else None
    raw_role = current_user.get("role") if current_user else None
    active_role = str(raw_role).strip().upper() if raw_role else None

    db_connected = False
    unread_notifications = []
    unread_notifications_count = 0

    try:
        health = check_db_health()
        db_connected = bool(health.get("connected", False))
    except Exception:
        db_connected = False

    if db_connected and current_user:
        try:
            unread_notifications, unread_notifications_count = _fetch_unread_notifications(
                current_user,
                active_role,
            )
        except Exception:
            unread_notifications = []
            unread_notifications_count = 0

    return {
        "current_user": current_user,
        "active_role": active_role,
        "unread_notifications": unread_notifications,
        "unread_notifications_count": unread_notifications_count,
        "db_connected": db_connected,
        "theme_prefs": get_user_theme_prefs(request),
        "theme_catalog": get_theme_studio_catalog(),
    }
