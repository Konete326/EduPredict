import json
import uuid
from datetime import datetime, timezone
from django.contrib.auth.hashers import make_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from pymongo import ASCENDING, DESCENDING
from pymongo.errors import DuplicateKeyError
from accounts.services import ensure_accounts_indexes_once, generate_unique_student_id, generate_unique_user_id
from core.db import classes_col, courses_col, get_cached, invalidate_cache, semesters_col, student_records_col, users_col
from panels.admin_audit_services import record_audit_log
from panels.admin_seed import _format_dt, _safe_int

def _audit(category, action, summary, severity="INFO", actor="System Admin"):
    try: record_audit_log(actor, "ADMIN", category, action, summary, severity=severity, source="SYSTEM")
    except Exception: pass

def _as_bool(value, default=True):
    if isinstance(value, bool): return value
    if value is None or str(value).strip() == "": return default
    return str(value).strip().lower() in ("1", "true", "yes", "on", "active")

def _clean_status(value, default="ACTIVE"):
    st = str(value or default).strip().upper()
    return st if st in ("ACTIVE", "INACTIVE") else default

def _action(label, icon, onclick, title, attrs, variant="default"):
    return {"label": label, "icon": icon, "variant": variant, "title": title, "onclick": onclick, "attrs": attrs}

def _view_action(title, payload):
    return {"type": "view_modal", "label": "View", "icon": "fa-solid fa-eye", "variant": "default", "title": title, "payload_json": json.dumps(payload)}

def _initials(name, fallback="U"):
    return "".join(p[0] for p in str(name or "").split() if p)[:2].upper() or fallback

def _gen_id(col, field, prefix):
    base = 1001 + col.count_documents({})
    for offset in range(30):
        candidate = f"{prefix}-{base + offset}"
        if col.find_one({field: candidate}, {"_id": 1}) is None: return candidate
    return f"{prefix}-{uuid.uuid4().hex[:6].upper()}"

def _validate_person(full_name, email):
    clean_name, clean_email = str(full_name or "").strip(), str(email or "").strip().lower()
    if not clean_name: return None, None, "Full name is required."
    try: validate_email(clean_email)
    except ValidationError: return None, None, "Please enter a valid email address."
    return clean_name, clean_email, None

def _validate_new_account(full_name, email, password):
    ensure_accounts_indexes_once()
    clean_name, clean_email, err = _validate_person(full_name, email)
    if err: return None, None, err
    if len(str(password or "")) < 6: return None, None, "Password must be at least 6 characters long."
    if users_col().find_one({"email": clean_email}, {"_id": 1}) is not None: return None, None, "A user with this email already exists."
    return clean_name, clean_email, None

def _validate_update_account(col, clean_uid, role, full_name, email, password, not_found_msg):
    existing = col.find_one({"user_id": clean_uid, "role": role})
    if existing is None: return None, None, None, not_found_msg
    clean_name, clean_email, err = _validate_person(full_name, email)
    if err: return None, None, None, err
    if col.find_one({"email": clean_email, "user_id": {"$ne": clean_uid}}, {"_id": 1}) is not None: return None, None, None, "Another user already uses this email address."
    if password and len(str(password)) < 6: return None, None, None, "New password must be at least 6 characters long."
    return existing, clean_name, clean_email, None

def _delete_doc(col, query, action, summary, not_found_msg, actor_name="System Admin"):
    if col.delete_one(query).deleted_count:
        _audit("ACADEMIC", action, summary, "DANGER", actor=actor_name)
        invalidate_cache()
        return True, None
    return False, not_found_msg

def _load_academic_maps():
    classes_list = list(classes_col().find({}, {"_id": 0}).sort("class_name", ASCENDING))
    semesters_list = list(semesters_col().find({}, {"_id": 0}).sort([("class_id", ASCENDING), ("semester_number", ASCENDING)]))
    teachers_list = list(users_col().find({"role": "TEACHER"}, {"_id": 0, "password_hash": 0}).sort("full_name", ASCENDING))
    class_map = {str(c.get("class_id") or ""): c for c in classes_list if c.get("class_id")}
    sem_map = {str(s.get("semester_id") or ""): s for s in semesters_list if s.get("semester_id")}
    teacher_map = {str(t.get("user_id") or ""): t for t in teachers_list if t.get("user_id")}
    return classes_list, semesters_list, teachers_list, class_map, sem_map, teacher_map

