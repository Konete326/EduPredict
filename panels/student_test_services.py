import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from django.conf import settings
from core.cloudinary_services import ALLOWED_IMAGE_EXTS, is_cloudinary_configured, upload_academic_attachment
from core.db import course_tests_col, courses_col, invalidate_cache, semesters_col, student_records_col, users_col


def _safe_float(val, default=0.0):
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _semester_label(s):
    if not s:
        return "-"
    prog = str(s.get("program_name") or "BSCS").strip()
    sname = str(s.get("semester_name") or f"Semester {s.get('semester_number') or 1}").strip()
    return f"{prog} · {sname}"


def _resolve_student_scope(student_id, user_id, role):
    sid = str(student_id or "").strip()
    uid = str(user_id or "").strip()
    u_doc = None
    try:
        ucol = users_col()
        if sid:
            u_doc = ucol.find_one({"student_id": sid}, {"_id": 0, "student_id": 1, "user_id": 1, "full_name": 1, "semester_id": 1, "batch": 1})
        if not u_doc and uid:
            u_doc = ucol.find_one({"user_id": uid}, {"_id": 0, "student_id": 1, "user_id": 1, "full_name": 1, "semester_id": 1, "batch": 1})
    except Exception:
        u_doc = None
    sid = sid or str((u_doc or {}).get("student_id") or uid).strip()
    sem_id = str((u_doc or {}).get("semester_id") or "").strip()
    rec_docs = list(student_records_col().find({"student_id": sid}, {"_id": 0, "course_code": 1, "semester_id": 1, "full_name": 1})) if sid else []
    if not sem_id:
        for r in rec_docs:
            if r.get("semester_id"):
                sem_id = str(r.get("semester_id") or "").strip()
                break
    enrolled_codes = {str(r.get("course_code") or "").strip().upper() for r in rec_docs if r.get("course_code")}
    sem_doc = semesters_col().find_one({"semester_id": sem_id}, {"_id": 0}) if sem_id else None
    sem_label = _semester_label(sem_doc) if sem_doc else "-"
    return sid, sem_id, sem_label, enrolled_codes, str((u_doc or {}).get("full_name") or "").strip()


def _normalize_files(sub):
    raw_items = list(sub.get("files") or sub.get("attachments") or [])
    legacy_url = str(sub.get("submission_file_url") or "").strip()
    if legacy_url:
        raw_items.append({"url": legacy_url, "name": str(sub.get("submission_file_name") or "").strip()})
    files, seen = [], set()
    for item in raw_items:
        if isinstance(item, str):
            url, name, is_img = item.strip(), "", None
        elif isinstance(item, dict):
            url = str(item.get("url") or item.get("file_url") or "").strip()
            name = str(item.get("name") or item.get("filename") or "").strip()
            is_img = item.get("is_image")
        else:
            continue
        if not url or url in seen:
            continue
        seen.add(url)
        clean_path = url.split("?", 1)[0].split("#", 1)[0]
        if not name:
            name = Path(clean_path).name or "file"
        ext = (Path(name).suffix or Path(clean_path).suffix).lower()
        files.append({"url": url, "name": name, "is_image": bool(is_img) if isinstance(is_img, bool) else (ext in ALLOWED_IMAGE_EXTS)})
    return files


