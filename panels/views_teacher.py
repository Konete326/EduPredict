from django.shortcuts import render
from core.db import get_collection, predictions_col, student_records_col, support_tickets_col
from core.decorators import role_required


def _teacher_live_metrics():
    metrics = {
        "records": 0,
        "high_risk": 0,
        "courses": 0,
        "tickets": 0,
        "db_error": None,
    }
    try:
        metrics["records"] = student_records_col().count_documents({})
        metrics["high_risk"] = predictions_col().count_documents({"risk_level": "HIGH"})
        metrics["courses"] = get_collection("courses").count_documents({"status": "ACTIVE"})
        metrics["tickets"] = support_tickets_col().count_documents({"status": "OPEN"})
    except Exception as exc:
        metrics["db_error"] = str(exc)
    return metrics


def _render_teacher_coming_soon(request, page_title, module_badge, module_description, module_icon, features):
    metrics = _teacher_live_metrics()
    live_cards = [
        {
            "title": "Tracked Student Records",
            "value": metrics["records"],
            "badge": "MongoDB Atlas live count",
            "status": "info",
            "icon": "fa-solid fa-user-graduate",
        },
        {
            "title": "High Dropout Alerts",
            "value": metrics["high_risk"],
            "badge": "Flagged for intervention",
            "status": "danger",
            "icon": "fa-solid fa-triangle-exclamation",
        },
        {
            "title": "Active Courses",
            "value": metrics["courses"],
            "badge": "Assigned catalog",
            "status": "success",
            "icon": "fa-solid fa-book-open",
        },
        {
            "title": "Open Support Tickets",
            "value": metrics["tickets"],
            "badge": "Helpdesk queue",
            "status": "warning",
            "icon": "fa-solid fa-life-ring",
        },
    ]
    return render(
        request,
        "panels/coming_soon_panel.html",
        {
            "page_title": page_title,
            "active_role": "TEACHER",
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


@role_required(["TEACHER"])
def teacher_dashboard(request):
    return _render_teacher_coming_soon(
        request,
        page_title="Teacher Command Center",
        module_badge="Faculty Panel · Coming Soon",
        module_description="Class-wide attendance monitoring, cohort GPA averages, and real-time early-warning intervention queues.",
        module_icon="fa-solid fa-chalkboard-user",
        features=[
            "Batch-level attendance heatmaps and weekly engagement trends",
            "One-click high-risk student intervention flags and advisor notes",
            "Automated midterm grade variance alerts synced with ML predictions",
            "Exportable cohort readiness briefs for department chairs",
        ],
    )


@role_required(["TEACHER"])
def teacher_students(request):
    return _render_teacher_coming_soon(
        request,
        page_title="Student Performance Tracker",
        module_badge="Faculty Panel · Coming Soon",
        module_description="Individual learner trajectory tracking, attendance threshold diagnostics, and personalized mentoring workflows.",
        module_icon="fa-solid fa-user-graduate",
        features=[
            "Searchable and paginated student risk roster across assigned courses",
            "Side-by-side previous GPA vs. ML predicted GPA breakdown",
            "Anomaly explanation badges from Isolation Forest diagnostics",
            "Direct faculty feedback notifications to at-risk students",
        ],
    )


@role_required(["TEACHER"])
def teacher_ingest(request):
    return _render_teacher_coming_soon(
        request,
        page_title="Class Data Ingestion",
        module_badge="Faculty Panel · Coming Soon",
        module_description="Streamlined CSV and Excel attendance, quiz, and assignment score uploads scoped directly to faculty sections.",
        module_icon="fa-solid fa-file-arrow-up",
        features=[
            "Course-scoped spreadsheet upload with instant schema validation",
            "Automated median and mode imputation preview before commit",
            "Automatic ML pipeline trigger after section grades are posted",
            "Upload audit log with fixed cell counters per submission",
        ],
    )
