import json
import uuid
from datetime import datetime, timezone
from django.contrib.auth.hashers import make_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from pymongo import ASCENDING, DESCENDING
from pymongo.errors import DuplicateKeyError
from accounts.services import ensure_accounts_indexes_once, generate_unique_student_id, generate_unique_user_id
from core.db import courses_col, get_cached, invalidate_cache, semesters_col, student_records_col, users_col
from panels.admin_audit_services import record_audit_log
from panels.admin_seed import _format_dt, _safe_int

DEFAULT_PROGRAMS = ("BSCS", "BSSE", "BSIT", "BBA", "BSEE", "MSCS")

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
    for offset in range(40):
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
    semesters_list = sorted(semesters_col().find({}, {"_id": 0}), key=lambda s: (str(s.get("program_name") or ""), int(s.get("semester_number") or 0)))
    teachers_list = list(users_col().find({"role": "TEACHER"}, {"_id": 0, "password_hash": 0}).sort("full_name", ASCENDING))
    sem_map = {str(s.get("semester_id") or ""): s for s in semesters_list if s.get("semester_id")}
    teacher_map = {str(t.get("user_id") or ""): t for t in teachers_list if t.get("user_id")}
    return semesters_list, teachers_list, sem_map, teacher_map

def _semester_label(s):
    if not s: return "-"
    prog = str(s.get("program_name") or "BSCS").strip()
    sname = str(s.get("semester_name") or f"Semester {s.get('semester_number') or 1}")
    return f"{prog} · {sname}"

def _build_option_lists(semesters_list, teachers_list):
    semester_options = [{"value": str(s.get("semester_id") or ""), "label": _semester_label(s), "program": str(s.get("program_name") or "BSCS"), "number": int(s.get("semester_number") or 1)} for s in semesters_list if s.get("semester_id")]
    teacher_options = [{"value": str(t.get("user_id") or ""), "label": f"{t.get('full_name', '')} ({t.get('email', '')})"} for t in teachers_list if t.get("user_id") and t.get("is_active", True)]
    prog_names = sorted(set(DEFAULT_PROGRAMS) | {str(s.get("program_name") or "").strip().upper() for s in semesters_list if s.get("program_name")})
    program_options = [{"value": p, "label": p} for p in prog_names]
    return semester_options, teacher_options, program_options

def _build_teachers_context():
    docs = list(users_col().find({"role": "TEACHER"}, {"_id": 0, "password_hash": 0}).sort("created_at", DESCENDING))
    teachers, rows, cards, active_count = [], [], [], 0
    for d in docs:
        uid, name, email, phone = str(d.get("user_id") or ""), str(d.get("full_name") or "Teacher"), str(d.get("email") or ""), str(d.get("phone") or "")
        is_active = bool(d.get("is_active", True))
        active_count += int(is_active)
        badge = {"text": "Active" if is_active else "Inactive", "status": "success" if is_active else "danger"}
        teachers.append({"user_id": uid, "full_name": name, "email": email, "phone": phone, "is_active": is_active, "created_at_str": _format_dt(d.get("created_at"))})
        attrs = {"data-user-id": uid, "data-full-name": name, "data-email": email, "data-phone": phone, "data-is-active": "true" if is_active else "false"}
        actions = [_view_action(f"View {name}", {"title": name, "subtitle": email, "badge": badge["text"], "items": [{"label": "Teacher ID", "value": uid}, {"label": "Phone", "value": phone or "-"}, {"label": "Joined", "value": _format_dt(d.get("created_at"))}]}), _action("Edit", "fa-solid fa-pen-to-square", "openEditTeacherModal(this)", f"Edit {name}", attrs), _action("Delete", "fa-solid fa-trash", "openDeleteTeacherModal(this)", f"Delete {name}", {"data-user-id": uid, "data-full-name": name}, variant="danger")]
        rows.append([{"text": name, "initials": _initials(name, "T")}, email, phone or "-", badge, {"actions": actions}])
        cards.append({"id": uid, "title": name, "subtitle": email, "badge": badge, "meta": [{"label": "ID", "value": uid}, {"label": "Phone", "value": phone or "-"}], "actions": actions})
    return {"teachers": teachers, "teacher_headers": ["Teacher", "Email", "Phone", "Status", "Actions"], "teacher_rows": rows, "teacher_cards": cards, "total_teachers": len(teachers), "active_teachers": active_count, "inactive_teachers": len(teachers) - active_count}

