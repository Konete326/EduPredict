import uuid
from datetime import datetime, timezone
from django.contrib.auth.hashers import make_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from pymongo import ASCENDING, DESCENDING
from pymongo.errors import DuplicateKeyError
from accounts.services import VALID_ROLES, ensure_accounts_indexes_once, generate_unique_student_id, generate_unique_user_id
from analytics.data_pipeline import ingest_dataset
from analytics.ml_engine import run_prediction_pipeline
from core.cloudinary_services import encode_image_data_uri, is_cloudinary_configured, upload_ticket_attachment
from core.db import datasets_log_col, get_cached, invalidate_cache, notifications_col, predictions_col, student_records_col, support_tickets_col, users_col
from panels.admin_audit_services import record_audit_log
from panels.admin_seed import _format_dt, _infer_department_from_code, _safe_int, build_backup_payload, courses_col, ensure_admin_seed_data, get_admin_overview_context as _base_admin_overview
from panels.notification_services import create_notification
from panels.phase62_services import reject_teacher_account
VALID_TICKET_STATUSES, VALID_COURSE_STATUSES = ("OPEN", "RESOLVED"), ("ACTIVE", "ARCHIVED")
VALID_PROGRAM_LEVELS = ("School / Junior", "College / Intermediate", "BS / Undergraduate", "MS / Graduate")
LIVE_RECORD_QUERY = {"is_training_dataset": {"$ne": True}}
def _load_live_admin_overview():
    base = _base_admin_overview()
    kpis, charts = dict(base.get("kpis") or {}), {k: dict(v) for k, v in (base.get("chart_data") or {}).items()}
    sr_col, u_col, c_col, p_col = student_records_col(), users_col(), courses_col(), predictions_col()
    live_sr_count, student_accounts = sr_col.count_documents(LIVE_RECORD_QUERY), int(kpis.get("student_accounts") or u_col.count_documents({"role": "STUDENT"}))
    course_dept_map, dept_capacity = {}, {}
    for c in c_col.find({}, {"_id": 0, "course_code": 1, "department": 1, "capacity": 1}):
        code, dept = str(c.get("course_code") or "").strip().upper(), str(c.get("department") or "General").strip()
        if code: course_dept_map[code] = dept
        dept_capacity[dept] = dept_capacity.get(dept, 0) + _safe_int(c.get("capacity"), 60, 0, 10000)
    dept_enrolled, att_sum, att_count = {d: 0 for d in dept_capacity}, 0.0, 0
    for rec in sr_col.find(LIVE_RECORD_QUERY, {"_id": 0, "course_code": 1, "attendance_pct": 1}):
        code = str(rec.get("course_code") or "").strip().upper()
        dept = course_dept_map.get(code) or _infer_department_from_code(code)
        dept_enrolled[dept] = dept_enrolled.get(dept, 0) + 1
        try:
            att_sum, att_count = att_sum + float(rec.get("attendance_pct") or 0.0), att_count + 1
        except (TypeError, ValueError):
            pass
    if att_count == 0:
        for usr in u_col.find({"role": "STUDENT"}, {"_id": 0, "department": 1}):
            dept = str(usr.get("department") or "General").strip()
            dept_enrolled[dept] = dept_enrolled.get(dept, 0) + 1
    dept_labels = sorted(set(dept_capacity.keys()) | set(dept_enrolled.keys()))
    low_r, med_r, high_r = p_col.count_documents({**LIVE_RECORD_QUERY, "risk_level": "LOW"}), p_col.count_documents({**LIVE_RECORD_QUERY, "risk_level": "MEDIUM"}), p_col.count_documents({**LIVE_RECORD_QUERY, "risk_level": "HIGH"})
    kpis.update({"total_students": live_sr_count if live_sr_count > 0 else student_accounts, "avg_attendance": round(att_sum / att_count, 1) if att_count > 0 else 0.0, "high_risk_count": high_r, "total_predictions": p_col.count_documents(LIVE_RECORD_QUERY)})
    charts["departments"] = {"labels": dept_labels, "enrolled": [dept_enrolled.get(d, 0) for d in dept_labels], "capacity": [dept_capacity.get(d, 0) for d in dept_labels]}
    charts["risk_breakdown"] = {"labels": ["Low Risk", "Medium Risk", "High Risk"], "counts": [low_r, med_r, high_r]}
    return {**base, "kpis": kpis, "chart_data": charts}