def _build_option_lists(classes_list, semesters_list, teachers_list, class_map):
    class_options = [{"id": str(c.get("class_id") or ""), "code": str(c.get("class_code") or ""), "name": str(c.get("class_name") or ""), "label": f"{c.get('class_code', '')} - {c.get('class_name', '')}".strip(" -")} for c in classes_list if c.get("class_id")]
    semester_options = []
    for s in semesters_list:
        sid, cid = str(s.get("semester_id") or ""), str(s.get("class_id") or "")
        if not sid: continue
        cname = str((class_map.get(cid) or {}).get("class_name") or cid or "-")
        sname = str(s.get("semester_name") or f"Semester {s.get('semester_number') or 1}")
        semester_options.append({"id": sid, "class_id": cid, "number": int(s.get("semester_number") or 1), "name": sname, "label": f"{cname} · {sname}"})
    teacher_options = [{"id": str(t.get("user_id") or ""), "name": str(t.get("full_name") or ""), "email": str(t.get("email") or ""), "label": f"{t.get('full_name', '')} ({t.get('email', '')})"} for t in teachers_list if t.get("user_id") and t.get("is_active", True)]
    return class_options, semester_options, teacher_options

def _build_teachers_context():
    docs = list(users_col().find({"role": "TEACHER"}, {"_id": 0, "password_hash": 0}).sort("created_at", DESCENDING))
    teachers, rows, cards, active_count = [], [], [], 0
    for d in docs:
        uid, name, email, phone, dept = str(d.get("user_id") or ""), str(d.get("full_name") or "Teacher"), str(d.get("email") or ""), str(d.get("phone") or ""), str(d.get("department") or "General")
        is_active = bool(d.get("is_active", True))
        active_count += int(is_active)
        created_str = _format_dt(d.get("created_at"))
        badge = {"text": "Active" if is_active else "Inactive", "status": "success" if is_active else "danger"}
        teachers.append({"user_id": uid, "full_name": name, "email": email, "phone": phone, "department": dept, "is_active": is_active, "created_at_str": created_str})
        attrs = {"data-user-id": uid, "data-full-name": name, "data-email": email, "data-phone": phone, "data-department": dept, "data-is-active": "true" if is_active else "false"}
        actions = [_view_action(f"View {name}", {"title": name, "subtitle": f"TEACHER · {uid}", "badge": badge["text"], "items": [{"label": "Teacher ID", "value": uid or "-"}, {"label": "Email", "value": email or "-"}, {"label": "Phone", "value": phone or "-"}, {"label": "Department", "value": dept or "-"}, {"label": "Joined", "value": created_str, "fullWidth": True}]}), _action("Edit", "fa-solid fa-pen-to-square", "openEditTeacherModal(this)", f"Edit {name}", attrs), _action("Delete", "fa-solid fa-trash", "openDeleteTeacherModal(this)", f"Delete {name}", {"data-user-id": uid, "data-full-name": name}, variant="danger")]
        rows.append([{"text": name, "initials": _initials(name, "T"), "avatar_url": str(d.get("avatar_url") or "")}, email or "-", phone or "-", badge, {"actions": actions}])
        cards.append({"id": uid, "title": name, "subtitle": email or uid, "badge": badge, "meta": [{"label": "Phone", "value": phone or "-"}], "actions": actions})
    return {"teachers": teachers, "teacher_headers": ["Teacher", "Email", "Phone", "Status", "Actions"], "teacher_rows": rows, "teacher_cards": cards, "total_teachers": len(teachers), "active_teachers": active_count, "inactive_teachers": len(teachers) - active_count}

def get_admin_teachers_context():
    return get_cached("admin:academic:teachers", _build_teachers_context, ttl=30.0)

def create_teacher_record(full_name, email, password, phone="", is_active=True, department="General", actor_name="System Admin"):
    clean_name, clean_email, err = _validate_new_account(full_name, email, password)
    if err: return None, err
    col = users_col()
    uid, active_flag = generate_unique_user_id(col), _as_bool(is_active, True)
    doc = {"user_id": uid, "full_name": clean_name, "email": clean_email, "password_hash": make_password(password), "role": "TEACHER", "department": str(department or "").strip() or "General", "batch": "", "phone": str(phone or "").strip(), "is_active": active_flag, "approval_status": "APPROVED" if active_flag else "INACTIVE", "created_at": datetime.now(timezone.utc)}
    try: col.insert_one(doc)
    except DuplicateKeyError: return None, "A user with this email already exists."
    _audit("ACADEMIC", "CREATE_TEACHER", f"Created teacher {clean_name} ({uid}).", "SUCCESS", actor=actor_name)
    invalidate_cache()
    return doc, None

