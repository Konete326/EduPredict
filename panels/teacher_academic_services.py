import json, uuid
from datetime import datetime, timezone
from analytics.ml_engine import run_prediction_pipeline
from core.db import attendance_records_col, course_tests_col, courses_col, get_cached, invalidate_cache, semesters_col, student_records_col, users_col
from panels.teacher_services import _action, _alert_attrs, _is_admin, _load_joined_students, _safe_float, _scope_key, _semester_label, _student_attrs, _view_action, provision_student_accounts


def _teacher_courses_list(teacher_user=None):
    sem_map = {str(s.get("semester_id") or "").strip(): s for s in semesters_col().find({}, {"_id": 0}) if s.get("semester_id")}
    is_adm = _is_admin(teacher_user)
    uid, email, tname = str((teacher_user or {}).get("user_id") or "").strip(), str((teacher_user or {}).get("email") or "").strip().lower(), str((teacher_user or {}).get("full_name") or "").strip().lower()
    courses = []
    for c in courses_col().find({}, {"_id": 0}).sort("course_code", 1):
        code, status = str(c.get("course_code") or "").strip().upper(), str(c.get("status") or "ACTIVE").strip().upper()
        if not code or status == "INACTIVE": continue
        if not is_adm and not ((uid and str(c.get("instructor_id") or "").strip() == uid) or (email and str(c.get("instructor_email") or "").strip().lower() == email) or (tname and str(c.get("instructor") or "").strip().lower() == tname)): continue
        sem_id = str(c.get("semester_id") or "").strip()
        courses.append({"course_code": code, "title": str(c.get("title") or code).strip(), "semester_id": sem_id, "semester_label": _semester_label(sem_map.get(sem_id)), "instructor": str(c.get("instructor") or "TBA").strip(), "instructor_id": str(c.get("instructor_id") or "").strip(), "instructor_email": str(c.get("instructor_email") or "").strip().lower(), "status": status})
    return courses


def _build_teacher_courses_context(teacher_user=None):
    courses = _teacher_courses_list(teacher_user)
    students = _load_joined_students(teacher_user)
    stats = {}
    for s in students:
        bucket = stats.setdefault(s["course_code"], {"count": 0, "att": 0.0, "marks": 0.0})
        bucket["count"] += 1
        bucket["att"] += s["attendance_pct"]
        bucket["marks"] += s["internal_marks"]
    rows, cards, sem_ids = [], [], set()
    for c in courses:
        code = c["course_code"]
        if c["semester_id"]:
            sem_ids.add(c["semester_id"])
        st = stats.get(code) or {"count": 0, "att": 0.0, "marks": 0.0}
        cnt = st["count"]
        avg_att = round(st["att"] / cnt, 1) if cnt else 0.0
        avg_marks = round(st["marks"] / cnt, 1) if cnt else 0.0
        c["student_count"], c["avg_attendance"], c["avg_marks"] = cnt, avg_att, avg_marks
        badge = {"text": c["status"], "status": "success" if c["status"] == "ACTIVE" else "warning"}
        actions = [_view_action(f"Course {code}", {"title": f"{code} · {c['title']}", "subtitle": c["semester_label"], "badge": c["status"], "items": [{"label": "Course Code", "value": code}, {"label": "Semester", "value": c["semester_label"]}, {"label": "Instructor", "value": c["instructor"]}, {"label": "Enrolled Students", "value": str(cnt)}, {"label": "Avg Attendance", "value": f"{avg_att:.1f}%"}, {"label": "Avg Marks", "value": f"{avg_marks:.1f}"}]})]
        rows.append([code, c["title"], c["semester_label"], str(cnt), f"{avg_att:.1f}%", f"{avg_marks:.1f}", badge, {"actions": actions}])
        cards.append({"id": code, "title": f"{code} · {c['title']}", "subtitle": c["semester_label"], "badge": badge, "meta": [{"label": "Students", "value": str(cnt)}, {"label": "Avg Att", "value": f"{avg_att:.1f}%"}, {"label": "Avg Marks", "value": f"{avg_marks:.1f}"}], "actions": actions})
    return {"courses": courses, "course_headers": ["Code", "Course Title", "Semester", "Students", "Avg Att.", "Avg Marks", "Status", "Actions"], "course_rows": rows, "course_cards": cards, "total_courses": len(courses), "total_semesters": len(sem_ids), "total_students": len(students)}


