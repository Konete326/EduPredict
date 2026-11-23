import uuid
from datetime import datetime, timezone
from django.contrib.auth.hashers import make_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from pymongo import ASCENDING, DESCENDING
from pymongo.errors import DuplicateKeyError
from accounts.services import VALID_ROLES, ensure_accounts_indexes_once, generate_unique_student_id, generate_unique_user_id
from core.cloudinary_services import encode_image_data_uri, is_cloudinary_configured, upload_ticket_attachment
from core.db import get_cached, invalidate_cache, notifications_col, student_records_col, support_tickets_col, users_col
from panels.admin_audit_services import record_audit_log
from panels.admin_seed import _format_dt, _safe_int, build_backup_payload, courses_col, ensure_admin_seed_data, get_admin_overview_context
from panels.notification_services import create_notification
from panels.phase62_services import reject_teacher_account

VALID_TICKET_STATUSES = ("OPEN", "RESOLVED")
VALID_COURSE_STATUSES = ("ACTIVE", "ARCHIVED")


def _audit(category, action, summary, severity="INFO", actor="System Admin"):
    try:
        record_audit_log(actor, "ADMIN", category, action, summary, severity=severity, source="SYSTEM")
    except Exception:
        pass


def _generate_unique_ticket_id(col):
    base = 1001 + col.count_documents({})
    for offset in range(30):
        candidate = f"TKT-{base + offset}"
        if col.find_one({"ticket_id": candidate}, {"_id": 1}) is None:
            return candidate
    return f"TKT-{uuid.uuid4().hex[:6].upper()}"


def _is_self_target(existing, clean_uid, actor_user_id, actor_email):
    clean_actor_email = str(actor_email or "").strip().lower()
    return bool((actor_user_id and clean_uid == str(actor_user_id).strip()) or (clean_actor_email and str((existing or {}).get("email") or "").strip().lower() == clean_actor_email))


def _load_users(normalized):
    ensure_admin_seed_data()
    role_counts, users = {"ALL": 0, "ADMIN": 0, "TEACHER": 0, "STUDENT": 0, "ANALYST": 0, "PENDING": 0, "REJECTED": 0}, []
    for doc in users_col().find({}, {"_id": 0, "password_hash": 0}).sort("created_at", DESCENDING):
        role, is_active = str(doc.get("role") or "").strip().upper(), bool(doc.get("is_active", True))
        approval_status = str(doc.get("approval_status") or ("APPROVED" if is_active else "INACTIVE")).upper()
        role_counts["ALL"] += 1
        if role in role_counts:
            role_counts[role] += 1
        if approval_status in ("PENDING", "REJECTED"):
            role_counts[approval_status] += 1
        if normalized == "ALL" or (normalized in ("PENDING", "REJECTED") and approval_status == normalized) or role == normalized:
            users.append({"user_id": str(doc.get("user_id") or ""), "full_name": str(doc.get("full_name") or ""), "email": str(doc.get("email") or ""), "role": role, "department": str(doc.get("department") or "General"), "batch": str(doc.get("batch") or "ALL"), "phone": str(doc.get("phone") or ""), "bio": str(doc.get("bio") or ""), "is_active": is_active, "approval_status": approval_status, "rejection_reason": str(doc.get("rejection_reason") or ""), "student_id": str(doc.get("student_id") or ""), "avatar_url": str(doc.get("avatar_url") or ""), "created_at_str": _format_dt(doc.get("created_at"))})
    return users, role_counts


def list_users(role_filter="ALL"):
    normalized = str(role_filter or "ALL").strip().upper()
    return get_cached(f"admin:users:{normalized}", lambda: _load_users(normalized), ttl=30.0)


def _validate_user_input(full_name, email, role, department, batch):
    clean_name, clean_email, clean_role = str(full_name or "").strip(), str(email or "").strip().lower(), str(role or "").strip().upper()
    if not clean_name:
        return None, "Full name is required."
    try:
        validate_email(clean_email)
    except ValidationError:
        return None, "Please enter a valid email address."
    if clean_role not in VALID_ROLES:
        return None, "Select a valid role (ADMIN, TEACHER, STUDENT, or ANALYST)."
    clean_dept, clean_batch = str(department or "").strip() or "General", str(batch or "").strip() or ("2026-A" if clean_role == "STUDENT" else "ALL")
    return (clean_name, clean_email, clean_role, clean_dept, clean_batch), None


