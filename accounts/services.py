import os
import re
import threading
import uuid
from datetime import datetime, timezone
from django.contrib.auth.hashers import check_password, make_password
from pymongo import ASCENDING
from pymongo.errors import DuplicateKeyError
from core.db import courses_col, ensure_indexes, get_cached, invalidate_cache, notifications_col, predictions_col, resolve_portal_branding, student_records_col, support_tickets_col, users_col

VALID_ROLES = ("ADMIN", "TEACHER", "STUDENT", "ANALYST")
SELF_REGISTER_ROLES = ("STUDENT", "TEACHER", "ANALYST")
PROGRAM_LEVELS = (
    "School / Junior",
    "College / Intermediate",
    "BS / Undergraduate",
    "MS / Graduate",
)

_INDEXES_ENSURED = False
_INDEX_LOCK = threading.Lock()
_DEFAULT_ADMIN_ENSURED = False
_DEFAULT_ADMIN_LOCK = threading.Lock()


def ensure_accounts_indexes_once():
    global _INDEXES_ENSURED
    if _INDEXES_ENSURED:
        return True
    with _INDEX_LOCK:
        if _INDEXES_ENSURED:
            return True
        if ensure_indexes():
            _INDEXES_ENSURED = True
            return True
        return False


def ensure_default_admin():
    global _DEFAULT_ADMIN_ENSURED
    if _DEFAULT_ADMIN_ENSURED:
        return None
    with _DEFAULT_ADMIN_LOCK:
        if _DEFAULT_ADMIN_ENSURED:
            return None

        admin_email = (os.getenv("ADMIN_EMAIL") or "admin@gmail.com").strip().lower() or "admin@gmail.com"
        admin_password = os.getenv("ADMIN_PASSWORD") or "admin123"
        admin_full_name = (os.getenv("ADMIN_FULL_NAME") or "System Administrator").strip() or "System Administrator"

        ensure_accounts_indexes_once()
        col = users_col()
        existing = col.find_one({"email": admin_email})
        if existing is None:
            admin_doc = {
                "user_id": "USR-1000",
                "full_name": admin_full_name,
                "email": admin_email,
                "password_hash": make_password(admin_password),
                "role": "ADMIN",
                "department": "Administration",
                "batch": "ALL",
                "is_active": True,
                "created_at": datetime.now(timezone.utc),
            }
            try:
                col.insert_one(admin_doc)
                _DEFAULT_ADMIN_ENSURED = True
                return admin_doc
            except DuplicateKeyError:
                existing = col.find_one({"email": admin_email})
                if existing is None:
                    raise

        updates = {}
        if existing.get("role") != "ADMIN":
            updates["role"] = "ADMIN"
        if existing.get("is_active") is not True:
            updates["is_active"] = True
        if not check_password(admin_password, existing.get("password_hash", "")):
            updates["password_hash"] = make_password(admin_password)
        if updates:
            col.update_one({"_id": existing["_id"]}, {"$set": updates})
            existing.update(updates)
        _DEFAULT_ADMIN_ENSURED = True
        return existing


def serialize_session_user(user_doc):
    role = str(user_doc.get("role") or "").strip().upper()
    session_user = {
        "user_id": str(user_doc.get("user_id") or ""),
        "full_name": str(user_doc.get("full_name") or ""),
        "email": str(user_doc.get("email") or "").strip().lower(),
        "role": role,
        "department": str(user_doc.get("department") or ""),
        "batch": str(user_doc.get("batch") or ""),
        "program_level": str(user_doc.get("program_level") or ""),
        "phone": str(user_doc.get("phone") or ""),
        "bio": str(user_doc.get("bio") or ""),
        "avatar_url": str(user_doc.get("avatar_url") or ""),
        "assigned_teacher_id": str(user_doc.get("assigned_teacher_id") or ""),
        "assigned_teacher_name": str(user_doc.get("assigned_teacher_name") or ""),
        "is_active": bool(user_doc.get("is_active", True)),
        "approval_status": str(user_doc.get("approval_status") or ("APPROVED" if user_doc.get("is_active", True) else "INACTIVE")).upper(),
        "theme_prefs": dict(user_doc.get("theme_prefs")) if isinstance(user_doc.get("theme_prefs"), dict) else {},
    }
    student_id = user_doc.get("student_id")
    if role == "STUDENT":
        session_user["student_id"] = str(student_id or session_user["user_id"])
    elif student_id:
        session_user["student_id"] = str(student_id)
    return session_user


