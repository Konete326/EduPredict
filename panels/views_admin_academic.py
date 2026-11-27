from django.contrib import messages
from django.shortcuts import redirect, render
from core.decorators import role_required
from panels.admin_academic_services import (
    create_class_record,
    create_course_record,
    create_semester_record,
    create_student_record,
    create_teacher_record,
    delete_class_record,
    delete_course_record,
    delete_semester_record,
    delete_student_record,
    delete_teacher_record,
    get_admin_classes_context,
    get_admin_courses_context,
    get_admin_students_context,
    get_admin_teachers_context,
    update_class_record,
    update_course_record,
    update_semester_record,
    update_student_record,
    update_teacher_record,
)


def _param(request, key, default=""):
    return str(request.POST.get(key) or request.GET.get(key) or default).strip()


def _actor_name(request):
    user = request.session.get("user") or {}
    return str(user.get("full_name") or user.get("email") or "System Admin").strip() or "System Admin"


def _flash_result(request, ok, error, success_msg):
    messages.error(request, error or "Operation could not be completed.") if (error or not ok) else messages.success(request, success_msg)


def _render_academic(request, template_name, page_title, context_fn, fallback):
    context = {"page_title": page_title, "active_role": "ADMIN", "db_error": None, **fallback}
    try:
        context.update(context_fn())
    except Exception as exc:
        context["db_error"] = str(exc)
    return render(request, template_name, context)


@role_required(["ADMIN"])
def admin_teachers(request):
    if request.method == "POST":
        action, user_id, actor = _param(request, "action").lower(), _param(request, "user_id"), _actor_name(request)
        full_name = request.POST.get("full_name") or request.POST.get("name")
        is_active = request.POST.get("is_active") if "is_active" in request.POST else request.POST.get("status", "true")
        department = request.POST.get("department") or "General"
        try:
            if action == "create_teacher":
                doc, err = create_teacher_record(full_name, request.POST.get("email"), request.POST.get("password"), request.POST.get("phone") or "", is_active, department, actor_name=actor)
                _flash_result(request, doc is not None, err, f"Teacher {doc['full_name']} added." if doc else "")
            elif action == "edit_teacher":
                ok, err = update_teacher_record(user_id, full_name, request.POST.get("email"), request.POST.get("phone") or "", is_active, request.POST.get("password") or "", department, actor_name=actor)
                _flash_result(request, ok, err, f"Teacher {user_id} updated.")
            elif action == "delete_teacher":
                ok, err = delete_teacher_record(user_id, actor_name=actor)
                _flash_result(request, ok, err, f"Teacher {user_id} deleted.")
            else:
                messages.error(request, "Unknown teacher action.")
        except Exception as exc:
            messages.error(request, f"Teacher error: {exc}")
        return redirect("panels:admin_teachers")
    return _render_academic(request, "panels/admin_teachers.html", "Teachers", get_admin_teachers_context, {"teachers": [], "teacher_headers": [], "teacher_rows": [], "teacher_cards": [], "total_teachers": 0, "active_teachers": 0, "inactive_teachers": 0})


@role_required(["ADMIN"])
def admin_students(request):
    if request.method == "POST":
        action, user_id, actor = _param(request, "action").lower(), _param(request, "user_id"), _actor_name(request)
        full_name = request.POST.get("full_name") or request.POST.get("name")
        try:
            if action == "create_student":
                doc, err = create_student_record(full_name, request.POST.get("email"), request.POST.get("password"), request.POST.get("class_id") or "", request.POST.get("semester_id") or "", request.POST.get("phone") or "", request.POST.get("department") or "General", actor_name=actor)
                _flash_result(request, doc is not None, err, f"Student {doc['full_name']} added." if doc else "")
            elif action == "edit_student":
                ok, err = update_student_record(user_id, full_name, request.POST.get("email"), request.POST.get("class_id") or "", request.POST.get("semester_id") or "", request.POST.get("phone") or "", request.POST.get("password") or "", actor_name=actor)
                _flash_result(request, ok, err, f"Student {user_id} updated.")
            elif action == "delete_student":
                ok, err = delete_student_record(user_id, actor_name=actor)
                _flash_result(request, ok, err, f"Student {user_id} deleted.")
            else:
                messages.error(request, "Unknown student action.")
        except Exception as exc:
            messages.error(request, f"Student error: {exc}")
        return redirect("panels:admin_students")
    return _render_academic(request, "panels/admin_students.html", "Students", get_admin_students_context, {"students": [], "student_headers": [], "student_rows": [], "student_cards": [], "class_options": [], "semester_options": [], "semester_options_json": "[]", "total_students": 0, "assigned_students": 0})