def create_user_record(full_name, email, password, role, department, batch, actor_name="System Admin"):
    ensure_accounts_indexes_once()
    parsed, err = _validate_user_input(full_name, email, role, department, batch)
    if err:
        return None, err
    clean_name, clean_email, clean_role, clean_dept, clean_batch = parsed
    if len(str(password or "")) < 6:
        return None, "Password must be at least 6 characters long."
    col = users_col()
    if col.find_one({"email": clean_email}, {"_id": 1}) is not None:
        return None, "A user with this email already exists."

    user_id = generate_unique_user_id(col)
    student_id = generate_unique_student_id(student_records_col(), user_id) if clean_role == "STUDENT" else None
    doc = {"user_id": user_id, "full_name": clean_name, "email": clean_email, "password_hash": make_password(password), "role": clean_role, "department": clean_dept, "batch": clean_batch, "is_active": True, "created_at": datetime.now(timezone.utc), **({"student_id": student_id} if student_id else {})}
    try:
        col.insert_one(doc)
    except DuplicateKeyError:
        return None, "A user with this email already exists."

    _audit("USERS", "CREATE_USER", f"Created user {clean_name} ({user_id}, {clean_role}).", "SUCCESS", actor=actor_name)
    invalidate_cache()
    return doc, None


def update_user_record(user_id, full_name, email, role, department, batch, password="", actor_user_id=None, actor_email="", actor_name="System Admin"):
    col, clean_uid = users_col(), str(user_id or "").strip()
    existing = col.find_one({"user_id": clean_uid})
    if existing is None:
        return False, "User record not found."
    parsed, err = _validate_user_input(full_name, email, role, department, batch)
    if err:
        return False, err
    clean_name, clean_email, clean_role, clean_dept, clean_batch = parsed
    if _is_self_target(existing, clean_uid, actor_user_id, actor_email) and clean_role != "ADMIN":
        return False, "You cannot change your own active ADMIN role."
    if col.find_one({"email": clean_email, "user_id": {"$ne": clean_uid}}, {"_id": 1}) is not None:
        return False, "Another user already uses this email address."
    if password and len(password) < 6:
        return False, "New password must be at least 6 characters long."

    updates = {"full_name": clean_name, "email": clean_email, "role": clean_role, "department": clean_dept, "batch": clean_batch}
    if password:
        updates["password_hash"] = make_password(password)
    if clean_role == "STUDENT" and not existing.get("student_id"):
        updates["student_id"] = generate_unique_student_id(student_records_col(), clean_uid)
    col.update_one({"_id": existing["_id"]}, {"$set": updates})
    _audit("USERS", "UPDATE_USER", f"Updated user {clean_uid} ({clean_role}).", "INFO", actor=actor_name)
    invalidate_cache()
    return True, None


def toggle_user_status(user_id, actor_user_id=None, actor_email="", actor_name="System Admin"):
    clean_uid, col = str(user_id or "").strip(), users_col()
    existing = col.find_one({"user_id": clean_uid})
    if _is_self_target(existing, clean_uid, actor_user_id, actor_email):
        return None, "You cannot deactivate your own active admin account."
    if existing is None:
        return None, "User record not found."
    new_state = not bool(existing.get("is_active", True))
    is_pending_approve = new_state and str(existing.get("approval_status") or "").upper() == "PENDING"
    col.update_one({"_id": existing["_id"]}, {"$set": {"is_active": True, "approval_status": "APPROVED"} if is_pending_approve else {"is_active": new_state}})
    if is_pending_approve:
        _audit("USERS", "APPROVE_USER", f"Approved teacher account {clean_uid}.", "SUCCESS", actor=actor_name)
        create_notification("Account Approved", "Your EduPredict Teacher account has been approved by Admin. You can sign in now.", severity="SUCCESS", target_user_id=clean_uid, category="APPROVAL")
    else:
        _audit("USERS", "TOGGLE_USER", f"{'Activated' if new_state else 'Deactivated'} user {clean_uid}.", "SUCCESS" if new_state else "WARNING", actor=actor_name)
    invalidate_cache()
    return new_state, None


