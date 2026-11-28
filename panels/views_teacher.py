from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse
from core.db import notifications_col
from core.decorators import role_required
from panels.teacher_academic_services import create_course_test, delete_course_test, get_teacher_attendance_context, get_teacher_courses_context, get_teacher_marks_context, get_teacher_students_context, get_teacher_test_grade_context, get_teacher_tests_context, grade_test_submissions, save_course_attendance, save_student_marks_and_attendance, update_course_test
from panels.teacher_alert_services import get_teacher_portal_meta, toggle_teacher_auto_alerts
from panels.teacher_services import delete_student_record, get_teacher_dashboard_context, notify_all_high_risk_students, reply_teacher_feedback, send_student_alert, update_student_record_inline


def _param(request, key, default=""):
    return str(request.POST.get(key) or request.GET.get(key) or default).strip()


def _actor_label(request):
    user = request.session.get("user") or {}
    return str(user.get("full_name") or user.get("email") or "Teacher").strip()


def _actor_user_id(request):
    return str((request.session.get("user") or {}).get("user_id") or "").strip()


def _flash(request, ok, err, success_msg):
    if err or not ok:
        messages.error(request, err or "Action failed.")
    else:
        messages.success(request, success_msg)


def _handle_common_post(request):
    action = _param(request, "action").lower()
    user = request.session.get("user") or {}
    if action in ("update_student", "manual_entry", "update_marks"):
        doc, err = update_student_record_inline(request.POST, teacher_user=user)
        _flash(request, doc is not None, err, f"Saved marks for {doc['full_name']} ({doc['student_id']}) and updated predictions." if doc else "")
        return True
    if action == "send_alert":
        sev = _param(request, "severity") or _param(request, "urgency", "WARNING")
        doc, err = send_student_alert(_param(request, "student_id"), _param(request, "full_name"), _param(request, "course_code"), sev, request.POST.get("message") or request.POST.get("message_text"), _actor_label(request))
        if doc and doc.get("_id") and _actor_user_id(request):
            notifications_col().update_one({"_id": doc["_id"]}, {"$set": {"sender_user_id": _actor_user_id(request)}})
        _flash(request, doc is not None, err, f"Alert sent to {_param(request, 'student_id')}." if doc else "")
        return True
    if action == "delete_student":
        sid = _param(request, "student_id")
        ok, err = delete_student_record(sid)
        _flash(request, ok, err, f"Removed student record {sid}.")
        return True
    if action == "notify_all_high_risk":
        sent_count, err = notify_all_high_risk_students(_actor_label(request), sender_user_id=_actor_user_id(request), teacher_user=user)
        _flash(request, sent_count > 0, err, f"Sent alerts to {sent_count} high-risk / low-attendance student(s).")
        return True
    if action == "toggle_auto_alerts":
        state, err = toggle_teacher_auto_alerts(_param(request, "enabled") == "1", _actor_label(request))
        _flash(request, err is None, err, f"Auto-alerts below 75% attendance {'enabled' if state else 'paused'}.")
        return True
    if action in ("reply_feedback", "resolve_feedback"):
        tid = _param(request, "ticket_id")
        reply_txt = _param(request, "reply_text") or ("Resolved by teacher." if action == "resolve_feedback" else "")
        ok, err = reply_teacher_feedback(tid, reply_txt, teacher_user=user, resolve_ticket=True)
        _flash(request, ok, err, f"Reply sent and ticket {tid} marked resolved.")
        return True
    return False


@role_required(["TEACHER", "ADMIN"])
def teacher_dashboard(request):
    if request.method == "POST":
        try:
            if not _handle_common_post(request):
                messages.error(request, "Unknown action.")
        except Exception as exc:
            messages.error(request, f"Database error: {exc}")
        return redirect("panels:teacher_dashboard")

    user = request.session.get("user") or {}
    context = {
        "page_title": "Dashboard", "active_role": "TEACHER",
        "kpis": {"total_students": 0, "avg_attendance": 0.0, "avg_marks": 0.0, "at_risk_count": 0, "courses_count": 0},
        "chart_data": {"course_summary": {"labels": [], "attendance": [], "marks": []}, "badge_breakdown": {"labels": ["Excellent", "Stable", "Needs Help", "High Risk"], "counts": [0, 0, 0, 0]}},
        "at_risk_headers": ["Student ID", "Name", "Course", "Attendance", "Marks", "Status", "Actions"], "at_risk_rows": [],
        "assigned_courses": [], "course_scope": "ALL", "my_courses_count": 0, "all_courses_count": 0,
        "admin_contact": {"name": "EduPredict Admin", "email": "admin@edupredict.edu"}, "db_error": None,
    }
    try:
        context.update(get_teacher_dashboard_context(teacher_user=user))
        context.update(get_teacher_portal_meta(user, course_scope=_param(request, "scope", "AUTO").upper()))
    except Exception as exc:
        context["db_error"] = str(exc)
    return render(request, "panels/teacher_dashboard.html", context)


@role_required(["TEACHER", "ADMIN"])
def teacher_courses(request):
    user = request.session.get("user") or {}
    context = {"page_title": "My Courses", "active_role": "TEACHER", "db_error": None}
    try:
        context.update(get_teacher_courses_context(user))
    except Exception as exc:
        context["db_error"] = str(exc)
    return render(request, "panels/teacher_courses.html", context)