def get_teacher_courses_context(teacher_user=None):
    return get_cached(f"teacher:courses:{_scope_key(teacher_user)}", lambda: _build_teacher_courses_context(teacher_user), ttl=25.0)


def _risk_badge(risk_level):
    r = str(risk_level or "LOW").strip().upper()
    if r == "HIGH":
        return {"text": "HIGH", "status": "danger"}
    if r == "MEDIUM":
        return {"text": "MEDIUM", "status": "warning"}
    return {"text": "LOW", "status": "success"}


def get_teacher_students_context(teacher_user=None, course_filter="ALL", semester_filter="ALL"):
    all_students = _load_joined_students(teacher_user)
    courses = _teacher_courses_list(teacher_user)
    cf = str(course_filter or "ALL").strip().upper() or "ALL"
    sf = str(semester_filter or "ALL").strip() or "ALL"
    course_opts = sorted({c["course_code"] for c in courses} | {s["course_code"] for s in all_students if s.get("course_code")})
    sem_opts_map = {s["semester_id"]: s.get("semester_label") or s["semester_id"] for s in all_students if s.get("semester_id")}
    for c in courses:
        if c.get("semester_id"): sem_opts_map[c["semester_id"]] = c.get("semester_label") or c["semester_id"]
    filtered = [s for s in all_students if (cf == "ALL" or s["course_code"] == cf) and (sf == "ALL" or s.get("semester_id") == sf or s.get("semester_label") == sf)]
    rows, cards, high_cnt, med_cnt = [], [], 0, 0
    for s in filtered:
        risk = str(s.get("risk_level") or "LOW").strip().upper()
        high_cnt += int(risk == "HIGH")
        med_cnt += int(risk == "MEDIUM")
        prob_pct = round(_safe_float(s.get("risk_probability")) * (100.0 if _safe_float(s.get("risk_probability")) <= 1.0 else 1.0), 1)
        gpa_str, r_badge = f"{s['predicted_gpa']:.2f}" if s.get("predicted_gpa") is not None else "-", _risk_badge(risk)
        actions = [
            _view_action(f"Prediction: {s['full_name']}", {"title": s["full_name"], "subtitle": f"{s['student_id']} · {s['course_code']}", "badge": f"{risk} RISK", "items": [{"label": "Semester", "value": s.get("semester_label") or "-"}, {"label": "Dropout Risk", "value": f"{risk} ({prob_pct:.1f}%)"}, {"label": "Expected GPA", "value": gpa_str}, {"label": "Attendance", "value": f"{s['attendance_pct']:.1f}%"}, {"label": "Internal Marks", "value": f"{s['internal_marks']:.1f}"}, {"label": "Assignment Score", "value": f"{s['assignment_score']:.1f}"}, {"label": "LMS Hours / Wk", "value": f"{s['lms_hours_weekly']:.1f}"}, {"label": "Previous GPA", "value": f"{s['previous_gpa']:.2f}"}, {"label": "Recommendation", "value": s.get("recommendation") or "Update marks and attendance to generate tailored ML advice."}]}),
            _action("Update", "fa-solid fa-pen-to-square", "openUpdateMarksModal(this)", f"Update marks for {s['full_name']}", _student_attrs(s)),
            _action("Message", "fa-solid fa-envelope", "openSendMessageModal(this)", f"Message {s['full_name']}", _alert_attrs(s), variant="primary"),
        ]
        rows.append([s["student_id"], s["full_name"], s.get("semester_label") or "-", s["course_code"], f"{s['attendance_pct']:.1f}%", f"{s['internal_marks']:.1f}", gpa_str, r_badge, {"actions": actions}])
        cards.append({"id": s["student_id"], "title": s["full_name"], "subtitle": f"{s['student_id']} · {s.get('semester_label') or '-'}", "badge": r_badge, "meta": [{"label": "Course", "value": s["course_code"]}, {"label": "Attendance", "value": f"{s['attendance_pct']:.1f}%"}, {"label": "Marks", "value": f"{s['internal_marks']:.1f}"}, {"label": "Pred GPA", "value": gpa_str}], "actions": actions})
    total, gpa_vals = len(filtered), [s["predicted_gpa"] for s in filtered if s.get("predicted_gpa") is not None]
    return {"students": filtered, "student_headers": ["Student ID", "Name", "Semester", "Course", "Attendance", "Marks", "Pred GPA", "Risk", "Actions"], "student_rows": rows, "student_cards": cards, "filter_options": {"courses": course_opts, "semesters": [{"value": k, "label": v} for k, v in sorted(sem_opts_map.items(), key=lambda x: x[1])], "course_filter": cf, "semester_filter": sf}, "kpis": {"total_students": total, "high_risk_count": high_cnt, "medium_risk_count": med_cnt, "avg_attendance": round(sum(s["attendance_pct"] for s in filtered) / total, 1) if total else 0.0, "avg_marks": round(sum(s["internal_marks"] for s in filtered) / total, 1) if total else 0.0, "avg_pred_gpa": round(sum(gpa_vals) / len(gpa_vals), 2) if gpa_vals else 0.0}}