def delete_user_record(user_id, actor_user_id=None, actor_email="", actor_name="System Admin"):
    clean_uid, col = str(user_id or "").strip(), users_col()
    existing = col.find_one({"user_id": clean_uid}, {"_id": 1, "email": 1})
    if _is_self_target(existing, clean_uid, actor_user_id, actor_email):
        return False, "You cannot delete your own active admin account."
    if col.delete_one({"user_id": clean_uid}).deleted_count:
        _audit("USERS", "DELETE_USER", f"Deleted user {clean_uid}.", "DANGER", actor=actor_name)
        invalidate_cache()
        return True, None
    return False, "User record not found."


def _load_courses_with_stats(clean_dept):
    ensure_admin_seed_data()
    enrolled_map = {str(r.get("_id") or "").strip().upper(): int(r.get("count") or 0) for r in student_records_col().aggregate([{"$group": {"_id": "$course_code", "count": {"$sum": 1}}}]) if r.get("_id")}
    all_courses, dept_counts = [], {"ALL": 0}
    for doc in courses_col().find({}, {"_id": 0}).sort("course_code", ASCENDING):
        code, dept = str(doc.get("course_code") or "").strip().upper(), str(doc.get("department") or "General").strip()
        cap, enrolled = _safe_int(doc.get("capacity"), 60, 1, 2000), enrolled_map.get(code, 0)
        dept_counts["ALL"] += 1
        dept_counts[dept] = dept_counts.get(dept, 0) + 1
        all_courses.append({"course_code": code, "title": str(doc.get("title") or ""), "department": dept, "batch": str(doc.get("batch") or "2026-A"), "instructor": str(doc.get("instructor") or "TBA"), "credits": _safe_int(doc.get("credits"), 3, 1, 12), "capacity": cap, "enrolled_count": enrolled, "fill_pct": min(100, round((enrolled * 100) / cap)) if cap else 0, "status": str(doc.get("status") or "ACTIVE").upper(), "created_at_str": _format_dt(doc.get("created_at"))})
    departments = sorted([d for d in dept_counts if d != "ALL"])
    return (all_courses if clean_dept == "ALL" else [c for c in all_courses if c["department"] == clean_dept]), departments, dept_counts


def list_courses_with_stats(dept_filter="ALL"):
    clean_dept = str(dept_filter or "ALL").strip()
    return get_cached(f"admin:courses:{clean_dept}", lambda: _load_courses_with_stats(clean_dept), ttl=30.0)


def _course_fields(title, department, batch, instructor, credits, capacity, status, fallback=None):
    fb, clean_status = fallback or {}, str(status or "ACTIVE").strip().upper()
    return {"title": str(title or "").strip(), "department": str(department or "").strip() or fb.get("department") or "General", "batch": str(batch or "").strip() or fb.get("batch") or "2026-A", "instructor": str(instructor or "").strip() or fb.get("instructor") or "TBA", "credits": _safe_int(credits, 3, 1, 12), "capacity": _safe_int(capacity, 60, 1, 2000), "status": clean_status if clean_status in VALID_COURSE_STATUSES else "ACTIVE"}


def create_course_record(course_code, title, department, batch, instructor, credits, capacity, status="ACTIVE", actor_name="System Admin"):
    clean_code, clean_title = str(course_code or "").strip().upper(), str(title or "").strip()
    if len(clean_code) < 2 or not clean_title:
        return None, "Course code and title are required."
    col = courses_col()
    if col.find_one({"course_code": clean_code}, {"_id": 1}) is not None:
        return None, f"Course {clean_code} already exists."
    doc = {"course_code": clean_code, "created_at": datetime.now(timezone.utc), **_course_fields(title, department, batch, instructor, credits, capacity, status)}
    col.insert_one(doc)
    _audit("COURSES", "CREATE_COURSE", f"Added course {clean_code} ({clean_title}).", "SUCCESS", actor=actor_name)
    invalidate_cache()
    return doc, None