def update_teacher_record(user_id, full_name, email, phone="", is_active=True, password="", department="General", actor_name="System Admin"):
    clean_uid, col = str(user_id or "").strip(), users_col()
    existing, clean_name, clean_email, err = _validate_update_account(col, clean_uid, "TEACHER", full_name, email, password, "Teacher record not found.")
    if err: return False, err
    active_flag = _as_bool(is_active, True)
    updates = {"full_name": clean_name, "email": clean_email, "phone": str(phone or "").strip(), "department": str(department or "").strip() or "General", "is_active": active_flag, "approval_status": "APPROVED" if active_flag else "INACTIVE", "updated_at": datetime.now(timezone.utc)}
    if password: updates["password_hash"] = make_password(password)
    col.update_one({"_id": existing["_id"]}, {"$set": updates})
    _audit("ACADEMIC", "UPDATE_TEACHER", f"Updated teacher {clean_uid}.", "INFO", actor=actor_name)
    invalidate_cache()
    return True, None

def delete_teacher_record(user_id, actor_name="System Admin"):
    clean_uid = str(user_id or "").strip()
    return _delete_doc(users_col(), {"user_id": clean_uid, "role": "TEACHER"}, "DELETE_TEACHER", f"Deleted teacher {clean_uid}.", "Teacher record not found.", actor_name)

def _build_students_context():
    classes_list, semesters_list, teachers_list, class_map, sem_map, _ = _load_academic_maps()
    class_options, semester_options, _ = _build_option_lists(classes_list, semesters_list, teachers_list, class_map)
    docs = list(users_col().find({"role": "STUDENT"}, {"_id": 0, "password_hash": 0}).sort("created_at", DESCENDING))
    students, rows, cards, assigned = [], [], [], 0
    for d in docs:
        uid, sid = str(d.get("user_id") or ""), str(d.get("student_id") or "")
        name, email, phone = str(d.get("full_name") or uid or "Student"), str(d.get("email") or ""), str(d.get("phone") or "")
        cid, sem_id = str(d.get("class_id") or ""), str(d.get("semester_id") or "")
        cname, sname = str((class_map.get(cid) or {}).get("class_name") or "-"), str((sem_map.get(sem_id) or {}).get("semester_name") or "-")
        assigned += int(bool(cid))
        students.append({"user_id": uid, "student_id": sid, "full_name": name, "email": email, "phone": phone, "class_id": cid, "class_name": cname, "semester_id": sem_id, "semester_name": sname})
        attrs = {"data-user-id": uid, "data-full-name": name, "data-email": email, "data-class-id": cid, "data-semester-id": sem_id, "data-phone": phone}
        actions = [_view_action(f"View {name}", {"title": name, "subtitle": sid or uid, "badge": cname if cid else "Unassigned", "items": [{"label": "User ID", "value": uid or "-"}, {"label": "Student ID", "value": sid or "-"}, {"label": "Email", "value": email or "-"}, {"label": "Class", "value": cname}, {"label": "Semester", "value": sname}, {"label": "Phone", "value": phone or "-"}]}), _action("Edit", "fa-solid fa-pen-to-square", "openEditStudentModal(this)", f"Edit {name}", attrs), _action("Delete", "fa-solid fa-trash", "openDeleteStudentModal(this)", f"Delete {name}", {"data-user-id": uid, "data-full-name": name}, variant="danger")]
        rows.append([{"text": name, "initials": _initials(name, "S"), "avatar_url": str(d.get("avatar_url") or "")}, cname, sname, phone or "-", {"actions": actions}])
        cards.append({"id": uid, "title": name, "subtitle": email or sid or uid, "badge": {"text": cname, "status": "info" if cid else "warning"}, "meta": [{"label": "Semester", "value": sname}, {"label": "Phone", "value": phone or "-"}], "actions": actions})
    return {"students": students, "student_headers": ["Student", "Class", "Semester", "Phone", "Actions"], "student_rows": rows, "student_cards": cards, "class_options": class_options, "semester_options": semester_options, "semester_options_json": json.dumps(semester_options), "total_students": len(students), "assigned_students": assigned}