@role_required(["ADMIN"])
def admin_classes(request):
    if request.method == "POST":
        action, actor = _param(request, "action").lower(), _actor_name(request)
        class_id, semester_id = _param(request, "class_id"), _param(request, "semester_id")
        try:
            if action == "create_class":
                doc, err = create_class_record(request.POST.get("class_code"), request.POST.get("class_name"), request.POST.get("total_semesters") or 8, request.POST.get("status") or "ACTIVE", actor_name=actor)
                _flash_result(request, doc is not None, err, f"Class {doc['class_code']} created." if doc else "")
            elif action == "edit_class":
                ok, err = update_class_record(class_id, request.POST.get("class_code"), request.POST.get("class_name"), request.POST.get("total_semesters"), request.POST.get("status") or "ACTIVE", actor_name=actor)
                _flash_result(request, ok, err, f"Class {class_id} updated.")
            elif action == "delete_class":
                ok, err = delete_class_record(class_id, actor_name=actor)
                _flash_result(request, ok, err, f"Class {class_id} deleted.")
            elif action == "create_semester":
                doc, err = create_semester_record(class_id, request.POST.get("semester_number") or 1, request.POST.get("semester_name") or "", request.POST.get("status") or "ACTIVE", actor_name=actor)
                _flash_result(request, doc is not None, err, f"Semester {doc['semester_name']} created." if doc else "")
            elif action == "edit_semester":
                ok, err = update_semester_record(semester_id, class_id, request.POST.get("semester_number") or 1, request.POST.get("semester_name") or "", request.POST.get("status") or "ACTIVE", actor_name=actor)
                _flash_result(request, ok, err, f"Semester {semester_id} updated.")
            elif action == "delete_semester":
                ok, err = delete_semester_record(semester_id, actor_name=actor)
                _flash_result(request, ok, err, f"Semester {semester_id} deleted.")
            else:
                messages.error(request, "Unknown class/semester action.")
        except Exception as exc:
            messages.error(request, f"Class/Semester error: {exc}")
        return redirect("panels:admin_classes")
    return _render_academic(request, "panels/admin_classes.html", "Classes & Semesters", get_admin_classes_context, {"classes": [], "semesters": [], "class_headers": [], "class_rows": [], "class_cards": [], "semester_headers": [], "semester_rows": [], "semester_cards": [], "class_options": [], "total_classes": 0, "total_semesters_count": 0})


@role_required(["ADMIN"])
def admin_courses(request):
    if request.method == "POST":
        action, actor = _param(request, "action").lower(), _actor_name(request)
        code = _param(request, "course_code")
        try:
            if action == "create_course":
                doc, err = create_course_record(code, request.POST.get("title"), request.POST.get("class_id") or "", request.POST.get("semester_id") or "", request.POST.get("instructor_id") or "", request.POST.get("credits") or 3, request.POST.get("status") or "ACTIVE", actor_name=actor)
                _flash_result(request, doc is not None, err, f"Course {doc['course_code']} created." if doc else "")
            elif action == "edit_course":
                ok, err = update_course_record(code, request.POST.get("title"), request.POST.get("class_id") or "", request.POST.get("semester_id") or "", request.POST.get("instructor_id") or "", request.POST.get("credits") or 3, request.POST.get("status") or "ACTIVE", original_course_code=_param(request, "original_course_code"), actor_name=actor)
                _flash_result(request, ok, err, f"Course {code} updated.")
            elif action == "delete_course":
                ok, err = delete_course_record(code, actor_name=actor)
                _flash_result(request, ok, err, f"Course {code} deleted.")
            else:
                messages.error(request, "Unknown course action.")
        except Exception as exc:
            messages.error(request, f"Course error: {exc}")
        return redirect("panels:admin_courses")
    return _render_academic(request, "panels/admin_courses.html", "Courses", get_admin_courses_context, {"courses": [], "course_headers": [], "course_rows": [], "course_cards": [], "class_options": [], "semester_options": [], "semester_options_json": "[]", "teacher_options": [], "total_courses": 0, "active_courses": 0})