def update_course_record(course_code, title, department, batch, instructor, credits, capacity, status="ACTIVE", actor_name="System Admin"):
    clean_code, clean_title = str(course_code or "").strip().upper(), str(title or "").strip()
    if not clean_code or not clean_title:
        return False, "Course code and title are required."
    col = courses_col()
    existing = col.find_one({"course_code": clean_code})
    if existing is None:
        return False, "Course record not found."
    updates = {**_course_fields(title, department, batch, instructor, credits, capacity, status, fallback=existing), "updated_at": datetime.now(timezone.utc)}
    col.update_one({"_id": existing["_id"]}, {"$set": updates})
    _audit("COURSES", "UPDATE_COURSE", f"Updated course {clean_code} ({clean_title}).", "INFO", actor=actor_name)
    invalidate_cache()
    return True, None


def delete_course_record(course_code, actor_name="System Admin"):
    clean_code = str(course_code or "").strip().upper()
    if courses_col().delete_one({"course_code": clean_code}).deleted_count:
        _audit("COURSES", "DELETE_COURSE", f"Removed course {clean_code}.", "DANGER", actor=actor_name)
        invalidate_cache()
        return True, None
    return False, "Course record not found."


def _load_tickets(clean_status):
    ensure_admin_seed_data()
    counts, tickets = {"ALL": 0, "OPEN": 0, "RESOLVED": 0}, []
    for doc in support_tickets_col().find({}, {"_id": 0}).sort("created_at", DESCENDING):
        status = str(doc.get("status") or "OPEN").strip().upper()
        counts["ALL"] += 1
        if status in counts:
            counts[status] += 1
        if clean_status not in VALID_TICKET_STATUSES or status == clean_status:
            tickets.append({"ticket_id": str(doc.get("ticket_id") or ""), "user_id": str(doc.get("user_id") or ""), "user_name": str(doc.get("user_name") or "User"), "role": str(doc.get("role") or "USER").upper(), "subject": str(doc.get("subject") or ""), "message": str(doc.get("message") or ""), "status": status, "admin_reply": str(doc.get("admin_reply") or ""), "replied_by": str(doc.get("replied_by") or ""), "replied_at_str": _format_dt(doc.get("replied_at")) if doc.get("replied_at") else "", "created_at_str": _format_dt(doc.get("created_at")), "attachments": [str(a) for a in (doc.get("attachments") or []) if a]})
    return tickets, counts


def list_tickets(status_filter="ALL"):
    clean_status = str(status_filter or "ALL").strip().upper()
    return get_cached(f"admin:tickets:{clean_status}", lambda: _load_tickets(clean_status), ttl=30.0)


def _clean_ticket_attachments(attachments, user_id):
    clean = []
    for idx, item in enumerate(attachments or []):
        if len(clean) >= 3:
            break
        if isinstance(item, str):
            val = item.strip()
            if val.lower().startswith(("https://", "http://", "data:image/")):
                clean.append(val)
        elif item is not None:
            url = upload_ticket_attachment(item, user_id, index=idx)[0] if is_cloudinary_configured() else encode_image_data_uri(item)
            if url:
                clean.append(url)
    return clean[:3]


def create_ticket_record(user_id, user_name, role, subject, message, attachments=None):
    clean_subject, clean_message = str(subject or "").strip(), str(message or "").strip()
    if not clean_subject or not clean_message:
        return None, "Subject and message details are required."
    col, uid = support_tickets_col(), str(user_id or "")
    doc = {"ticket_id": _generate_unique_ticket_id(col), "user_id": uid, "user_name": str(user_name or "Portal User").strip() or "Portal User", "role": str(role or "USER").strip().upper(), "subject": clean_subject, "message": clean_message, "attachments": _clean_ticket_attachments(attachments, uid)[:3], "status": "OPEN", "created_at": datetime.now(timezone.utc)}
    col.insert_one(doc)
    create_notification(f"New Ticket {doc['ticket_id']}: {clean_subject}", clean_message, severity="WARNING", target_role="ADMIN", category="TICKET", ticket_id=doc["ticket_id"], feedback_text=clean_message)
    _audit("TICKETS", "CREATE_TICKET", f"Support ticket {doc['ticket_id']} submitted by {doc['user_name']}: {clean_subject}", "WARNING", actor=doc["user_name"])
    invalidate_cache()
    return doc, None