def get_student_tests_context(student_id, user_id, role):
    sid, sem_id, sem_label, enrolled_codes, _ = _resolve_student_scope(student_id, user_id, role)
    role_upper = str(role or "STUDENT").strip().upper()
    course_query = {"status": {"$ne": "INACTIVE"}}
    if sem_id:
        course_query["$or"] = [{"semester_id": sem_id}] + ([{"course_code": {"$in": sorted(enrolled_codes)}}] if enrolled_codes else [])
    elif enrolled_codes:
        course_query["course_code"] = {"$in": sorted(enrolled_codes)}
    elif role_upper != "ADMIN":
        course_query["course_code"] = "__NONE__"
    course_docs = list(courses_col().find(course_docs_query := course_query, {"_id": 0}).sort("course_code", 1))
    course_map = {str(c.get("course_code") or "").strip().upper(): c for c in course_docs if c.get("course_code")}
    target_codes = sorted(set(course_map.keys()) | enrolled_codes)
    if sem_id or target_codes:
        or_clauses = []
        if sem_id:
            or_clauses.append({"semester_id": sem_id})
        if target_codes:
            or_clauses.append({"course_code": {"$in": target_codes}})
        test_query = {"$or": or_clauses} if len(or_clauses) > 1 else or_clauses[0]
    elif role_upper == "ADMIN":
        test_query = {}
    else:
        test_query = {"course_code": "__NONE__"}
    today_str = datetime.now().strftime("%Y-%m-%d")
    tests = []
    counts = {"total": 0, "pending": 0, "submitted": 0, "late": 0, "graded": 0}
    for t in course_tests_col().find(test_query, {"_id": 0}).sort("created_at", -1):
        tid = str(t.get("test_id") or "").strip()
        c_code = str(t.get("course_code") or "").strip().upper()
        t_date = str(t.get("test_date") or "").strip()
        due_date = str(t.get("due_date") or t_date).strip()
        subs = t.get("submissions") or {}
        sub = subs.get(sid) if isinstance(subs.get(sid), dict) else {}
        files = _normalize_files(sub)
        obtained = sub.get("obtained_marks")
        has_marks = obtained not in (None, "")
        submitted_at = str(sub.get("submitted_at") or "").strip()
        raw_status = str(sub.get("submission_status") or "").strip().upper()
        if has_marks or raw_status == "GRADED":
            sub_status = "GRADED"
        elif raw_status in ("SUBMITTED", "LATE"):
            sub_status = raw_status
        elif files or submitted_at:
            sub_status = "LATE" if (due_date and submitted_at[:10] > due_date) else "SUBMITTED"
        else:
            sub_status = "PENDING"
        is_late_now = bool(due_date and today_str > due_date)
        counts["total"] += 1
        if sub_status == "GRADED":
            counts["graded"] += 1
        elif sub_status == "LATE":
            counts["late"] += 1
        elif sub_status == "SUBMITTED":
            counts["submitted"] += 1
        else:
            counts["pending"] += 1
        c_info = course_map.get(c_code) or {}
        tests.append({
            "test_id": tid, "title": str(t.get("title") or "Untitled Test").strip(), "course_code": c_code,
            "course_title": str(c_info.get("title") or c_code).strip(), "test_type": str(t.get("test_type") or "Quiz").strip(),
            "max_marks": _safe_float(t.get("max_marks"), 100.0), "test_date": t_date, "due_date": due_date,
            "notes": str(t.get("notes") or t.get("description") or "").strip(),
            "attachment_url": str(t.get("attachment_url") or "").strip(), "attachment_name": str(t.get("attachment_name") or "").strip(),
            "submission_status": sub_status, "is_late_now": is_late_now,
            "obtained_marks": obtained if has_marks else "", "percentage": sub.get("percentage", ""),
            "remarks": str(sub.get("remarks") or "").strip(), "submission_note": str(sub.get("submission_note") or sub.get("note") or "").strip(),
            "submitted_at": submitted_at, "files": files,
        })
    return {
        "tests": tests, "kpis": counts, "semester_id": sem_id, "semester_label": sem_label,
        "courses": [{"course_code": k, "title": str(v.get("title") or k).strip()} for k, v in sorted(course_map.items())],
        "today_str": today_str,
    }


def _save_submission_file(file_obj):
    if not file_obj or not getattr(file_obj, "name", ""):
        return None, None
    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(file_obj.name).name).strip("_") or "submission"
    ext = Path(safe_name).suffix.lower()
    if is_cloudinary_configured():
        url, orig_name, is_img, err = upload_academic_attachment(file_obj, folder="edupredict/submissions")
        if url:
            return {"url": url, "name": orig_name or safe_name, "is_image": is_img}, None
        if err and err != "not_configured" and ("allowed" in err.lower() or "unsupported" in err.lower() or "empty" in err.lower() or "exceeds" in err.lower()):
            return None, err
    else:
        _, _, is_img, err = upload_academic_attachment(file_obj, folder="edupredict/submissions")
        if err and err != "not_configured":
            return None, err
    upload_dir = Path(settings.BASE_DIR) / "static" / "uploads" / "submissions"
    upload_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex[:8]}_{safe_name}"
    if hasattr(file_obj, "seek"):
        file_obj.seek(0)
    with (upload_dir / stored_name).open("wb") as fh:
        for chunk in file_obj.chunks():
            fh.write(chunk)
    return {"url": f"/static/uploads/submissions/{stored_name}", "name": safe_name, "is_image": ext in ALLOWED_IMAGE_EXTS}, None


def submit_student_test(test_id, student_id, user_id, note="", files=None):
    tid = str(test_id or "").strip()
    if not tid:
        return None, "Test ID is required."
    sid, _, _, _, u_name = _resolve_student_scope(student_id, user_id, "STUDENT")
    if not sid:
        return None, "Student identity is missing."
    t_col = course_tests_col()
    test_doc = t_col.find_one({"test_id": tid})
    if not test_doc:
        return None, "Test not found."
    clean_note = str(note or "").strip()
    uploaded = []
    for f in (files or []):
        item, err = _save_submission_file(f)
        if err:
            return None, err
        if item:
            uploaded.append(item)
    if not uploaded and not clean_note:
        return None, "Please attach at least one file or write a submission note."
    now = datetime.now(timezone.utc)
    today_str = datetime.now().strftime("%Y-%m-%d")
    due_date = str(test_doc.get("due_date") or test_doc.get("test_date") or "").strip()
    status = "LATE" if (due_date and today_str > due_date) else "SUBMITTED"
    subs = test_doc.get("submissions") or {}
    prev_sub = subs.get(sid) if isinstance(subs.get(sid), dict) else {}
    existing_files = _normalize_files(prev_sub)
    combined_files = uploaded if uploaded else existing_files
    rec = student_records_col().find_one({"student_id": sid}, {"_id": 0, "full_name": 1}) or {}
    sub_doc = {
        **prev_sub,
        "student_id": sid,
        "user_id": str(user_id or "").strip(),
        "full_name": str(rec.get("full_name") or u_name or prev_sub.get("full_name") or sid).strip(),
        "submission_note": clean_note,
        "note": clean_note,
        "files": combined_files,
        "submission_status": status,
        "submitted_at": now.isoformat(),
    }
    t_col.update_one({"test_id": tid}, {"$set": {f"submissions.{sid}": sub_doc, "updated_at": now}})
    invalidate_cache()
    return sub_doc, None