@role_required(["TEACHER", "ADMIN"])
def teacher_students(request):
    if request.method == "POST":
        try:
            if not _handle_common_post(request):
                messages.error(request, "Unknown action.")
        except Exception as exc:
            messages.error(request, f"Database error: {exc}")
        return redirect("panels:teacher_students")

    user = request.session.get("user") or {}
    context = {"page_title": "My Students", "active_role": "TEACHER", "db_error": None}
    try:
        context.update(
            get_teacher_students_context(
                user,
                course_filter=_param(request, "course", "ALL"),
                semester_filter=_param(request, "semester", "ALL"),
            )
        )
    except Exception as exc:
        context["db_error"] = str(exc)
    return render(request, "panels/teacher_students.html", context)


@role_required(["TEACHER", "ADMIN"])
def teacher_marks(request):
    user = request.session.get("user") or {}
    if request.method == "POST":
        action = _param(request, "action").lower()
        try:
            if action == "save_bulk_marks":
                saved, err = save_student_marks_and_attendance(request.POST, user)
                msg = f"Saved marks & attendance for {saved} student(s) and updated predictions." if isinstance(saved, int) else "Saved marks & attendance and updated predictions."
                _flash(request, bool(saved) and not err, err, msg)
            elif not _handle_common_post(request):
                messages.error(request, "Unknown action.")
        except Exception as exc:
            messages.error(request, f"Database error: {exc}")
        course_q = _param(request, "course")
        if course_q and course_q.upper() != "ALL":
            return redirect(f"{reverse('panels:teacher_marks')}?course={course_q}")
        return redirect("panels:teacher_marks")

    context = {"page_title": "Attendance & Marks", "active_role": "TEACHER", "db_error": None}
    try:
        context.update(get_teacher_marks_context(user, course_filter=_param(request, "course", "ALL")))
    except Exception as exc:
        context["db_error"] = str(exc)
    return render(request, "panels/teacher_marks.html", context)


@role_required(["TEACHER", "ADMIN"])
def teacher_attendance(request):
    user = request.session.get("user") or {}
    if request.method == "POST":
        action = _param(request, "action").lower()
        try:
            if action in ("", "save_attendance"):
                saved, err = save_course_attendance(request.POST, user)
                _flash(request, bool(saved) and not err, err, f"Saved attendance for {saved} student(s) and updated predictions.")
            elif not _handle_common_post(request):
                messages.error(request, "Unknown action.")
        except Exception as exc:
            messages.error(request, f"Database error: {exc}")
        course_q, date_q = _param(request, "course"), _param(request, "date")
        qs = "&".join([p for p in (f"course={course_q}" if course_q and course_q.upper() != "ALL" else "", f"date={date_q}" if date_q else "") if p])
        return redirect(f"{reverse('panels:teacher_attendance')}?{qs}" if qs else "panels:teacher_attendance")

    context = {"page_title": "Attendance", "active_role": "TEACHER", "db_error": None}
    try:
        context.update(get_teacher_attendance_context(user, course_filter=_param(request, "course", "ALL"), date_str=_param(request, "date", "")))
    except Exception as exc:
        context["db_error"] = str(exc)
    return render(request, "panels/teacher_attendance.html", context)


@role_required(["TEACHER", "ADMIN"])
def teacher_tests(request):
    user = request.session.get("user") or {}
    if request.method == "POST":
        action = _param(request, "action").lower()
        try:
            if action == "create_test":
                doc, err = create_course_test(request.POST, user, attachment=request.FILES.get("attachment"))
                _flash(request, doc is not None, err, f"Created test '{doc['title']}'." if doc else "")
            elif action == "update_test":
                doc, err = update_course_test(request.POST, user, attachment=request.FILES.get("attachment"))
                _flash(request, doc is not None, err, f"Updated test '{doc['title']}'." if doc else "")
            elif action == "delete_test":
                ok, err = delete_course_test(_param(request, "test_id"))
                _flash(request, ok, err, "Test deleted.")
            elif action == "grade_test":
                graded, err = grade_test_submissions(request.POST, user)
                _flash(request, bool(graded) and not err, err, f"Graded {graded} student(s) and updated internal marks.")
            elif not _handle_common_post(request):
                messages.error(request, "Unknown action.")
        except Exception as exc:
            messages.error(request, f"Database error: {exc}")
        course_q = _param(request, "course")
        if course_q and course_q.upper() != "ALL":
            return redirect(f"{reverse('panels:teacher_tests')}?course={course_q}")
        return redirect("panels:teacher_tests")

    context = {"page_title": "Tests & Grading", "active_role": "TEACHER", "db_error": None}
    try:
        context.update(get_teacher_tests_context(user, course_filter=_param(request, "course", "ALL")))
    except Exception as exc:
        context["db_error"] = str(exc)
    return render(request, "panels/teacher_tests.html", context)


@role_required(["TEACHER", "ADMIN"])
def teacher_test_grade(request, test_id):
    user = request.session.get("user") or {}
    if request.method == "POST":
        action = _param(request, "action").lower()
        try:
            if action in ("", "grade_test", "grade_single_student"):
                post_data = request.POST.copy()
                post_data["test_id"] = test_id
                graded, err = grade_test_submissions(post_data, user)
                _flash(request, bool(graded) and not err, err, f"Graded {graded} student(s) and updated internal marks.")
            elif not _handle_common_post(request):
                messages.error(request, "Unknown action.")
        except Exception as exc:
            messages.error(request, f"Database error: {exc}")
        return redirect("panels:teacher_test_grade", test_id=test_id)

    context = {"page_title": "Grade Test", "active_role": "TEACHER", "db_error": None}
    try:
        context.update(get_teacher_test_grade_context(user, test_id))
    except Exception as exc:
        context["db_error"] = str(exc)
    return render(request, "panels/teacher_test_grade.html", context)