def get_admin_overview_context(): return get_cached("admin:overview:live", _load_live_admin_overview, ttl=30.0)
def _audit(category, action, summary, severity="INFO", actor="System Admin"):
    try: record_audit_log(actor, "ADMIN", category, action, summary, severity=severity, source="SYSTEM")
    except Exception: pass
def _generate_unique_ticket_id(col):
    base = 1001 + col.count_documents({})
    for offset in range(30):
        candidate = f"TKT-{base + offset}"
        if col.find_one({"ticket_id": candidate}, {"_id": 1}) is None: return candidate
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
        if role in role_counts: role_counts[role] += 1
        if approval_status in ("PENDING", "REJECTED"): role_counts[approval_status] += 1
        if normalized == "ALL" or (normalized in ("PENDING", "REJECTED") and approval_status == normalized) or role == normalized:
            users.append({"user_id": str(doc.get("user_id") or ""), "full_name": str(doc.get("full_name") or ""), "email": str(doc.get("email") or ""), "role": role, "department": str(doc.get("department") or "General"), "batch": str(doc.get("batch") or "ALL"), "program_level": str(doc.get("program_level") or ("BS / Undergraduate" if role == "STUDENT" else "")), "phone": str(doc.get("phone") or ""), "bio": str(doc.get("bio") or ""), "is_active": is_active, "approval_status": approval_status, "rejection_reason": str(doc.get("rejection_reason") or ""), "student_id": str(doc.get("student_id") or ""), "assigned_teacher_id": str(doc.get("assigned_teacher_id") or ""), "assigned_teacher_name": str(doc.get("assigned_teacher_name") or ""), "avatar_url": str(doc.get("avatar_url") or ""), "created_at_str": _format_dt(doc.get("created_at"))})
    return users, role_counts
def list_users(role_filter="ALL"):
    normalized = str(role_filter or "ALL").strip().upper()
    return get_cached(f"admin:users:{normalized}", lambda: _load_users(normalized), ttl=30.0)
def _validate_user_input(full_name, email, role, department, batch):
    clean_name, clean_email, clean_role = str(full_name or "").strip(), str(email or "").strip().lower(), str(role or "").strip().upper()
    if not clean_name: return None, "Full name is required."
    try: validate_email(clean_email)
    except ValidationError: return None, "Please enter a valid email address."
    if clean_role not in VALID_ROLES: return None, "Select a valid role (ADMIN, TEACHER, STUDENT, or ANALYST)."
    return (clean_name, clean_email, clean_role, str(department or "").strip() or "General", str(batch or "").strip() or ("2026-A" if clean_role == "STUDENT" else "ALL")), None
def create_user_record(full_name, email, password, role, department, batch, actor_name="System Admin", program_level=""):
    ensure_accounts_indexes_once()
    parsed, err = _validate_user_input(full_name, email, role, department, batch)
    if err: return None, err
    clean_name, clean_email, clean_role, clean_dept, clean_batch = parsed
    if len(str(password or "")) < 6: return None, "Password must be at least 6 characters long."
    col = users_col()
    if col.find_one({"email": clean_email}, {"_id": 1}) is not None: return None, "A user with this email already exists."
    user_id = generate_unique_user_id(col)
    student_id = generate_unique_student_id(student_records_col(), user_id) if clean_role == "STUDENT" else None
    clean_level = str(program_level or "").strip() or ("BS / Undergraduate" if clean_role == "STUDENT" else "")
    doc = {"user_id": user_id, "full_name": clean_name, "email": clean_email, "password_hash": make_password(password), "role": clean_role, "department": clean_dept, "batch": clean_batch, "is_active": True, "created_at": datetime.now(timezone.utc), **({"program_level": clean_level} if clean_level else {}), **({"student_id": student_id} if student_id else {})}
    try: col.insert_one(doc)
    except DuplicateKeyError: return None, "A user with this email already exists."
    _audit("USERS", "CREATE_USER", f"Created user {clean_name} ({user_id}, {clean_role}).", "SUCCESS", actor=actor_name)
    invalidate_cache()
    return doc, None