def get_teacher_marks_context(teacher_user=None, course_filter="ALL"):
    courses, students = _teacher_courses_list(teacher_user), _load_joined_students(teacher_user)
    cf = str(course_filter or "ALL").strip().upper() or "ALL"
    course_options = [{"value": c["course_code"], "label": f"{c['course_code']} · {c['title']}", "semester_id": c["semester_id"], "semester_label": c["semester_label"]} for c in courses]
    selected_course = next((c for c in courses if c["course_code"] == cf), None) if cf != "ALL" else (courses[0] if courses else None)
    filtered = [s for s in students if cf == "ALL" or s["course_code"] == cf]
    rows, cards = [], []
    for s in filtered:
        gpa_str = f"{s['predicted_gpa']:.2f}" if s.get("predicted_gpa") is not None else "-"
        actions = [_action("Edit Marks", "fa-solid fa-pen-to-square", "openUpdateMarksModal(this)", f"Edit marks for {s['full_name']}", _student_attrs(s), variant="primary")]
        rows.append([s["student_id"], s["full_name"], s.get("semester_label") or "-", s["course_code"], f"{s['attendance_pct']:.1f}%", f"{s['internal_marks']:.1f}", gpa_str, s["badge"], {"actions": actions}])
        cards.append({"id": s["student_id"], "title": s["full_name"], "subtitle": f"{s['student_id']} · {s['course_code']}", "badge": s["badge"], "meta": [{"label": "Semester", "value": s.get("semester_label") or "-"}, {"label": "Att", "value": f"{s['attendance_pct']:.1f}%"}, {"label": "Marks", "value": f"{s['internal_marks']:.1f}"}], "actions": actions})
    return {"course_options": course_options, "selected_course": selected_course, "course_filter": cf, "students": filtered, "roster_headers": ["Student ID", "Name", "Semester", "Course", "Attendance", "Marks", "Pred GPA", "Status", "Actions"], "roster_rows": rows, "roster_cards": cards}


def _extract_bulk_items(post_data):
    if post_data.get("bulk_rows_json"):
        try:
            parsed = json.loads(post_data.get("bulk_rows_json"))
            if isinstance(parsed, list): return parsed
        except (TypeError, ValueError): pass
    if hasattr(post_data, "getlist"):
        sids = [str(x).strip() for x in post_data.getlist("student_id") if str(x).strip()]
        if len(sids) > 1:
            atts, marks_l, assigns, lms_l, gpas, codes, sems = post_data.getlist("attendance_pct"), post_data.getlist("internal_marks"), post_data.getlist("assignment_score"), post_data.getlist("lms_hours_weekly"), post_data.getlist("previous_gpa"), post_data.getlist("course_code"), post_data.getlist("semester_id")
            return [{"student_id": sid, "attendance_pct": atts[i] if i < len(atts) else "", "internal_marks": marks_l[i] if i < len(marks_l) else "", "assignment_score": assigns[i] if i < len(assigns) else "", "lms_hours_weekly": lms_l[i] if i < len(lms_l) else "", "previous_gpa": gpas[i] if i < len(gpas) else "", "course_code": codes[i] if i < len(codes) else post_data.get("course_code"), "semester_id": sems[i] if i < len(sems) else post_data.get("semester_id")} for i, sid in enumerate(sids)]
    raw_ids = post_data.get("student_ids")
    if raw_ids:
        sids = raw_ids if isinstance(raw_ids, list) else [x.strip() for x in str(raw_ids).split(",") if x.strip()]
        return [{"student_id": sid, "attendance_pct": post_data.get(f"attendance_pct_{sid}"), "internal_marks": post_data.get(f"internal_marks_{sid}"), "assignment_score": post_data.get(f"assignment_score_{sid}"), "lms_hours_weekly": post_data.get(f"lms_hours_weekly_{sid}"), "previous_gpa": post_data.get(f"previous_gpa_{sid}"), "course_code": post_data.get(f"course_code_{sid}") or post_data.get("course_code"), "semester_id": post_data.get(f"semester_id_{sid}") or post_data.get("semester_id")} for sid in sids]
    return [post_data]