def get_admin_students_context():
    return get_cached("admin:academic:students", _build_students_context, ttl=30.0)

def create_student_record(full_name, email, password, class_id="", semester_id="", phone="", department="General", actor_name="System Admin"):
    clean_name, clean_email, err = _validate_new_account(full_name, email, password)
    if err: return None, err
    col = users_col()
    uid = generate_unique_user_id(col)
    sid = generate_unique_student_id(student_records_col(), uid)
    doc = {"user_id": uid, "student_id": sid, "full_name": clean_name, "email": clean_email, "password_hash": make_password(password), "role": "STUDENT", "department": str(department or "").strip() or "General", "batch": "", "class_id": str(class_id or "").strip(), "semester_id": str(semester_id or "").strip(), "phone": str(phone or "").strip(), "is_active": True, "approval_status": "APPROVED", "created_at": datetime.now(timezone.utc)}
    try: col.insert_one(doc)
    except DuplicateKeyError: return None, "A user with this email already exists."
    _audit("ACADEMIC", "CREATE_STUDENT", f"Created student {clean_name} ({uid}).", "SUCCESS", actor=actor_name)
    invalidate_cache()
    return doc, None

def update_student_record(user_id, full_name, email, class_id="", semester_id="", phone="", password="", actor_name="System Admin"):
    clean_uid, col = str(user_id or "").strip(), users_col()
    existing, clean_name, clean_email, err = _validate_update_account(col, clean_uid, "STUDENT", full_name, email, password, "Student record not found.")
    if err: return False, err
    updates = {"full_name": clean_name, "email": clean_email, "class_id": str(class_id or "").strip(), "semester_id": str(semester_id or "").strip(), "phone": str(phone or "").strip(), "updated_at": datetime.now(timezone.utc)}
    if password: updates["password_hash"] = make_password(password)
    if not existing.get("student_id"): updates["student_id"] = generate_unique_student_id(student_records_col(), clean_uid)
    col.update_one({"_id": existing["_id"]}, {"$set": updates})
    _audit("ACADEMIC", "UPDATE_STUDENT", f"Updated student {clean_uid}.", "INFO", actor=actor_name)
    invalidate_cache()
    return True, None

def delete_student_record(user_id, actor_name="System Admin"):
    clean_uid = str(user_id or "").strip()
    return _delete_doc(users_col(), {"user_id": clean_uid, "role": "STUDENT"}, "DELETE_STUDENT", f"Deleted student {clean_uid}.", "Student record not found.", actor_name)

def _build_classes_context():
    classes_list, semesters_list, teachers_list, class_map, _, _ = _load_academic_maps()
    class_options, _, _ = _build_option_lists(classes_list, semesters_list, teachers_list, class_map)
    class_rows, class_cards, sem_rows, sem_cards, sem_counts = [], [], [], [], {}
    for s in semesters_list:
        cid = str(s.get("class_id") or "")
        sem_counts[cid] = sem_counts.get(cid, 0) + 1
    for c in classes_list:
        cid, code, name = str(c.get("class_id") or ""), str(c.get("class_code") or ""), str(c.get("class_name") or "")
        total_sem, st = _safe_int(c.get("total_semesters"), 8, 1, 12), _clean_status(c.get("status"), "ACTIVE")
        badge = {"text": "Active" if st == "ACTIVE" else "Inactive", "status": "success" if st == "ACTIVE" else "danger"}
        attrs = {"data-class-id": cid, "data-class-code": code, "data-class-name": name, "data-total-semesters": str(total_sem), "data-status": st}
        actions = [_action("Edit", "fa-solid fa-pen-to-square", "openEditClassModal(this)", f"Edit {name}", attrs), _action("Delete", "fa-solid fa-trash", "openDeleteClassModal(this)", f"Delete {name}", {"data-class-id": cid, "data-class-name": name}, variant="danger")]
        class_rows.append([code, name, sem_counts.get(cid, total_sem), badge, {"actions": actions}])
        class_cards.append({"id": cid, "title": f"{code} · {name}", "subtitle": f"{sem_counts.get(cid, total_sem)} Semesters", "badge": badge, "meta": [], "actions": actions})
    for s in semesters_list:
        sid, cid = str(s.get("semester_id") or ""), str(s.get("class_id") or "")
        num, sname = _safe_int(s.get("semester_number"), 1, 1, 20), str(s.get("semester_name") or f"Semester {s.get('semester_number') or 1}")
        st, cname = _clean_status(s.get("status"), "ACTIVE"), str((class_map.get(cid) or {}).get("class_name") or cid or "-")
        badge = {"text": "Active" if st == "ACTIVE" else "Inactive", "status": "success" if st == "ACTIVE" else "danger"}
        attrs = {"data-semester-id": sid, "data-class-id": cid, "data-semester-number": str(num), "data-semester-name": sname, "data-status": st}
        actions = [_action("Edit", "fa-solid fa-pen-to-square", "openEditSemesterModal(this)", f"Edit {sname}", attrs), _action("Delete", "fa-solid fa-trash", "openDeleteSemesterModal(this)", f"Delete {sname}", {"data-semester-id": sid, "data-semester-name": sname}, variant="danger")]
        sem_rows.append([cname, f"#{num}", sname, badge, {"actions": actions}])
        sem_cards.append({"id": sid, "title": f"{cname} · {sname}", "subtitle": f"Semester #{num}", "badge": badge, "meta": [], "actions": actions})
    return {"classes": classes_list, "semesters": semesters_list, "class_headers": ["Code", "Class Name", "Semesters", "Status", "Actions"], "class_rows": class_rows, "class_cards": class_cards, "semester_headers": ["Class", "No.", "Semester Name", "Status", "Actions"], "semester_rows": sem_rows, "semester_cards": sem_cards, "class_options": class_options, "total_classes": len(classes_list), "total_semesters_count": len(semesters_list)}