def update_user_record(user_id, full_name, email, role, department, batch, password="", actor_user_id=None, actor_email="", actor_name="System Admin", program_level=None):
    col, clean_uid = users_col(), str(user_id or "").strip()
    existing = col.find_one({"user_id": clean_uid})
    if existing is None: return False, "User record not found."
    parsed, err = _validate_user_input(full_name, email, role, department, batch)
    if err: return False, err
    clean_name, clean_email, clean_role, clean_dept, clean_batch = parsed
    if _is_self_target(existing, clean_uid, actor_user_id, actor_email) and clean_role != "ADMIN": return False, "You cannot change your own active ADMIN role."
    if col.find_one({"email": clean_email, "user_id": {"$ne": clean_uid}}, {"_id": 1}) is not None: return False, "Another user already uses this email address."
    if password and len(password) < 6: return False, "New password must be at least 6 characters long."
    updates = {"full_name": clean_name, "email": clean_email, "role": clean_role, "department": clean_dept, "batch": clean_batch}
    if program_level is not None: updates["program_level"] = str(program_level or "").strip() or ("BS / Undergraduate" if clean_role == "STUDENT" else "")
    elif clean_role == "STUDENT" and not existing.get("program_level"): updates["program_level"] = "BS / Undergraduate"
    if password: updates["password_hash"] = make_password(password)
    if clean_role == "STUDENT" and not existing.get("student_id"): updates["student_id"] = generate_unique_student_id(student_records_col(), clean_uid)
    col.update_one({"_id": existing["_id"]}, {"$set": updates})
    _audit("USERS", "UPDATE_USER", f"Updated user {clean_uid} ({clean_role}).", "INFO", actor=actor_name)
    invalidate_cache()
    return True, None
def toggle_user_status(user_id, actor_user_id=None, actor_email="", actor_name="System Admin"):
    clean_uid, col = str(user_id or "").strip(), users_col()
    existing = col.find_one({"user_id": clean_uid})
    if _is_self_target(existing, clean_uid, actor_user_id, actor_email): return None, "You cannot deactivate your own active admin account."
    if existing is None: return None, "User record not found."
    new_state = not bool(existing.get("is_active", True))
    is_pending_approve = new_state and str(existing.get("approval_status") or "").upper() == "PENDING"
    col.update_one({"_id": existing["_id"]}, {"$set": {"is_active": True, "approval_status": "APPROVED"} if is_pending_approve else {"is_active": new_state}})
    if is_pending_approve:
        role_label = "Student" if str(existing.get("role") or "").strip().upper() == "STUDENT" else "Teacher"
        _audit("USERS", "APPROVE_USER", f"Approved {role_label.lower()} account {clean_uid}.", "SUCCESS", actor=actor_name)
        create_notification("Account Approved", f"Your EduPredict {role_label} account has been approved by Admin. You can sign in now.", severity="SUCCESS", target_user_id=clean_uid, category="APPROVAL")
    else:
        _audit("USERS", "TOGGLE_USER", f"{'Activated' if new_state else 'Deactivated'} user {clean_uid}.", "SUCCESS" if new_state else "WARNING", actor=actor_name)
    invalidate_cache()
    return new_state, None
def ingest_master_training_dataset(file_obj, actor_name="System Admin", is_training_dataset=True):
    if file_obj is None: return None, "Please select a master training CSV or Excel file."
    ingest_res = ingest_dataset(file_obj=file_obj, uploaded_by=actor_name, mode="upload", is_training_dataset=bool(is_training_dataset))
    if ingest_res.get("status") != "COMPLETED": return None, ingest_res.get("error") or "Master training dataset upload failed."
    pred_res, now = run_prediction_pipeline(persist=True), datetime.now(timezone.utc)
    rows_count, filename = int(ingest_res.get("rows_processed") or 0), str(ingest_res.get("filename") or "master_training.csv")
    try:
        log_col = datasets_log_col()
        latest = next(iter(log_col.find({"filename": filename, "status": "COMPLETED"}).sort("uploaded_at", DESCENDING).limit(1)), None)
        marker = {"is_training_dataset": True, "model_trained": True, "model_version": str(pred_res.get("model_version") or ""), "predictions_generated": int(pred_res.get("predictions_generated") or 0), "trained_at": now}
        if latest and latest.get("_id") is not None: log_col.update_one({"_id": latest["_id"]}, {"$set": marker})
        else: log_col.insert_one({"filename": filename, "uploaded_by": actor_name or "System Admin", "rows_processed": rows_count, "missing_values_fixed": int(ingest_res.get("missing_values_fixed") or 0), "status": "COMPLETED", "uploaded_at": now, **marker})
    except Exception:
        pass
    _audit("DATA", "UPLOAD_MASTER_CSV", f"Uploaded master training CSV {filename} ({rows_count} records) and trained ML models.", "SUCCESS", actor=actor_name)
    invalidate_cache()
    return {"filename": filename, "rows_processed": rows_count, "missing_values_fixed": int(ingest_res.get("missing_values_fixed") or 0), "predictions_generated": int(pred_res.get("predictions_generated") or 0), "high_risk_count": int(pred_res.get("high_risk_count") or 0)}, None