def get_admin_teachers_context():
    return get_cached("admin:academic:teachers", _build_teachers_context, ttl=20.0)

def create_teacher_record(full_name, email, password, phone="", is_active=True, department="General", actor_name="System Admin"):
    clean_name, clean_email, err = _validate_new_account(full_name, email, password)
    if err: return None, err
    col = users_col()
    uid = generate_unique_user_id(col)
    doc = {"user_id": uid, "full_name": clean_name, "email": clean_email, "password_hash": make_password(password), "role": "TEACHER", "department": str(department or "").strip() or "General", "batch": "", "phone": str(phone or "").strip(), "is_active": _as_bool(is_active, True), "approval_status": "APPROVED", "created_at": datetime.now(timezone.utc)}
    try: col.insert_one(doc)
    except DuplicateKeyError: return None, "A user with this email already exists."
    _audit("ACADEMIC", "CREATE_TEACHER", f"Created teacher {clean_name} ({uid}).", "SUCCESS", actor=actor_name)
    invalidate_cache()
    return doc, None

def update_teacher_record(user_id, full_name, email, phone="", is_active=True, password="", department="General", actor_name="System Admin"):
    clean_uid, col = str(user_id or "").strip(), users_col()
    existing, clean_name, clean_email, err = _validate_update_account(col, clean_uid, "TEACHER", full_name, email, password, "Teacher record not found.")
    if err: return False, err
    updates = {"full_name": clean_name, "email": clean_email, "phone": str(phone or "").strip(), "department": str(department or "").strip() or existing.get("department") or "General", "is_active": _as_bool(is_active, True), "updated_at": datetime.now(timezone.utc)}
    if updates["is_active"]: updates["approval_status"] = "APPROVED"
    if password: updates["password_hash"] = make_password(password)
    col.update_one({"_id": existing["_id"]}, {"$set": updates})
    _audit("ACADEMIC", "UPDATE_TEACHER", f"Updated teacher {clean_name} ({clean_uid}).", "INFO", actor=actor_name)
    invalidate_cache()
    return True, None

def delete_teacher_record(user_id, actor_name="System Admin"):
    clean_uid = str(user_id or "").strip()
    return _delete_doc(users_col(), {"user_id": clean_uid, "role": "TEACHER"}, "DELETE_TEACHER", f"Deleted teacher {clean_uid}.", "Teacher record not found.", actor_name)

def _build_students_context():
    semesters_list, teachers_list, sem_map, _ = _load_academic_maps()
    semester_options, _, _ = _build_option_lists(semesters_list, teachers_list)
    docs = list(users_col().find({"role": "STUDENT"}, {"_id": 0, "password_hash": 0}).sort("created_at", DESCENDING))
    students, rows, cards, assigned = [], [], [], 0
    for d in docs:
        uid, sid, name, email, phone = str(d.get("user_id") or ""), str(d.get("student_id") or d.get("user_id") or ""), str(d.get("full_name") or "Student"), str(d.get("email") or ""), str(d.get("phone") or "")
        sem_id = str(d.get("semester_id") or "")
        sem_label = _semester_label(sem_map.get(sem_id))
        if sem_id and sem_map.get(sem_id): assigned += 1
        badge = {"text": "Assigned" if sem_id else "Unassigned", "status": "success" if sem_id else "warning"}
        students.append({"user_id": uid, "student_id": sid, "full_name": name, "email": email, "phone": phone, "semester_id": sem_id, "semester_label": sem_label})
        attrs = {"data-user-id": uid, "data-student-id": sid, "data-full-name": name, "data-email": email, "data-semester-id": sem_id, "data-phone": phone}
        actions = [_view_action(f"View {name}", {"title": name, "subtitle": f"{sid} · {email}", "badge": badge["text"], "items": [{"label": "Student ID", "value": sid}, {"label": "Semester", "value": sem_label}, {"label": "Phone", "value": phone or "-"}]}), _action("Edit", "fa-solid fa-pen-to-square", "openEditStudentModal(this)", f"Edit {name}", attrs), _action("Delete", "fa-solid fa-trash", "openDeleteStudentModal(this)", f"Delete {name}", {"data-user-id": uid, "data-full-name": name}, variant="danger")]
        rows.append([{"text": name, "initials": _initials(name, "S")}, sid, sem_label, badge, {"actions": actions}])
        cards.append({"id": uid, "title": name, "subtitle": f"{sid} · {email}", "badge": badge, "meta": [{"label": "Semester", "value": sem_label}], "actions": actions})
    return {"students": students, "student_headers": ["Student", "ID", "Semester", "Status", "Actions"], "student_rows": rows, "student_cards": cards, "semester_options_json": json.dumps(semester_options), "total_students": len(students), "assigned_students": assigned}