def list_approved_teachers():
    def _fetch():
        try:
            docs = users_col().find({"role": "TEACHER", "is_active": True}, {"_id": 0, "user_id": 1, "full_name": 1, "department": 1, "email": 1}).sort("full_name", ASCENDING)
            return [{"user_id": str(d.get("user_id") or ""), "full_name": str(d.get("full_name") or ""), "department": str(d.get("department") or "General"), "email": str(d.get("email") or "")} for d in docs if d.get("user_id")]
        except Exception:
            return []
    return get_cached("admin:approved_teachers", _fetch, ttl=20.0)


def generate_unique_user_id(col):
    base = 1001 + col.count_documents({})
    for offset in range(25):
        candidate = f"USR-{base + offset}"
        if col.find_one({"user_id": candidate}, {"_id": 1}) is None:
            return candidate
    return f"USR-{uuid.uuid4().hex[:6].upper()}"


def generate_unique_student_id(records_col, user_id):
    year = datetime.now(timezone.utc).year
    suffix = str(user_id).split("-")[-1]
    candidate = f"STD-{year}-{suffix}"
    if records_col.find_one({"student_id": candidate}, {"_id": 1}) is None:
        return candidate
    return f"STD-{year}-{uuid.uuid4().hex[:4].upper()}"


def authenticate_user(identifier, password):
    ensure_default_admin()
    raw_id = str(identifier or "").strip()
    if not raw_id:
        return None, "Invalid email/student ID or password."
    col, lower_id, upper_id = users_col(), raw_id.lower(), raw_id.upper()
    user_doc = col.find_one({"email": lower_id})
    if user_doc is None:
        for candidate in dict.fromkeys((raw_id, upper_id, lower_id)):
            user_doc = col.find_one({"student_id": candidate})
            if user_doc is not None:
                break
    if user_doc is None:
        try:
            user_doc = col.find_one({"student_id": {"$regex": f"^{re.escape(raw_id)}$", "$options": "i"}})
        except Exception:
            user_doc = None
    if user_doc is None:
        return None, "Invalid email/student ID or password."
    role = str(user_doc.get("role") or "").strip().upper()
    role_label = "student" if role == "STUDENT" else "teacher"
    approval_status = str(user_doc.get("approval_status") or "").strip().upper()
    if approval_status == "PENDING":
        return None, f"Your {role_label} account is pending Admin approval. Please wait until an administrator approves your account."
    if approval_status == "REJECTED":
        reason = str(user_doc.get("rejection_reason") or "").strip()
        return None, (f"Your {role_label} account request was rejected by Admin. Reason: {reason}" if reason else f"Your {role_label} account request was rejected by Admin.")
    if not user_doc.get("is_active", True):
        return None, "Your account is inactive. Please contact an administrator."
    if not check_password(password, user_doc.get("password_hash", "")):
        return None, "Invalid email/student ID or password."
    if role not in VALID_ROLES:
        return None, "Account role is invalid. Please contact an administrator."
    return user_doc, None


def register_user(full_name, email, password, role, department, batch, phone="", bio="", program_level="", assigned_teacher_id="", assigned_teacher_name=""):
    normalized_role = str(role or "").strip().upper()
    if normalized_role not in SELF_REGISTER_ROLES:
        return None, "Administrator accounts can only be created by an existing Admin."
    ensure_accounts_indexes_once()
    col, normalized_email = users_col(), email.strip().lower()
    if col.find_one({"email": normalized_email}, {"_id": 1}) is not None:
        return None, "An account with this email already exists."

    resolved_department = department.strip() or "General"
    resolved_batch = batch.strip() or ("2026" if normalized_role == "STUDENT" else "ALL")
    raw_level = str(program_level or "").strip()
    resolved_program_level = raw_level if raw_level in PROGRAM_LEVELS else ""
    clean_teacher_id = str(assigned_teacher_id or "").strip()
    clean_teacher_name = str(assigned_teacher_name or "").strip()
    if normalized_role == "STUDENT" and clean_teacher_id:
        teacher_doc = col.find_one({"user_id": clean_teacher_id, "role": "TEACHER", "is_active": True}, {"_id": 0, "user_id": 1, "full_name": 1})
        if teacher_doc is None:
            return None, "Please select a valid approved Teacher."
        clean_teacher_name = str(teacher_doc.get("full_name") or clean_teacher_name).strip()

    user_id = generate_unique_user_id(col)
    needs_approval = normalized_role in ("TEACHER", "STUDENT")
    user_doc = {
        "user_id": user_id,
        "full_name": full_name.strip(),
        "email": normalized_email,
        "password_hash": make_password(password),
        "role": normalized_role,
        "department": resolved_department,
        "batch": resolved_batch,
        "program_level": resolved_program_level,
        "phone": str(phone or "").strip(),
        "bio": str(bio or "").strip(),
        "is_active": not needs_approval,
        "approval_status": "PENDING" if needs_approval else "APPROVED",
        "created_at": datetime.now(timezone.utc),
    }

    if normalized_role == "STUDENT":
        user_doc["student_id"] = generate_unique_student_id(student_records_col(), user_id)
        if clean_teacher_id:
            user_doc["assigned_teacher_id"] = clean_teacher_id
            user_doc["assigned_teacher_name"] = clean_teacher_name

    try:
        col.insert_one(user_doc)
    except DuplicateKeyError:
        return None, "An account with this email already exists."

    if needs_approval:
        try:
            role_title = "Teacher" if normalized_role == "TEACHER" else "Student"
            teacher_note = f", Teacher: {clean_teacher_name}" if clean_teacher_name else ""
            notifications_col().insert_one({"title": f"{role_title} Approval Needed", "message": f"{full_name.strip()} ({normalized_email}, {resolved_department}{teacher_note}) registered as {role_title} and is waiting for Admin approval.", "severity": "WARNING", "category": "APPROVAL", "target_role": "ADMIN", "is_read": False, "created_at": datetime.now(timezone.utc)})
            invalidate_cache("notifs:")
        except Exception:
            pass

    invalidate_cache("admin:")
    invalidate_cache("soon:")
    invalidate_cache("public:")
    return user_doc, None