def get_master_training_status():
    def _fetch():
        try:
            log_col = datasets_log_col()
            doc = next(iter(log_col.find({"is_training_dataset": True, "status": "COMPLETED"}, {"_id": 0}).sort("uploaded_at", DESCENDING).limit(1)), None) or next(iter(log_col.find({"status": "COMPLETED"}, {"_id": 0}).sort("uploaded_at", DESCENDING).limit(1)), None)
            pred_count, train_sr = int(predictions_col().count_documents(LIVE_RECORD_QUERY)), int(student_records_col().count_documents({"is_training_dataset": True}))
            return {"trained": bool((doc and doc.get("is_training_dataset")) or (doc and pred_count > 0) or pred_count > 0), "records_count": int((doc or {}).get("rows_processed") or 0) or train_sr or pred_count, "filename": str((doc or {}).get("filename") or ""), "uploaded_at": _format_dt((doc or {}).get("uploaded_at")) if doc else ""}
        except Exception:
            return {"trained": False, "records_count": 0, "filename": "", "uploaded_at": ""}
    return get_cached("admin:ml_status", _fetch, ttl=20.0)
def _load_training_uploads():
    uploads, rows = [], []
    try:
        query = {"$or": [{"is_training_dataset": True}, {"uploaded_by": {"$regex": "admin", "$options": "i"}}]}
        for d in datasets_log_col().find(query, {"_id": 0}).sort("uploaded_at", DESCENDING).limit(20):
            fn, by, rc, preds, st, dt = str(d.get("filename") or "master.csv"), str(d.get("uploaded_by") or "System Admin"), int(d.get("rows_processed") or 0), int(d.get("predictions_generated") or 0), str(d.get("status") or "COMPLETED").upper(), _format_dt(d.get("uploaded_at"))
            uploads.append({"filename": fn, "uploaded_by": by, "rows_processed": rc, "predictions_generated": preds, "status": st, "uploaded_at_str": dt})
            rows.append([fn, by, rc, preds, {"text": st, "status": "success" if st == "COMPLETED" else "warning"}, dt])
    except Exception:
        pass
    return uploads, rows
def get_admin_training_context():
    uploads, rows = get_cached("admin:training_uploads", _load_training_uploads, ttl=20.0)
    return {"ml_status": get_master_training_status(), "training_uploads": uploads, "training_headers": ["Filename", "Uploaded By", "Rows", "Predictions", "Status", "Uploaded At"], "training_rows": rows}
def delete_user_record(user_id, actor_user_id=None, actor_email="", actor_name="System Admin"):
    clean_uid, col = str(user_id or "").strip(), users_col()
    existing = col.find_one({"user_id": clean_uid}, {"_id": 1, "email": 1})
    if _is_self_target(existing, clean_uid, actor_user_id, actor_email): return False, "You cannot delete your own active admin account."
    if col.delete_one({"user_id": clean_uid}).deleted_count:
        _audit("USERS", "DELETE_USER", f"Deleted user {clean_uid}.", "DANGER", actor=actor_name)
        invalidate_cache()
        return True, None
    return False, "User record not found."