def toggle_ticket_status(ticket_id, actor_name="System Admin"):
    col = support_tickets_col()
    existing = col.find_one({"ticket_id": str(ticket_id or "").strip()})
    if existing is None:
        return None, "Support ticket not found."
    new_status = "RESOLVED" if str(existing.get("status") or "OPEN").strip().upper() == "OPEN" else "OPEN"
    col.update_one({"_id": existing["_id"]}, {"$set": {"status": new_status, "updated_at": datetime.now(timezone.utc)}})
    tid = str(existing.get("ticket_id") or ticket_id)
    if existing.get("user_id"):
        create_notification(f"Ticket {tid} {new_status}", f"Your support ticket \"{existing.get('subject', '')}\" is now {new_status}.", severity="SUCCESS" if new_status == "RESOLVED" else "INFO", target_user_id=str(existing.get("user_id") or ""), category="TICKET_STATUS", ticket_id=tid)
    _audit("TICKETS", "TOGGLE_TICKET", f"Ticket {tid} marked as {new_status}.", "SUCCESS" if new_status == "RESOLVED" else "WARNING", actor=actor_name)
    invalidate_cache()
    return new_status, None


def delete_ticket_record(ticket_id, actor_name="System Admin"):
    clean_tid = str(ticket_id or "").strip()
    if support_tickets_col().delete_one({"ticket_id": clean_tid}).deleted_count:
        _audit("TICKETS", "DELETE_TICKET", f"Deleted support ticket {clean_tid}.", "DANGER", actor=actor_name)
        invalidate_cache()
        return True, None
    return False, "Support ticket not found."


def mark_notifications_read(user_doc):
    user = user_doc if isinstance(user_doc, dict) else {}
    user_id, student_id, active_role = str(user.get("user_id") or "").strip(), str(user.get("student_id") or "").strip(), str(user.get("role") or "").strip().upper()
    if not user_id and not student_id and not active_role:
        return 0
    targets = [{"target_user_id": tid} for tid in dict.fromkeys(x for x in (user_id, student_id) if x)]
    for target_role in dict.fromkeys(r for r in (active_role, "ALL") if r):
        targets.extend([{"target_role": target_role, "target_user_id": {"$in": [None, ""]}}, {"target_role": target_role, "target_user_id": {"$exists": False}}])
    modified = int(notifications_col().update_many({"is_read": False, "$or": targets}, {"$set": {"is_read": True}}).modified_count)
    invalidate_cache()
    return modified


def _action(label, icon, onclick, title, attrs, variant="default"):
    return {"label": label, "icon": icon, "variant": variant, "title": title, "onclick": onclick, "attrs": attrs}


def build_user_table_data(users, filter_role, actor_user_id, actor_email=""):
    headers, role_status_map = ["User ID", "Full Name", "Email", "Role", "Department", "Status", "Actions"], {"ADMIN": "info", "ANALYST": "info", "TEACHER": "warning", "STUDENT": "success"}
    clean_actor_email, rows = str(actor_email or "").strip().lower(), []
    for u in users:
        uid = u["user_id"]
        is_self = (actor_user_id and uid == actor_user_id) or (clean_actor_email and u["email"].strip().lower() == clean_actor_email)
        edit_attrs = {"data-user-id": uid, "data-full-name": u["full_name"], "data-email": u["email"], "data-role": u["role"], "data-department": u["department"], "data-batch": u["batch"], "data-filter-role": filter_role, **({"data-is-self": "true"} if is_self else {})}
        actions = [_action("Edit", "fa-solid fa-pen-to-square", "openEditUserModal(this)", f"Edit {u['full_name']}", edit_attrs)]
        if not is_self:
            lbl, ico = ("Deactivate", "fa-solid fa-user-slash") if u["is_active"] else ("Activate", "fa-solid fa-user-check")
            actions += [_action(lbl, ico, "openToggleUserModal(this)", f"{lbl} {u['full_name']}", {"data-user-id": uid, "data-full-name": u["full_name"], "data-is-active": "true" if u["is_active"] else "false", "data-filter-role": filter_role}), _action("Delete", "fa-solid fa-trash", "openDeleteUserModal(this)", f"Delete {u['full_name']}", {"data-user-id": uid, "data-full-name": u["full_name"], "data-filter-role": filter_role}, variant="danger")]
        display_name = f"{u['full_name']} (You)" if is_self else u["full_name"]
        rows.append([uid, display_name, u["email"], {"text": u["role"], "status": role_status_map.get(u["role"], "info")}, u["department"], {"text": "Active" if u["is_active"] else "Inactive", "status": "success" if u["is_active"] else "danger"}, {"actions": actions}])
    return headers, rows