def get_admin_students_context():
    return get_cached("admin:academic:students", _build_students_context, ttl=20.0)

def create_student_record(full_name, email, password, semester_id="", phone="", actor_name="System Admin"):
    clean_name, clean_email, err = _validate_new_account(full_name, email, password)
    if err: return None, err
    col = users_col()
    uid = generate_unique_user_id(col)
    sid = generate_unique_student_id(student_records_col(), uid)
    doc = {"user_id": uid, "student_id": sid, "full_name": clean_name, "email": clean_email, "password_hash": make_password(password), "role": "STUDENT", "department": "University", "batch": "", "semester_id": str(semester_id or "").strip(), "phone": str(phone or "").strip(), "is_active": True, "approval_status": "APPROVED", "created_at": datetime.now(timezone.utc)}
    try: col.insert_one(doc)
    except DuplicateKeyError: return None, "A user with this email already exists."
    _audit("ACADEMIC", "CREATE_STUDENT", f"Created student {clean_name} ({sid}).", "SUCCESS", actor=actor_name)
    invalidate_cache()
    return doc, None

def update_student_record(user_id, full_name, email, semester_id="", phone="", password="", actor_name="System Admin"):
    clean_uid, col = str(user_id or "").strip(), users_col()
    existing, clean_name, clean_email, err = _validate_update_account(col, clean_uid, "STUDENT", full_name, email, password, "Student record not found.")
    if err: return False, err
    updates = {"full_name": clean_name, "email": clean_email, "semester_id": str(semester_id or "").strip(), "phone": str(phone or "").strip(), "updated_at": datetime.now(timezone.utc)}
    if password: updates["password_hash"] = make_password(password)
    col.update_one({"_id": existing["_id"]}, {"$set": updates})
    _audit("ACADEMIC", "UPDATE_STUDENT", f"Updated student {clean_name} ({clean_uid}).", "INFO", actor=actor_name)
    invalidate_cache()
    return True, None

def delete_student_record(user_id, actor_name="System Admin"):
    clean_uid = str(user_id or "").strip()
    return _delete_doc(users_col(), {"user_id": clean_uid, "role": "STUDENT"}, "DELETE_STUDENT", f"Deleted student {clean_uid}.", "Student record not found.", actor_name)

def _build_semesters_context():
    semesters_list, teachers_list, _, _ = _load_academic_maps()
    _, _, program_options = _build_option_lists(semesters_list, teachers_list)
    sem_rows, sem_cards, programs_set = [], [], set()
    for s in semesters_list:
        sid = str(s.get("semester_id") or "")
        prog = str(s.get("program_name") or "BSCS").strip().upper()
        num, sname, st = int(s.get("semester_number") or 1), str(s.get("semester_name") or f"Semester {s.get('semester_number') or 1}"), _clean_status(s.get("status"), "ACTIVE")
        programs_set.add(prog)
        badge = {"text": st, "status": "success" if st == "ACTIVE" else "warning"}
        attrs = {"data-semester-id": sid, "data-program-name": prog, "data-semester-number": str(num), "data-semester-name": sname, "data-status": st}
        actions = [_action("Edit", "fa-solid fa-pen-to-square", "openEditSemesterModal(this)", f"Edit {prog} {sname}", attrs), _action("Delete", "fa-solid fa-trash", "openDeleteSemesterModal(this)", f"Delete {prog} {sname}", {"data-semester-id": sid, "data-semester-name": f"{prog} · {sname}"}, variant="danger")]
        sem_rows.append([sid, prog, f"{sname} (#{num})", badge, {"actions": actions}])
        sem_cards.append({"id": sid, "title": f"{prog} · {sname}", "subtitle": f"Code: {sid} · #{num}", "badge": badge, "actions": actions})
    return {"semesters": semesters_list, "semester_headers": ["Code", "Program", "Semester", "Status", "Actions"], "semester_rows": sem_rows, "semester_cards": sem_cards, "program_options_json": json.dumps(program_options), "next_semester_code": _gen_id(semesters_col(), "semester_id", "SEM"), "total_semesters_count": len(semesters_list), "total_programs_count": len(programs_set)}