def save_student_marks_and_attendance(post_data, teacher_user=None):
    items = _extract_bulk_items(post_data)
    sem_map = {str(s.get("semester_id") or "").strip(): s for s in semesters_col().find({}, {"_id": 0}) if s.get("semester_id")}
    saved, now = 0, datetime.now(timezone.utc)
    for item in items:
        raw_sid = str(item.get("student_id") or "").strip()
        if len(raw_sid) < 2:
            continue
        existing = student_records_col().find_one({"student_id": raw_sid}, {"_id": 0}) or student_records_col().find_one({"student_id": raw_sid.upper()}, {"_id": 0}) or {}
        u_doc = users_col().find_one({"student_id": raw_sid}, {"_id": 0, "full_name": 1, "semester_id": 1, "batch": 1}) or {}
        sid = str(existing.get("student_id") or raw_sid).strip()
        course_code = str(item.get("course_code") or existing.get("course_code") or "CS-101").strip().upper()
        c_doc = courses_col().find_one({"course_code": course_code}, {"_id": 0, "semester_id": 1}) or {}
        sem_id = str(item.get("semester_id") or existing.get("semester_id") or u_doc.get("semester_id") or c_doc.get("semester_id") or "").strip()
        sem_label = _semester_label(sem_map.get(sem_id)) if sem_id in sem_map else str(item.get("semester_label") or existing.get("semester_label") or "-")
        full_name = str(item.get("full_name") or item.get("name") or existing.get("full_name") or u_doc.get("full_name") or f"Student {sid}").strip()
        try:
            att = max(0.0, min(100.0, float(item.get("attendance_pct") if item.get("attendance_pct") not in (None, "") else (item.get("attendance") or existing.get("attendance_pct") or 0.0))))
            marks = max(0.0, min(100.0, float(item.get("internal_marks") if item.get("internal_marks") not in (None, "") else (item.get("marks") or existing.get("internal_marks") or 0.0))))
            assign = max(0.0, min(100.0, float(item.get("assignment_score") if item.get("assignment_score") not in (None, "") else (existing.get("assignment_score") or marks))))
            lms = max(0.0, min(168.0, float(item.get("lms_hours_weekly") if item.get("lms_hours_weekly") not in (None, "") else (existing.get("lms_hours_weekly") or 0.0))))
            gpa = max(0.0, min(4.0, float(item.get("previous_gpa") if item.get("previous_gpa") not in (None, "") else (existing.get("previous_gpa") or 0.0))))
        except (TypeError, ValueError):
            return 0, f"Invalid numeric marks or attendance for student {sid}."
        doc = {"student_id": sid, "full_name": full_name, "batch": str(item.get("batch") or existing.get("batch") or u_doc.get("batch") or "2026-A").strip(), "course_code": course_code, "semester_id": sem_id, "semester_label": sem_label, "attendance_pct": round(att, 2), "attendance_rate": round(att, 2), "internal_marks": round(marks, 2), "marks": round(marks, 2), "final_score": round(marks, 2), "assignment_score": round(assign, 2), "lms_hours_weekly": round(lms, 2), "previous_gpa": round(gpa, 2), "gpa": round(gpa, 2), "updated_at": now}
        if isinstance(teacher_user, dict) and str(teacher_user.get("role") or "").upper() != "ADMIN":
            doc["teacher_user_id"] = str(teacher_user.get("user_id") or "").strip()
            doc["teacher_name"] = str(teacher_user.get("full_name") or "Teacher").strip()
            doc["teacher_email"] = str(teacher_user.get("email") or "").strip().lower()
        student_records_col().update_one({"student_id": sid}, {"$set": doc}, upsert=True)
        if not u_doc and full_name:
            provision_student_accounts([doc], teacher_user)
        saved += 1
    if saved == 0:
        return 0, "Please provide at least one valid student ID."
    run_prediction_pipeline(persist=True)
    invalidate_cache()
    return saved, None


