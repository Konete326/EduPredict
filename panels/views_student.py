from django.contrib import messages
from django.shortcuts import redirect, render
from core.decorators import role_required
from panels.student_services import get_student_overview_context
from panels.student_test_services import get_student_attendance_context, get_student_tests_context, submit_student_test


def _student_identity(request):
    user = request.session.get("user") or {}
    role = str(user.get("role") or "STUDENT").strip().upper()
    student_id = str(user.get("student_id") or "").strip()
    user_id = str(user.get("user_id") or "").strip()
    if not student_id:
        student_id = user_id
    return student_id, user_id, role, user


def _empty_overview_context():
    return {
        "record": {
            "student_id": "", "full_name": "", "batch": "", "department": "", "program_level": "",
            "courses": [], "avg_attendance": 0.0, "avg_marks": 0.0, "avg_assignment": 0.0,
            "lms_hours_weekly": 0.0, "previous_gpa": 0.0, "predicted_gpa": None,
            "risk_level": "PENDING", "risk_score": None, "is_anomaly": False,
            "anomaly_reason": "", "recommendation": "", "generated_at": None,
        },
        "subject_rows": [],
        "chart": {"labels": [], "mine": [], "class_avg": []},
        "rank": None,
        "tips": [],
        "insight": {"summary": "Prediction data is unavailable right now.", "status": "info", "points": []},
        "unread_alerts": 0,
        "active_courses": 0,
        "credits": 0.0,
        "teacher_alerts": [],
        "enrolled_courses": [],
        "admin_contact": {"name": "", "email": ""},
        "assigned_teacher": {"teacher_id": "", "name": "", "email": ""},
        "alerts": [],
        "my_tickets": [],
        "unread": 0,
        "total": 0,
    }


def _safe_context(loader, *args):
    try:
        return loader(*args), None
    except Exception as exc:
        return _empty_overview_context(), str(exc)


def _risk_status(risk_level):
    risk = str(risk_level or "").upper()
    return {"HIGH": "danger", "MEDIUM": "warning", "PENDING": "info"}.get(risk, "success")


def _build_subject_table_rows(subject_rows):
    headers = ["Course", "My Marks", "Class Avg", "My Attendance", "Class Att", "Status"]
    rows = [[s["course_code"], f"{s['my_marks']:.1f}", f"{s['class_marks']:.1f}", f"{s['my_attendance']:.1f}%", f"{s['class_attendance']:.1f}%", s["status"]] for s in subject_rows]
    return headers, rows


@role_required(["STUDENT", "ADMIN"])
def student_dashboard(request):
    student_id, user_id, role, user = _student_identity(request)
    data, db_error = _safe_context(get_student_overview_context, student_id, user_id, role)
    record = data["record"]
    subject_headers, subject_table_rows = _build_subject_table_rows(data["subject_rows"])
    predicted_gpa_display = f"{record['predicted_gpa']:.2f}" if record["predicted_gpa"] is not None else "Pending"
    rank = data["rank"]
    return render(request, "panels/student_dashboard.html", {
        "page_title": "Dashboard",
        "active_role": "STUDENT",
        "record": record,
        "risk_status": _risk_status(record["risk_level"]),
        "insight": data["insight"],
        "tips": data["tips"],
        "subject_headers": subject_headers,
        "subject_table_rows": subject_table_rows,
        "chart_data": data["chart"],
        "rank": rank,
        "unread_alerts": data["unread_alerts"],
        "credits": data["credits"],
        "credits_display": f"{data['credits']:.1f}",
        "predicted_gpa_display": predicted_gpa_display,
        "class_standing_display": f"#{rank['rank']} of {rank['total']}" if rank else "N/A",
        "teacher_alerts": data["teacher_alerts"],
        "enrolled_courses": data.get("enrolled_courses", []),
        "admin_contact": data.get("admin_contact", {}),
        "assigned_teacher": data.get("assigned_teacher", {}),
        "db_error": db_error,
    })


@role_required(["STUDENT", "ADMIN"])
def student_tests(request):
    student_id, user_id, role, user = _student_identity(request)
    if request.method == "POST":
        action = str(request.POST.get("action") or "").strip().lower()
        if action == "submit_test":
            test_id = str(request.POST.get("test_id") or "").strip()
            note = str(request.POST.get("submission_note") or request.POST.get("note") or "").strip()
            files = request.FILES.getlist("files")
            sub, err = submit_student_test(test_id, student_id, user_id, note=note, files=files)
            if err or not sub:
                messages.error(request, err or "Submission failed.")
            else:
                messages.success(request, f"Work submitted ({sub.get('submission_status', 'SUBMITTED')}).")
        else:
            messages.error(request, "Unknown action.")
        return redirect("panels:student_tests")

    ctx = {"tests": [], "kpis": {"total": 0, "pending": 0, "submitted": 0, "late": 0, "graded": 0}, "semester_id": "", "semester_label": "-", "courses": [], "today_str": ""}
    db_error = None
    try:
        ctx = get_student_tests_context(student_id, user_id, role)
    except Exception as exc:
        db_error = str(exc)
    return render(request, "panels/student_tests.html", {
        "page_title": "My Tests",
        "active_role": "STUDENT",
        **ctx,
        "db_error": db_error,
    })


@role_required(["STUDENT", "ADMIN"])
def student_attendance(request):
    student_id, user_id, role, user = _student_identity(request)
    course_filter = str(request.GET.get("course") or "ALL").strip().upper() or "ALL"
    ctx = {"semester_label": "-", "courses": [], "course_filter": course_filter, "course_cards": [], "attendance_headers": ["Date", "Course", "Status", "Teacher"], "attendance_rows": [], "attendance_cards": [], "kpis": {"attendance_pct": 0.0, "total_days": 0, "present_days": 0, "absent_days": 0, "leave_days": 0}}
    db_error = None
    try:
        ctx = get_student_attendance_context(student_id, user_id, role, course_filter=course_filter)
    except Exception as exc:
        db_error = str(exc)
    return render(request, "panels/student_attendance.html", {
        "page_title": "My Attendance",
        "active_role": "STUDENT",
        **ctx,
        "db_error": db_error,
    })