def get_admin_semesters_context():
    return get_cached("admin:academic:semesters", _build_semesters_context, ttl=20.0)

def create_semester_record(program_name, semester_number=1, semester_name="", status="ACTIVE", total_semesters=1, actor_name="System Admin"):
    prog = str(program_name or "").strip().upper()
    if len(prog) < 2: return None, "Program name is required (e.g. BSCS)."
    col, st, now = semesters_col(), _clean_status(status), datetime.now(timezone.utc)
    batch_n = _safe_int(total_semesters, 1, 1, 12)
    if batch_n > 1:
        created = []
        for i in range(1, batch_n + 1):
            if col.find_one({"program_name": prog, "semester_number": i}, {"_id": 1}) is None:
                doc = {"semester_id": _gen_id(col, "semester_id", "SEM"), "program_name": prog, "semester_number": i, "semester_name": f"Semester {i}", "status": st, "created_at": now}
                col.insert_one(doc)
                created.append(doc)
        if not created: return None, f"Semesters 1-{batch_n} already exist for {prog}."
        _audit("ACADEMIC", "CREATE_SEMESTER", f"Generated {len(created)} semesters for {prog}.", "SUCCESS", actor=actor_name)
        invalidate_cache()
        return created[0], None
    num = _safe_int(semester_number, 1, 1, 12)
    if col.find_one({"program_name": prog, "semester_number": num}, {"_id": 1}) is not None: return None, f"{prog} Semester {num} already exists."
    sname = str(semester_name or "").strip() or f"Semester {num}"
    doc = {"semester_id": _gen_id(col, "semester_id", "SEM"), "program_name": prog, "semester_number": num, "semester_name": sname, "status": st, "created_at": now}
    col.insert_one(doc)
    _audit("ACADEMIC", "CREATE_SEMESTER", f"Created {prog} {sname} ({doc['semester_id']}).", "SUCCESS", actor=actor_name)
    invalidate_cache()
    return doc, None

def update_semester_record(semester_id, program_name, semester_number, semester_name="", status="ACTIVE", actor_name="System Admin"):
    clean_sid, col = str(semester_id or "").strip(), semesters_col()
    existing = col.find_one({"semester_id": clean_sid})
    if existing is None: return False, "Semester record not found."
    prog = str(program_name or existing.get("program_name") or "").strip().upper()
    if len(prog) < 2: return False, "Program name is required."
    num = _safe_int(semester_number, 1, 1, 12)
    sname = str(semester_name or "").strip() or f"Semester {num}"
    if col.find_one({"program_name": prog, "semester_number": num, "semester_id": {"$ne": clean_sid}}, {"_id": 1}) is not None: return False, f"{prog} Semester {num} already exists."
    col.update_one({"_id": existing["_id"]}, {"$set": {"program_name": prog, "semester_number": num, "semester_name": sname, "status": _clean_status(status), "updated_at": datetime.now(timezone.utc)}})
    _audit("ACADEMIC", "UPDATE_SEMESTER", f"Updated {prog} {sname} ({clean_sid}).", "INFO", actor=actor_name)
    invalidate_cache()
    return True, None

def delete_semester_record(semester_id, actor_name="System Admin"):
    clean_sid = str(semester_id or "").strip()
    return _delete_doc(semesters_col(), {"semester_id": clean_sid}, "DELETE_SEMESTER", f"Deleted semester {clean_sid}.", "Semester record not found.", actor_name)