def get_admin_classes_context():
    return get_cached("admin:academic:classes", _build_classes_context, ttl=30.0)

def create_class_record(class_code, class_name, total_semesters=8, status="ACTIVE", actor_name="System Admin"):
    code, name = str(class_code or "").strip().upper(), str(class_name or "").strip()
    if not code or not name: return None, "Class code and class name are required."
    col, sem_col = classes_col(), semesters_col()
    if col.find_one({"class_code": code}, {"_id": 1}) is not None: return None, "A class with this code already exists."
    n_sem, cid, now = _safe_int(total_semesters, 8, 1, 12), _gen_id(col, "class_id", "CLS"), datetime.now(timezone.utc)
    doc = {"class_id": cid, "class_code": code, "class_name": name, "total_semesters": n_sem, "status": _clean_status(status), "created_at": now}
    col.insert_one(doc)
    sem_docs = [{"semester_id": _gen_id(sem_col, "semester_id", "SEM") if i == 1 else f"SEM-{uuid.uuid4().hex[:6].upper()}", "class_id": cid, "semester_number": i, "semester_name": f"Semester {i}", "status": "ACTIVE", "created_at": now} for i in range(1, n_sem + 1)]
    if sem_docs: sem_col.insert_many(sem_docs)
    _audit("ACADEMIC", "CREATE_CLASS", f"Created class {code} ({name}) with {n_sem} semesters.", "SUCCESS", actor=actor_name)
    invalidate_cache()
    return doc, None

def update_class_record(class_id, class_code, class_name, total_semesters=None, status="ACTIVE", actor_name="System Admin"):
    clean_cid, col = str(class_id or "").strip(), classes_col()
    existing = col.find_one({"class_id": clean_cid})
    if existing is None: return False, "Class record not found."
    code, name = str(class_code or "").strip().upper(), str(class_name or "").strip()
    if not code or not name: return False, "Class code and class name are required."
    if col.find_one({"class_code": code, "class_id": {"$ne": clean_cid}}, {"_id": 1}) is not None: return False, "Another class already uses this code."
    n_sem = _safe_int(total_semesters, int(existing.get("total_semesters") or 8), 1, 12)
    col.update_one({"_id": existing["_id"]}, {"$set": {"class_code": code, "class_name": name, "total_semesters": n_sem, "status": _clean_status(status), "updated_at": datetime.now(timezone.utc)}})
    _audit("ACADEMIC", "UPDATE_CLASS", f"Updated class {clean_cid} ({code}).", "INFO", actor=actor_name)
    invalidate_cache()
    return True, None

def delete_class_record(class_id, actor_name="System Admin"):
    clean_cid = str(class_id or "").strip()
    ok, err = _delete_doc(classes_col(), {"class_id": clean_cid}, "DELETE_CLASS", f"Deleted class {clean_cid} and its semesters.", "Class record not found.", actor_name)
    if ok: semesters_col().delete_many({"class_id": clean_cid})
    return ok, err