def list_active_teachers(): return get_cached("admin:active_teachers", lambda: [{"user_id": str(d.get("user_id") or ""), "full_name": str(d.get("full_name") or ""), "email": str(d.get("email") or ""), "department": str(d.get("department") or "General")} for d in users_col().find({"role": "TEACHER", "is_active": True}, {"_id": 0, "user_id": 1, "full_name": 1, "email": 1, "department": 1}).sort("full_name", ASCENDING)], ttl=30.0)
def _load_courses_with_stats(clean_dept):
    ensure_admin_seed_data()
    enrolled_map = {str(r.get("_id") or "").strip().upper(): int(r.get("count") or 0) for r in student_records_col().aggregate([{"$match": LIVE_RECORD_QUERY}, {"$group": {"_id": "$course_code", "count": {"$sum": 1}}}]) if r.get("_id")}
    all_courses, dept_counts = [], {"ALL": 0}
    for doc in courses_col().find({}, {"_id": 0}).sort("course_code", ASCENDING):
        code, dept = str(doc.get("course_code") or "").strip().upper(), str(doc.get("department") or "General").strip()
        cap, enrolled = _safe_int(doc.get("capacity"), 60, 1, 2000), enrolled_map.get(code, 0)
        dept_counts["ALL"] += 1
        dept_counts[dept] = dept_counts.get(dept, 0) + 1
        all_courses.append({"course_code": code, "title": str(doc.get("title") or ""), "department": dept, "batch": str(doc.get("batch") or "2026-A"), "program_level": str(doc.get("program_level") or ""), "instructor": str(doc.get("instructor") or "TBA"), "instructor_id": str(doc.get("instructor_id") or ""), "instructor_email": str(doc.get("instructor_email") or ""), "credits": _safe_int(doc.get("credits"), 3, 1, 12), "capacity": cap, "enrolled_count": enrolled, "fill_pct": min(100, round((enrolled * 100) / cap)) if cap else 0, "status": str(doc.get("status") or "ACTIVE").upper(), "created_at_str": _format_dt(doc.get("created_at"))})
    return (all_courses if clean_dept == "ALL" else [c for c in all_courses if c["department"] == clean_dept]), sorted(d for d in dept_counts if d != "ALL"), dept_counts
def list_courses_with_stats(dept_filter="ALL"):
    clean_dept = str(dept_filter or "ALL").strip()
    return get_cached(f"admin:courses:{clean_dept}", lambda: _load_courses_with_stats(clean_dept), ttl=30.0)
def _resolve_course_teacher(instructor, instructor_id, instructor_email, fallback=None):
    fb, clean_iid, clean_name, clean_email = fallback or {}, str(instructor_id or "").strip(), str(instructor or "").strip(), str(instructor_email or "").strip()
    if clean_iid:
        teacher = users_col().find_one({"user_id": clean_iid, "role": "TEACHER"}, {"_id": 0, "full_name": 1, "email": 1})
        if teacher: clean_name, clean_email = clean_name or str(teacher.get("full_name") or "").strip(), clean_email or str(teacher.get("email") or "").strip()
    return clean_name or fb.get("instructor") or "TBA", clean_iid, clean_email
def _course_fields(title, department, batch, instructor, credits, capacity, status, fallback=None, instructor_id="", instructor_email="", program_level=""):
    fb, clean_status, clean_level = fallback or {}, str(status or "ACTIVE").strip().upper(), str(program_level or "").strip()
    t_name, t_id, t_email = _resolve_course_teacher(instructor, instructor_id, instructor_email, fb)
    return {"title": str(title or "").strip(), "department": str(department or "").strip() or fb.get("department") or "General", "batch": str(batch or "").strip() or fb.get("batch") or "2026-A", "instructor": t_name, "instructor_id": t_id, "instructor_email": t_email, **({"program_level": clean_level} if clean_level else {}), "credits": _safe_int(credits, 3, 1, 12), "capacity": _safe_int(capacity, 60, 1, 2000), "status": clean_status if clean_status in VALID_COURSE_STATUSES else "ACTIVE"}
def create_course_record(course_code, title, department, batch, instructor, credits, capacity, status="ACTIVE", actor_name="System Admin", instructor_id="", instructor_email="", program_level=""):
    clean_code, clean_title = str(course_code or "").strip().upper(), str(title or "").strip()
    if len(clean_code) < 2 or not clean_title: return None, "Course code and title are required."
    col = courses_col()
    if col.find_one({"course_code": clean_code}, {"_id": 1}) is not None: return None, f"Course {clean_code} already exists."
    doc = {"course_code": clean_code, "created_at": datetime.now(timezone.utc), **_course_fields(title, department, batch, instructor, credits, capacity, status, instructor_id=instructor_id, instructor_email=instructor_email, program_level=program_level)}
    col.insert_one(doc)
    _audit("COURSES", "CREATE_COURSE", f"Added course {clean_code} ({clean_title}).", "SUCCESS", actor=actor_name)
    invalidate_cache()
    return doc, None