def _parse_json_list(raw):
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, list) else []
    except (TypeError, ValueError):
        return []


def _norm_att_status(val):
    s = str(val or "PRESENT").strip().upper()
    if s in ("P", "PRESENT"): return "PRESENT"
    if s in ("A", "ABSENT"): return "ABSENT"
    if s in ("L", "LEAVE", "EXCUSED"): return "LEAVE"
    return "PRESENT"


def get_teacher_attendance_context(teacher_user=None, course_filter="ALL", date_str=""):
    courses, students = _teacher_courses_list(teacher_user), _load_joined_students(teacher_user)
    cf = str(course_filter or "ALL").strip().upper() or "ALL"
    selected_date = str(date_str or "").strip() or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    course_options = [{"value": c["course_code"], "label": f"{c['course_code']} · {c['title']}", "semester_id": c["semester_id"], "semester_label": c["semester_label"]} for c in courses]
    selected_course = next((c for c in courses if c["course_code"] == cf), None) if cf != "ALL" else (courses[0] if courses else None)
    filtered = [s for s in students if cf == "ALL" or s["course_code"] == cf]
    att_query = {"date": selected_date, **({"course_code": cf} if cf != "ALL" else {})}
    existing_map = {str(r.get("student_id") or "").strip(): str(r.get("status") or "PRESENT").strip().upper() for r in attendance_records_col().find(att_query, {"_id": 0, "student_id": 1, "status": 1})}
    att_students, present_cnt, absent_cnt, leave_cnt, marked_cnt = [], 0, 0, 0, 0
    for s in filtered:
        st = existing_map.get(s["student_id"], "")
        marked_cnt += int(bool(st))
        eff = st or "PRESENT"
        present_cnt += int(eff == "PRESENT")
        absent_cnt += int(eff == "ABSENT")
        leave_cnt += int(eff == "LEAVE")
        att_students.append({**s, "today_status": eff, "has_marked": bool(st)})
    return {"course_options": course_options, "selected_course": selected_course, "course_filter": cf, "selected_date": selected_date, "students": att_students, "kpis": {"total_students": len(att_students), "present_count": present_cnt, "absent_count": absent_cnt, "leave_count": leave_cnt, "marked_count": marked_cnt}}


def save_course_attendance(post_data, teacher_user=None):
    date_str = str(post_data.get("date") or post_data.get("attendance_date") or datetime.now(timezone.utc).strftime("%Y-%m-%d")).strip()
    course_code = str(post_data.get("course_code") or "").strip().upper()
    items = _parse_json_list(post_data.get("attendance_json"))
    if not items and post_data.get("student_ids"):
        raw_ids = post_data.get("student_ids")
        sids = raw_ids if isinstance(raw_ids, list) else [x.strip() for x in str(raw_ids).split(",") if x.strip()]
        items = [{"student_id": sid, "status": post_data.get(f"status_{sid}") or "PRESENT", "course_code": post_data.get(f"course_code_{sid}") or course_code} for sid in sids]
    elif not items and hasattr(post_data, "getlist"):
        sids, statuses = [str(x).strip() for x in post_data.getlist("student_id") if str(x).strip()], post_data.getlist("status")
        items = [{"student_id": sid, "status": post_data.get(f"status_{sid}") or (statuses[i] if i < len(statuses) else "PRESENT"), "course_code": post_data.get(f"course_code_{sid}") or course_code} for i, sid in enumerate(sids)]
    if not items:
        return 0, "Please select at least one student to record attendance."
    now = datetime.now(timezone.utc)
    t_uid, t_name = str((teacher_user or {}).get("user_id") or "").strip(), str((teacher_user or {}).get("full_name") or "Teacher").strip()
    att_col, rec_col, saved = attendance_records_col(), student_records_col(), 0
    for item in items:
        sid = str(item.get("student_id") or "").strip()
        if not sid: continue
        status = _norm_att_status(item.get("status"))
        rec = rec_col.find_one({"student_id": sid}, {"_id": 0}) or {}
        c_code = str(item.get("course_code") or course_code or rec.get("course_code") or "CS-101").strip().upper()
        att_col.update_one({"course_code": c_code, "date": date_str, "student_id": sid}, {"$set": {"course_code": c_code, "date": date_str, "student_id": sid, "full_name": str(rec.get("full_name") or sid), "semester_id": str(rec.get("semester_id") or ""), "status": status, "teacher_user_id": t_uid, "teacher_name": t_name, "updated_at": now}, "$setOnInsert": {"created_at": now}}, upsert=True)
        all_recs = list(att_col.find({"student_id": sid}, {"_id": 0, "status": 1}))
        pct = round((sum(1 for r in all_recs if r.get("status") == "PRESENT") / len(all_recs)) * 100.0, 2) if all_recs else 100.0
        rec_col.update_one({"student_id": sid}, {"$set": {"attendance_pct": pct, "attendance_rate": pct, "updated_at": now}, "$setOnInsert": {"full_name": str(rec.get("full_name") or sid), "course_code": c_code, "semester_id": str(rec.get("semester_id") or "")}}, upsert=True)
        saved += 1
    if saved == 0:
        return 0, "No valid student attendance rows found."
    run_prediction_pipeline(persist=True)
    invalidate_cache()
    return saved, None