def create_semester_record(class_id, semester_number, semester_name="", status="ACTIVE", actor_name="System Admin"):
    clean_cid = str(class_id or "").strip()
    if not clean_cid or classes_col().find_one({"class_id": clean_cid}, {"_id": 1}) is None: return None, "Select a valid class."
    num = _safe_int(semester_number, 1, 1, 20)
    sname, col = str(semester_name or "").strip() or f"Semester {num}", semesters_col()
    if col.find_one({"class_id": clean_cid, "semester_number": num}, {"_id": 1}) is not None: return None, f"Semester {num} already exists for this class."
    doc = {"semester_id": _gen_id(col, "semester_id", "SEM"), "class_id": clean_cid, "semester_number": num, "semester_name": sname, "status": _clean_status(status), "created_at": datetime.now(timezone.utc)}
    col.insert_one(doc)
    _audit("ACADEMIC", "CREATE_SEMESTER", f"Created {sname} for class {clean_cid}.", "SUCCESS", actor=actor_name)
    invalidate_cache()
    return doc, None

def update_semester_record(semester_id, class_id, semester_number, semester_name="", status="ACTIVE", actor_name="System Admin"):
    clean_sid, col = str(semester_id or "").strip(), semesters_col()
    existing = col.find_one({"semester_id": clean_sid})
    if existing is None: return False, "Semester record not found."
    clean_cid = str(class_id or existing.get("class_id") or "").strip()
    if not clean_cid or classes_col().find_one({"class_id": clean_cid}, {"_id": 1}) is None: return False, "Select a valid class."
    num = _safe_int(semester_number, int(existing.get("semester_number") or 1), 1, 20)
    sname = str(semester_name or "").strip() or f"Semester {num}"
    if col.find_one({"class_id": clean_cid, "semester_number": num, "semester_id": {"$ne": clean_sid}}, {"_id": 1}) is not None: return False, f"Semester {num} already exists for this class."
    col.update_one({"_id": existing["_id"]}, {"$set": {"class_id": clean_cid, "semester_number": num, "semester_name": sname, "status": _clean_status(status), "updated_at": datetime.now(timezone.utc)}})
    _audit("ACADEMIC", "UPDATE_SEMESTER", f"Updated semester {clean_sid}.", "INFO", actor=actor_name)
    invalidate_cache()
    return True, None

def delete_semester_record(semester_id, actor_name="System Admin"):
    clean_sid = str(semester_id or "").strip()
    return _delete_doc(semesters_col(), {"semester_id": clean_sid}, "DELETE_SEMESTER", f"Deleted semester {clean_sid}.", "Semester record not found.", actor_name)

def _build_courses_context():
    classes_list, semesters_list, teachers_list, class_map, sem_map, teacher_map = _load_academic_maps()
    class_options, semester_options, teacher_options = _build_option_lists(classes_list, semesters_list, teachers_list, class_map)
    docs = list(courses_col().find({}, {"_id": 0}).sort("course_code", ASCENDING))
    courses, rows, cards, active_count = [], [], [], 0
    for c in docs:
        code, title = str(c.get("course_code") or "").upper(), str(c.get("title") or "")
        cid, sem_id, iid = str(c.get("class_id") or ""), str(c.get("semester_id") or ""), str(c.get("instructor_id") or "")
        credits, st = _safe_int(c.get("credits"), 3, 1, 10), _clean_status(c.get("status"), "ACTIVE")
        active_count += int(st == "ACTIVE")
        cname, sname = str((class_map.get(cid) or {}).get("class_name") or "-"), str((sem_map.get(sem_id) or {}).get("semester_name") or "-")
        t_doc = teacher_map.get(iid) or {}
        iname, iemail = str(t_doc.get("full_name") or c.get("instructor") or "-"), str(t_doc.get("email") or "")
        badge = {"text": "Active" if st == "ACTIVE" else "Inactive", "status": "success" if st == "ACTIVE" else "danger"}
        courses.append({"course_code": code, "title": title, "class_id": cid, "class_name": cname, "semester_id": sem_id, "semester_name": sname, "instructor_id": iid, "instructor_name": iname, "instructor_email": iemail, "credits": credits, "status": st})
        attrs = {"data-course-code": code, "data-title": title, "data-class-id": cid, "data-semester-id": sem_id, "data-instructor-id": iid, "data-credits": str(credits), "data-status": st}
        actions = [_view_action(f"View {code}", {"title": title, "subtitle": code, "badge": badge["text"], "items": [{"label": "Course Code", "value": code}, {"label": "Class", "value": cname}, {"label": "Semester", "value": sname}, {"label": "Instructor", "value": f"{iname} ({iemail})" if iemail else iname}, {"label": "Credits", "value": str(credits)}]}), _action("Edit", "fa-solid fa-pen-to-square", "openEditCourseModal(this)", f"Edit {code}", attrs), _action("Delete", "fa-solid fa-trash", "openDeleteCourseModal(this)", f"Delete {code}", {"data-course-code": code, "data-title": title}, variant="danger")]
        rows.append([f"{code} · {title}", f"{cname} / {sname}", iname, credits, badge, {"actions": actions}])
        cards.append({"id": code, "title": f"{code} · {title}", "subtitle": f"{cname} · {sname}", "badge": badge, "meta": [{"label": "Instructor", "value": iname}, {"label": "Credits", "value": str(credits)}], "actions": actions})
    return {"courses": courses, "course_headers": ["Course", "Class / Semester", "Instructor", "Credits", "Status", "Actions"], "course_rows": rows, "course_cards": cards, "class_options": class_options, "semester_options": semester_options, "semester_options_json": json.dumps(semester_options), "teacher_options": teacher_options, "total_courses": len(courses), "active_courses": active_count}

