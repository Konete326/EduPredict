from django.shortcuts import render
from core.db import get_cached, get_collection, predictions_col, student_records_col
from core.decorators import role_required


def _load_student_shared_counts():
    return {
        "courses": get_collection("courses").count_documents({"status": "ACTIVE"}),
        "records_total": student_records_col().count_documents({}),
    }


def _load_student_personal_metrics(student_id):
    data = {
        "attendance": "N/A",
        "predicted_gpa": "Pending",
        "risk_level": "Pending",
    }
    rec = student_records_col().find_one({"student_id": student_id}, {"_id": 0})
    if rec and rec.get("attendance_pct") is not None:
        data["attendance"] = f"{float(rec['attendance_pct']):.1f}%"
    pred = predictions_col().find_one({"student_id": student_id}, {"_id": 0})
    if pred:
        if pred.get("predicted_gpa") is not None:
            data["predicted_gpa"] = f"{float(pred['predicted_gpa']):.2f}"
        data["risk_level"] = str(pred.get("risk_level") or "PENDING").upper()
    return data


def _student_live_metrics(request):
    user = request.session.get("user") or {}
    student_id = str(user.get("student_id") or "").strip()
    metrics = {
        "attendance": "N/A",
        "predicted_gpa": "Pending",
        "risk_level": "Pending",
        "courses": 0,
        "records_total": 0,
        "db_error": None,
    }
    try:
        shared = get_cached("soon:STUDENT", _load_student_shared_counts, ttl=45.0)
        metrics["courses"] = shared["courses"]
        metrics["records_total"] = shared["records_total"]
        if student_id:
            personal = get_cached(
                f"soon:STUDENT:{student_id}",
                lambda: _load_student_personal_metrics(student_id),
                ttl=45.0,
            )
            metrics.update(personal)
    except Exception as exc:
        metrics["db_error"] = str(exc)
    return metrics


def _render_student_coming_soon(request, page_title, module_badge, module_description, module_icon, features):
    user = request.session.get("user") or {}
    active_role = str(user.get("role") or "STUDENT").strip().upper()
    metrics = _student_live_metrics(request)
    risk_status = "danger" if metrics["risk_level"] == "HIGH" else ("warning" if metrics["risk_level"] == "MEDIUM" else "success")
    live_cards = [
        {
            "title": "Your Attendance",
            "value": metrics["attendance"],
            "badge": "From your profile",
            "status": "info",
            "icon": "fa-solid fa-calendar-check",
        },
        {
            "title": "Predicted GPA",
            "value": metrics["predicted_gpa"],
            "badge": "Expected score",
            "status": "success",
            "icon": "fa-solid fa-chart-line",
        },
        {
            "title": "Risk Level",
            "value": metrics["risk_level"],
            "badge": "Current status",
            "status": risk_status,
            "icon": "fa-solid fa-shield-halved",
        },
        {
            "title": "Active Courses",
            "value": metrics["courses"],
            "badge": f"{metrics['records_total']} total students",
            "status": "info",
            "icon": "fa-solid fa-book-open",
        },
    ]
    return render(
        request,
        "panels/coming_soon_panel.html",
        {
            "page_title": page_title,
            "active_role": active_role,
            "module_badge": module_badge,
            "module_title": page_title,
            "module_description": module_description,
            "module_icon": module_icon,
            "roadmap_features": features,
            "features_pipe": "|".join(features),
            "live_cards": live_cards,
            "db_error": metrics["db_error"],
        },
    )


@role_required(["STUDENT", "ADMIN"])
def student_dashboard(request):
    return _render_student_coming_soon(
        request,
        page_title="My Dashboard",
        module_badge="Student · Soon",
        module_description="Track your attendance, weekly study hours, and helpful tips for your classes.",
        module_icon="fa-solid fa-graduation-cap",
        features=[
            "See your attendance and target GPA side by side",
            "Get weekly study hour tips for your courses",
            "Check marks for each assignment and test",
            "Message your teacher or ask for help anytime",
        ],
    )


@role_required(["STUDENT", "ADMIN"])
def student_report(request):
    return _render_student_coming_soon(
        request,
        page_title="My Result",
        module_badge="Student · Soon",
        module_description="View your predicted semester GPA, past grades, and printable result summary.",
        module_icon="fa-solid fa-file-lines",
        features=[
            "Compare past GPA and expected GPA by term",
            "See course credits and teacher notes",
            "Follow simple tips to keep your grades up",
            "Download or print your result summary",
        ],
    )