def _build_courses_context():
    semesters_list, teachers_list, sem_map, teacher_map = _load_academic_maps()
    semester_options, teacher_options, _ = _build_option_lists(semesters_list, teachers_list)
    courses, rows, cards, active_count = [], [], [], 0
    for c in courses_col().find({}, {"_id": 0}).sort("course_code", ASCENDING):
        code, title = str(c.get("course_code") or "").strip().upper(), str(c.get("title") or "").strip()
        if not code: continue
        sem_id, iid = str(c.get("semester_id") or ""), str(c.get("instructor_id") or "")
        st = _clean_status(c.get("status"), "ACTIVE")
        active_count += int(st == "ACTIVE")
        sem_label = _semester_label(sem_map.get(sem_id))
        t_doc = teacher_map.get(iid) or {}
        iname, iemail = str(t_doc.get("full_name") or c.get("instructor") or "Unassigned"), str(t_doc.get("email") or c.get("instructor_email") or "")
        badge = {"text": st, "status": "success" if st == "ACTIVE" else "warning"}
        courses.append({"course_code": code, "title": title, "semester_id": sem_id, "semester_label": sem_label, "instructor_id": iid, "instructor_name": iname, "instructor_email": iemail, "status": st})
        attrs = {"data-course-code": code, "data-title": title, "data-semester-id": sem_id, "data-instructor-id": iid, "data-status": st}
        actions = [_view_action(f"View {code}", {"title": title, "subtitle": code, "badge": badge["text"], "items": [{"label": "Course Code", "value": code}, {"label": "Semester", "value": sem_label}, {"label": "Teacher", "value": f"{iname} ({iemail})" if iemail else iname}]}), _action("Edit", "fa-solid fa-pen-to-square", "openEditCourseModal(this)", f"Edit {code}", attrs), _action("Delete", "fa-solid fa-trash", "openDeleteCourseModal(this)", f"Delete {code}", {"data-course-code": code, "data-title": title}, variant="danger")]
        rows.append([f"{code} · {title}", sem_label, iname, badge, {"actions": actions}])
        cards.append({"id": code, "title": f"{code} · {title}", "subtitle": sem_label, "badge": badge, "meta": [{"label": "Teacher", "value": iname}], "actions": actions})
    return {"courses": courses, "course_headers": ["Course", "Semester", "Teacher", "Status", "Actions"], "course_rows": rows, "course_cards": cards, "semester_options_json": json.dumps(semester_options), "teacher_options_json": json.dumps(teacher_options), "next_course_code": _gen_id(courses_col(), "course_code", "CRS"), "total_courses": len(courses), "active_courses": active_count}

def get_admin_courses_context():
    return get_cached("admin:academic:courses", _build_courses_context, ttl=20.0)

def create_course_record(course_code, title, semester_id="", instructor_id="", status="ACTIVE", actor_name="System Admin"):
    col, clean_title = courses_col(), str(title or "").strip()
    code = str(course_code or "").strip().upper() or _gen_id(col, "course_code", "CRS")
    if not clean_title: return None, "Course title is required."
    if col.find_one({"course_code": code}, {"_id": 1}) is not None: code = _gen_id(col, "course_code", "CRS")
    iid = str(instructor_id or "").strip()
    t_doc = users_col().find_one({"user_id": iid, "role": "TEACHER"}, {"_id": 0, "full_name": 1, "email": 1}) if iid else None
    doc = {"course_code": code, "title": clean_title, "semester_id": str(semester_id or "").strip(), "instructor_id": iid, "instructor": str((t_doc or {}).get("full_name") or ""), "instructor_email": str((t_doc or {}).get("email") or ""), "status": _clean_status(status), "created_at": datetime.now(timezone.utc)}
    col.insert_one(doc)
    _audit("ACADEMIC", "CREATE_COURSE", f"Created course {code} ({clean_title}).", "SUCCESS", actor=actor_name)
    invalidate_cache()
    return doc, None

def update_course_record(course_code, title, semester_id="", instructor_id="", status="ACTIVE", original_course_code="", actor_name="System Admin"):
    target_code = str(original_course_code or course_code or "").strip().upper()
    code, clean_title = str(course_code or target_code).strip().upper(), str(title or "").strip()
    if not code or not clean_title: return False, "Course title is required."
    col = courses_col()
    existing = col.find_one({"course_code": target_code})
    if existing is None: return False, "Course record not found."
    iid = str(instructor_id or "").strip()
    t_doc = users_col().find_one({"user_id": iid, "role": "TEACHER"}, {"_id": 0, "full_name": 1, "email": 1}) if iid else None
    col.update_one({"_id": existing["_id"]}, {"$set": {"course_code": code, "title": clean_title, "semester_id": str(semester_id or "").strip(), "instructor_id": iid, "instructor": str((t_doc or {}).get("full_name") or ""), "instructor_email": str((t_doc or {}).get("email") or ""), "status": _clean_status(status), "updated_at": datetime.now(timezone.utc)}})
    _audit("ACADEMIC", "UPDATE_COURSE", f"Updated course {code} ({clean_title}).", "INFO", actor=actor_name)
    invalidate_cache()
    return True, None

def delete_course_record(course_code, actor_name="System Admin"):
    clean_code = str(course_code or "").strip().upper()
    return _delete_doc(courses_col(), {"course_code": clean_code}, "DELETE_COURSE", f"Deleted course {clean_code}.", "Course record not found.", actor_name)