def get_admin_courses_context():
    return get_cached("admin:academic:courses", _build_courses_context, ttl=30.0)

def create_course_record(course_code, title, class_id="", semester_id="", instructor_id="", credits=3, status="ACTIVE", actor_name="System Admin"):
    code, clean_title = str(course_code or "").strip().upper(), str(title or "").strip()
    if not code or not clean_title: return None, "Course code and title are required."
    col = courses_col()
    if col.find_one({"course_code": code}, {"_id": 1}) is not None: return None, "A course with this code already exists."
    iid = str(instructor_id or "").strip()
    t_doc = users_col().find_one({"user_id": iid, "role": "TEACHER"}, {"_id": 0, "full_name": 1}) if iid else None
    doc = {"course_code": code, "title": clean_title, "class_id": str(class_id or "").strip(), "semester_id": str(semester_id or "").strip(), "instructor_id": iid, "instructor": str((t_doc or {}).get("full_name") or ""), "credits": _safe_int(credits, 3, 1, 10), "status": _clean_status(status), "created_at": datetime.now(timezone.utc)}
    col.insert_one(doc)
    _audit("ACADEMIC", "CREATE_COURSE", f"Created course {code} ({clean_title}).", "SUCCESS", actor=actor_name)
    invalidate_cache()
    return doc, None

def update_course_record(course_code, title, class_id="", semester_id="", instructor_id="", credits=3, status="ACTIVE", original_course_code="", actor_name="System Admin"):
    lookup_code, code, clean_title = str(original_course_code or course_code or "").strip().upper(), str(course_code or "").strip().upper(), str(title or "").strip()
    if not code or not clean_title: return False, "Course code and title are required."
    col = courses_col()
    existing = col.find_one({"course_code": lookup_code})
    if existing is None: return False, "Course record not found."
    if code != lookup_code and col.find_one({"course_code": code}, {"_id": 1}) is not None: return False, "Another course already uses this code."
    iid = str(instructor_id or "").strip()
    t_doc = users_col().find_one({"user_id": iid, "role": "TEACHER"}, {"_id": 0, "full_name": 1}) if iid else None
    col.update_one({"_id": existing["_id"]}, {"$set": {"course_code": code, "title": clean_title, "class_id": str(class_id or "").strip(), "semester_id": str(semester_id or "").strip(), "instructor_id": iid, "instructor": str((t_doc or {}).get("full_name") or ""), "credits": _safe_int(credits, 3, 1, 10), "status": _clean_status(status), "updated_at": datetime.now(timezone.utc)}})
    _audit("ACADEMIC", "UPDATE_COURSE", f"Updated course {code}.", "INFO", actor=actor_name)
    invalidate_cache()
    return True, None

def delete_course_record(course_code, actor_name="System Admin"):
    clean_code = str(course_code or "").strip().upper()
    return _delete_doc(courses_col(), {"course_code": clean_code}, "DELETE_COURSE", f"Deleted course {clean_code}.", "Course record not found.", actor_name)
