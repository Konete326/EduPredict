import json
from datetime import datetime, timezone
from pymongo import DESCENDING
from core.db import get_cached, invalidate_cache, password_requests_col, users_col
from panels.admin_audit_services import record_audit_log
from panels.admin_seed import _format_dt
from panels.notification_services import create_notification


def _audit(action, summary, severity="INFO", actor="System Admin"):
    try:
        record_audit_log(actor, "ADMIN", "SECURITY", action, summary, severity=severity, source="SYSTEM")
    except Exception:
        pass


def _initials(name, fallback="U"):
    return "".join(p[0] for p in str(name or "").split() if p)[:2].upper() or fallback


def _status_badge(status):
    st = str(status or "PENDING").strip().upper()
    if st == "APPROVED":
        return {"text": "Approved", "status": "success"}
    if st == "REJECTED":
        return {"text": "Rejected", "status": "danger"}
    return {"text": "Pending", "status": "warning"}


def _action_btn(label, icon, onclick, title, attrs, variant="default"):
    return {"label": label, "icon": icon, "variant": variant, "title": title, "onclick": onclick, "attrs": attrs}


def _view_action(title, payload):
    return {"type": "view_modal", "label": "View", "icon": "fa-solid fa-eye", "variant": "default", "title": title, "payload_json": json.dumps(payload)}


def _build_password_requests_context():
    docs = list(password_requests_col().find({}, {"_id": 0}).sort("created_at", DESCENDING))
    requests, rows, cards, pending_count = [], [], [], 0
    for d in docs:
        rid = str(d.get("request_id") or "").strip()
        uid = str(d.get("user_id") or "").strip()
        name = str(d.get("full_name") or "User").strip()
        role = str(d.get("role") or "USER").strip().upper()
        email = str(d.get("email") or "").strip()
        plain_pwd = str(d.get("requested_password_plain") or "").strip()
        status = str(d.get("status") or "PENDING").strip().upper()
        if status == "PENDING":
            pending_count += 1
        badge = _status_badge(status)
        created_str = _format_dt(d.get("created_at"))
        reviewed_str = _format_dt(d.get("reviewed_at")) if d.get("reviewed_at") else "-"
        reviewed_by = str(d.get("reviewed_by") or "-").strip()
        requests.append({
            "request_id": rid, "user_id": uid, "full_name": name, "role": role, "email": email,
            "requested_password_plain": plain_pwd, "status": status,
            "created_at_str": created_str, "reviewed_by": reviewed_by, "reviewed_at_str": reviewed_str,
        })
        attrs = {"data-request-id": rid, "data-full-name": name, "data-email": email, "data-role": role}
        if status == "PENDING":
            actions = [
                _action_btn("Approve", "fa-solid fa-check", "openApprovePasswordModal(this)", f"Approve {name}", attrs, variant="primary"),
                _action_btn("Reject", "fa-solid fa-xmark", "openRejectPasswordModal(this)", f"Reject {name}", attrs, variant="danger"),
            ]
        else:
            actions = [_view_action(f"Request {rid}", {
                "title": name, "subtitle": f"{role} · {email}", "badge": badge["text"],
                "items": [
                    {"label": "Request ID", "value": rid}, {"label": "New Password", "value": plain_pwd or "-"},
                    {"label": "Requested", "value": created_str}, {"label": "Reviewed By", "value": reviewed_by},
                    {"label": "Reviewed At", "value": reviewed_str},
                ],
            })]
        rows.append([{"text": name, "initials": _initials(name, "U")}, role, email, plain_pwd or "-", badge, {"actions": actions}])
        cards.append({
            "id": rid, "title": name, "subtitle": f"{role} · {email}", "badge": badge,
            "meta": [{"label": "Request ID", "value": rid}, {"label": "New Password", "value": plain_pwd or "-"}, {"label": "Requested", "value": created_str}],
            "actions": actions,
        })
    return {
        "requests": requests, "headers": ["User", "Role", "Email", "New Password", "Status", "Actions"],
        "rows": rows, "cards": cards, "pending_count": pending_count, "total_count": len(requests),
    }


def get_password_requests_context():
    return get_cached("admin:password_requests", _build_password_requests_context, ttl=15.0)


def approve_password_request(request_id, actor_name="System Admin"):
    clean_id = str(request_id or "").strip()
    if not clean_id:
        return False, "Request ID is required."
    req = password_requests_col().find_one({"request_id": clean_id, "status": "PENDING"})
    if req is None:
        return False, "Pending password request not found."
    target_uid = str(req.get("user_id") or "").strip()
    target_email = str(req.get("email") or "").strip().lower()
    user_query = {"user_id": target_uid} if target_uid else {"email": target_email}
    user_doc = users_col().find_one(user_query)
    if user_doc is None and target_email:
        user_query = {"email": target_email}
        user_doc = users_col().find_one(user_query)
    if user_doc is None:
        return False, "Target user account not found."
    now = datetime.now(timezone.utc)
    users_col().update_one(
        {"_id": user_doc["_id"]},
        {"$set": {
            "password_hash": req.get("requested_password_hash", ""),
            "previous_password_hash": req.get("previous_password_hash", ""),
            "updated_at": now,
        }},
    )
    password_requests_col().update_one(
        {"request_id": clean_id},
        {"$set": {"status": "APPROVED", "reviewed_by": actor_name, "reviewed_at": now}},
    )
    plain_pwd = str(req.get("requested_password_plain") or "").strip()
    create_notification(
        title="Password Approved",
        message=f"Admin approved your password change. Your new password is: {plain_pwd}",
        severity="SUCCESS",
        target_user_id=str(user_doc.get("user_id") or target_uid),
        category="PASSWORD",
    )
    _audit("APPROVE_PASSWORD", f"Approved password request {clean_id} for {req.get('email', target_uid)}.", "INFO", actor=actor_name)
    invalidate_cache()
    return True, None


def reject_password_request(request_id, actor_name="System Admin"):
    clean_id = str(request_id or "").strip()
    if not clean_id:
        return False, "Request ID is required."
    req = password_requests_col().find_one({"request_id": clean_id, "status": "PENDING"})
    if req is None:
        return False, "Pending password request not found."
    now = datetime.now(timezone.utc)
    password_requests_col().update_one(
        {"request_id": clean_id},
        {"$set": {"status": "REJECTED", "reviewed_by": actor_name, "reviewed_at": now}},
    )
    target_uid = str(req.get("user_id") or "").strip()
    if target_uid:
        create_notification(
            title="Password Request Rejected",
            message="Admin rejected your password change request. Your current password remains active.",
            severity="DANGER",
            target_user_id=target_uid,
            category="PASSWORD",
        )
    _audit("REJECT_PASSWORD", f"Rejected password request {clean_id} for {req.get('email', target_uid)}.", "WARNING", actor=actor_name)
    invalidate_cache()
    return True, None