def update_course_record(course_code, title, department, batch, instructor, credits, capacity, status="ACTIVE", actor_name="System Admin", instructor_id="", instructor_email="", program_level=""):
    clean_code, clean_title = str(course_code or "").strip().upper(), str(title or "").strip()
    if not clean_code or not clean_title: return False, "Course code and title are required."
    col = courses_col()
    existing = col.find_one({"course_code": clean_code})
    if existing is None: return False, "Course record not found."
    updates = {**_course_fields(title, department, batch, instructor, credits, capacity, status, fallback=existing, instructor_id=instructor_id, instructor_email=instructor_email, program_level=program_level), "updated_at": datetime.now(timezone.utc)}
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
        if status in counts: counts[status] += 1
        if clean_status not in VALID_TICKET_STATUSES or status == clean_status:
            tickets.append({"ticket_id": str(doc.get("ticket_id") or ""), "user_id": str(doc.get("user_id") or ""), "user_name": str(doc.get("user_name") or "User"), "role": str(doc.get("role") or "USER").upper(), "subject": str(doc.get("subject") or ""), "message": str(doc.get("message") or ""), "status": status, "admin_reply": str(doc.get("admin_reply") or ""), "replied_by": str(doc.get("replied_by") or ""), "replied_at_str": _format_dt(doc.get("replied_at")) if doc.get("replied_at") else "", "created_at_str": _format_dt(doc.get("created_at")), "attachments": [str(a) for a in (doc.get("attachments") or []) if a]})
    return tickets, counts
def list_tickets(status_filter="ALL"):
    clean_status = str(status_filter or "ALL").strip().upper()
    return get_cached(f"admin:tickets:{clean_status}", lambda: _load_tickets(clean_status), ttl=30.0)
def _clean_ticket_attachments(attachments, user_id):
    clean = []
    for idx, item in enumerate(attachments or []):
        if len(clean) >= 3: break
        if isinstance(item, str):
            val = item.strip()
            if val.lower().startswith(("https://", "http://", "data:image/")): clean.append(val)
        elif item is not None:
            url = upload_ticket_attachment(item, user_id, index=idx)[0] if is_cloudinary_configured() else encode_image_data_uri(item)
            if url: clean.append(url)
    return clean[:3]
def create_ticket_record(user_id, user_name, role, subject, message, attachments=None):
    clean_subject, clean_message = str(subject or "").strip(), str(message or "").strip()
    if not clean_subject or not clean_message: return None, "Subject and message details are required."
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
    if existing is None: return None, "Support ticket not found."
    new_status = "RESOLVED" if str(existing.get("status") or "OPEN").strip().upper() == "OPEN" else "OPEN"
    col.update_one({"_id": existing["_id"]}, {"$set": {"status": new_status, "updated_at": datetime.now(timezone.utc)}})
    tid = str(existing.get("ticket_id") or ticket_id)
    if existing.get("user_id"): create_notification(f"Ticket {tid} {new_status}", f"Your support ticket \"{existing.get('subject', '')}\" is now {new_status}.", severity="SUCCESS" if new_status == "RESOLVED" else "INFO", target_user_id=str(existing.get("user_id") or ""), category="TICKET_STATUS", ticket_id=tid)
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
    if not user_id and not student_id and not active_role: return 0
    targets = [{"target_user_id": tid} for tid in dict.fromkeys(x for x in (user_id, student_id) if x)]
    for target_role in dict.fromkeys(r for r in (active_role, "ALL") if r):
        targets.extend([{"target_role": target_role, "target_user_id": {"$in": [None, ""]}}, {"target_role": target_role, "target_user_id": {"$exists": False}}])
    modified = int(notifications_col().update_many({"is_read": False, "$or": targets}, {"$set": {"is_read": True}}).modified_count)
    invalidate_cache()
    return modified
from panels.admin_directory_services import build_course_table_data, build_ticket_table_data, build_user_table_data