def get_teacher_tests_context(teacher_user=None, course_filter="ALL"):
    courses, students = _teacher_courses_list(teacher_user), _load_joined_students(teacher_user)
    cf = str(course_filter or "ALL").strip().upper() or "ALL"
    course_options = [{"value": c["course_code"], "label": f"{c['course_code']} · {c['title']}", "semester_id": c["semester_id"], "semester_label": c["semester_label"]} for c in courses]
    allowed_codes = {c["course_code"] for c in courses}
    query = {"course_code": cf} if cf != "ALL" else ({"course_code": {"$in": sorted(allowed_codes)}} if not _is_admin(teacher_user) and allowed_codes else {})
    tests = []
    for t in course_tests_col().find(query, {"_id": 0}).sort("created_at", -1):
        c_code, subs = str(t.get("course_code") or "").strip().upper(), t.get("submissions") or {}
        c_students = [s for s in students if s["course_code"] == c_code]
        graded_vals = [_safe_float(v.get("percentage")) for v in subs.values() if isinstance(v, dict)]
        roster = [{"student_id": s["student_id"], "full_name": s["full_name"], "obtained_marks": subs.get(s["student_id"], {}).get("obtained_marks", ""), "percentage": subs.get(s["student_id"], {}).get("percentage", "")} for s in c_students]
        tests.append({"test_id": str(t.get("test_id") or "").strip(), "title": str(t.get("title") or "Untitled Test").strip(), "course_code": c_code, "test_type": str(t.get("test_type") or "Quiz").strip(), "max_marks": _safe_float(t.get("max_marks"), 100.0), "test_date": str(t.get("test_date") or "").strip(), "description": str(t.get("description") or "").strip(), "graded_count": len(subs), "total_students": len(c_students), "avg_score": round(sum(graded_vals) / len(graded_vals), 1) if graded_vals else 0.0, "roster_json": json.dumps(roster)})
    return {"course_options": course_options, "course_filter": cf, "tests": tests, "students": [s for s in students if cf == "ALL" or s["course_code"] == cf], "kpis": {"total_tests": len(tests), "graded_tests": sum(1 for t in tests if t["graded_count"] > 0), "total_students": len(students)}}


def _validate_test_payload(post_data, require_id=False):
    tid = str(post_data.get("test_id") or "").strip()
    title, course_code = str(post_data.get("title") or "").strip(), str(post_data.get("course_code") or "").strip().upper()
    if (require_id and not tid) or not title or not course_code:
        return None, "Test ID, title, and course are required." if require_id else "Test title and course are required."
    try:
        max_marks = float(post_data.get("max_marks") or 100.0)
        if max_marks <= 0: raise ValueError()
    except (TypeError, ValueError):
        return None, "Max marks must be greater than 0."
    return {"test_id": tid, "title": title, "course_code": course_code, "test_type": str(post_data.get("test_type") or "Quiz").strip() or "Quiz", "max_marks": round(max_marks, 2), "test_date": str(post_data.get("test_date") or "").strip(), "description": str(post_data.get("description") or "").strip()}, None