def build_course_table_data(courses, filter_dept):
    headers, rows = ["Code", "Course Title", "Department", "Batch", "Instructor", "Enrolled", "Status", "Actions"], []
    for c in courses:
        actions = [_action("Edit", "fa-solid fa-pen-to-square", "openEditCourseModal(this)", f"Edit {c['course_code']}", {"data-course-code": c["course_code"], "data-title": c["title"], "data-department": c["department"], "data-batch": c["batch"], "data-instructor": c["instructor"], "data-credits": str(c["credits"]), "data-capacity": str(c["capacity"]), "data-status": c["status"], "data-filter-dept": filter_dept}), _action("Delete", "fa-solid fa-trash", "openDeleteCourseModal(this)", f"Delete {c['course_code']}", {"data-course-code": c["course_code"], "data-title": c["title"], "data-filter-dept": filter_dept}, variant="danger")]
        rows.append([c["course_code"], c["title"], c["department"], c["batch"], c["instructor"], f"{c['enrolled_count']} / {c['capacity']} ({c['fill_pct']}%)", {"text": c["status"], "status": "success" if c["status"] == "ACTIVE" else "warning"}, {"actions": actions}])
    return headers, rows


def build_ticket_table_data(tickets, filter_status):
    headers, rows = ["Ticket ID", "User", "Role", "Subject", "Status", "Date", "Actions"], []
    for t in tickets:
        is_open, has_reply = t["status"] == "OPEN", bool(t.get("admin_reply"))
        lbl, ico = ("Resolve", "fa-solid fa-circle-check") if is_open else ("Reopen", "fa-solid fa-rotate-left")
        attachments, created_at = [str(a) for a in (t.get("attachments") or []) if a], t.get("created_at_str") or t.get("created_at", "")
        base_attrs = {"data-ticket-id": t["ticket_id"], "data-subject": t["subject"], "data-filter-status": filter_status}
        detail_attrs = {**base_attrs, "data-message": t["message"], "data-admin-reply": t.get("admin_reply", ""), "data-status": t["status"], "data-attachments": "|".join(attachments), "data-user-name": t.get("user_name", ""), "data-role": t.get("role", ""), "data-created-at": created_at, "data-replied-by": t.get("replied_by", ""), "data-replied-at": t.get("replied_at_str") or t.get("replied_at", "")}
        actions = [_action("View", "fa-solid fa-eye", "openTicketDetailDrawer(this)", f"View {t['ticket_id']}", detail_attrs), _action("Edit" if has_reply else "Reply", "fa-solid fa-reply", "openReplyTicketModal(this)", f"Reply to {t['ticket_id']}", detail_attrs, variant="primary")]
        if has_reply:
            actions.append(_action("Clear", "fa-solid fa-comment-slash", "openDeleteReplyModal(this)", f"Delete reply on {t['ticket_id']}", base_attrs, variant="danger"))
        actions.extend([_action(lbl, ico, "openToggleTicketModal(this)", f"{lbl} {t['ticket_id']}", {**base_attrs, "data-status": t["status"]}), _action("", "fa-solid fa-trash", "openDeleteTicketModal(this)", f"Delete ticket {t['ticket_id']}", {**base_attrs, "aria-label": f"Delete ticket {t['ticket_id']}"}, variant="danger")])
        subject_cell = (f"{t['subject']} (Replied)" if has_reply else t["subject"]) + (f" [{len(attachments)} img]" if attachments else "")
        rows.append([t["ticket_id"], t["user_name"], {"text": t["role"], "status": "info"}, subject_cell, {"text": t["status"], "status": "success" if t["status"] == "RESOLVED" else "warning"}, created_at, {"actions": actions}])
    return headers, rows