def _safe_count(col_fn):
    try:
        return max(int(col_fn().count_documents({})), 0)
    except Exception:
        return 0


def get_public_portal_metrics():
    def _fetch():
        inst_name, current_term = resolve_portal_branding(db_connected=True)
        return {
            "institution_name": inst_name,
            "current_term": current_term,
            "users_count": _safe_count(users_col),
            "students_count": _safe_count(student_records_col),
            "teachers_count": int(users_col().count_documents({"role": "TEACHER"})) if callable(users_col) else 0,
            "courses_count": _safe_count(courses_col),
            "records_count": _safe_count(student_records_col),
            "predictions_count": _safe_count(predictions_col),
        }

    return get_cached("public:portal_metrics", _fetch, ttl=60.0)


def get_public_admin_contact():
    def _fetch():
        inst_name, current_term = resolve_portal_branding(db_connected=True)
        proj = {"_id": 0, "full_name": 1, "email": 1, "department": 1, "phone": 1}
        try:
            admin_doc = users_col().find_one({"role": "ADMIN", "is_active": True}, proj) or users_col().find_one({"role": "ADMIN"}, proj)
        except Exception:
            admin_doc = None
        doc = admin_doc if isinstance(admin_doc, dict) else {}
        return {"institution_name": inst_name, "current_term": current_term, "full_name": str(doc.get("full_name") or "System Administrator").strip() or "System Administrator", "email": str(doc.get("email") or "admin@gmail.com").strip() or "admin@gmail.com", "department": str(doc.get("department") or "Administration").strip() or "Administration", "phone": str(doc.get("phone") or "").strip()}
    return get_cached("public:admin_contact", _fetch, ttl=60.0)


def _generate_public_ticket_id(col):
    base = 1001 + int(col.count_documents({}))
    for offset in range(25):
        candidate = f"TCK-{base + offset}"
        if col.find_one({"ticket_id": candidate}, {"_id": 1}) is None:
            return candidate
    return f"TCK-{uuid.uuid4().hex[:6].upper()}"


def create_public_contact_ticket(name, email, subject, message):
    clean_name, clean_email = str(name or "").strip(), str(email or "").strip().lower()
    clean_subject, clean_message = str(subject or "").strip(), str(message or "").strip()
    if not clean_name or not clean_email or not clean_subject or not clean_message:
        return None, "All fields are required."
    try:
        col, now = support_tickets_col(), datetime.now(timezone.utc)
        ticket_id = _generate_public_ticket_id(col)
        doc = {"ticket_id": ticket_id, "user_id": "GUEST", "user_name": clean_name, "email": clean_email, "role": "GUEST", "subject": clean_subject, "message": f"[Public Contact: {clean_email}] {clean_message}", "attachments": [], "status": "OPEN", "source": "PUBLIC_CONTACT", "created_at": now}
        col.insert_one(doc)
        try:
            notifications_col().insert_one({"title": f"New Contact {ticket_id}: {clean_subject}", "message": f"{clean_name} ({clean_email}): {clean_message}", "severity": "WARNING", "category": "TICKET", "target_role": "ADMIN", "ticket_id": ticket_id, "is_read": False, "created_at": now})
            invalidate_cache("notifs:")
        except Exception:
            pass
        invalidate_cache("admin:")
        invalidate_cache("public:")
        return doc, None
    except Exception:
        return None, "Unable to save your inquiry right now. Please try again."