def create_course_test(post_data, teacher_user=None):
    data, err = _validate_test_payload(post_data, require_id=False)
    if err: return None, err
    now = datetime.now(timezone.utc)
    c_doc = courses_col().find_one({"course_code": data["course_code"]}, {"_id": 0, "semester_id": 1}) or {}
    doc = {**data, "test_id": f"TST-{uuid.uuid4().hex[:6].upper()}", "semester_id": str(c_doc.get("semester_id") or "").strip(), "test_date": data["test_date"] or now.strftime("%Y-%m-%d"), "submissions": {}, "teacher_user_id": str((teacher_user or {}).get("user_id") or "").strip(), "teacher_name": str((teacher_user or {}).get("full_name") or "Teacher").strip(), "created_at": now, "updated_at": now}
    course_tests_col().insert_one(doc)
    invalidate_cache()
    return doc, None


def update_course_test(post_data, teacher_user=None):
    data, err = _validate_test_payload(post_data, require_id=True)
    if err: return None, err
    tid = data.pop("test_id")
    updates = {**data, "updated_at": datetime.now(timezone.utc)}
    res = course_tests_col().update_one({"test_id": tid}, {"$set": updates})
    if not res.matched_count: return None, "Test not found."
    invalidate_cache()
    return {"test_id": tid, **updates}, None


def delete_course_test(test_id):
    tid = str(test_id or "").strip()
    if not tid: return False, "Test ID is required."
    res = course_tests_col().delete_one({"test_id": tid})
    invalidate_cache()
    return (True, None) if res.deleted_count else (False, "Test not found.")


def grade_test_submissions(post_data, teacher_user=None):
    tid, t_col = str(post_data.get("test_id") or "").strip(), course_tests_col()
    test_doc = t_col.find_one({"test_id": tid})
    if not test_doc: return 0, "Test not found."
    max_marks = _safe_float(test_doc.get("max_marks"), 100.0) or 100.0
    scores = _parse_json_list(post_data.get("scores_json"))
    if not scores and hasattr(post_data, "getlist"):
        sids, marks_l = [str(x).strip() for x in post_data.getlist("student_id") if str(x).strip()], post_data.getlist("obtained_marks")
        scores = [{"student_id": sid, "obtained_marks": post_data.get(f"marks_{sid}") if post_data.get(f"marks_{sid}") not in (None, "") else (marks_l[i] if i < len(marks_l) else "")} for i, sid in enumerate(sids)]
    subs, now, graded_sids, rec_col = dict(test_doc.get("submissions") or {}), datetime.now(timezone.utc), set(), student_records_col()
    for item in scores:
        sid, raw_m = str(item.get("student_id") or "").strip(), item.get("obtained_marks")
        if not sid or raw_m in (None, ""): continue
        try: val = float(raw_m)
        except (TypeError, ValueError): return 0, f"Invalid marks for student {sid}."
        if val < 0 or val > max_marks: return 0, f"Marks for {sid} must be between 0 and {max_marks:g}."
        pct = round((val / max_marks) * 100.0, 2)
        rec = rec_col.find_one({"student_id": sid}, {"_id": 0, "full_name": 1}) or {}
        subs[sid] = {"student_id": sid, "full_name": str(rec.get("full_name") or sid), "obtained_marks": round(val, 2), "percentage": pct, "graded_at": now.isoformat()}
        graded_sids.add(sid)
    if not graded_sids: return 0, "Please enter marks for at least one student."
    t_col.update_one({"test_id": tid}, {"$set": {"submissions": subs, "updated_at": now}})
    all_tests = list(t_col.find({}, {"_id": 0, "submissions": 1}))
    for sid in graded_sids:
        pcts = [_safe_float((t.get("submissions") or {}).get(sid, {}).get("percentage")) for t in all_tests if isinstance((t.get("submissions") or {}).get(sid), dict)]
        avg_pct = round(sum(pcts) / len(pcts), 2) if pcts else 0.0
        rec_col.update_one({"student_id": sid}, {"$set": {"internal_marks": avg_pct, "marks": avg_pct, "final_score": avg_pct, "updated_at": now}})
    run_prediction_pipeline(persist=True)
    invalidate_cache()
    return len(graded_sids), None
