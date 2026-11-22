from django.contrib import messages
from django.contrib.messages.api import MessageFailure
from django.http import JsonResponse
from django.shortcuts import redirect, render
from core.decorators import login_required_custom, role_required
from panels.admin_services import mark_notifications_read
from panels.notification_services import (
    get_live_notifications_feed,
    list_notifications_history,
    mark_single_notification_read,
)
from panels.phase62_services import get_student_360_summary


def _flash(level_fn, request, text):
    try:
        level_fn(request, text)
    except MessageFailure:
        pass


@login_required_custom
def notifications_feed_view(request):
    if request.method != "GET":
        return JsonResponse({"ok": False, "error": "Method not allowed."}, status=405)
    user = request.session.get("user") or {}
    try:
        items, count = get_live_notifications_feed(user)
        return JsonResponse({"ok": True, "unread_count": count, "notifications": items})
    except Exception as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=500)


@login_required_custom
def notifications_history_view(request):
    user = request.session.get("user") or {}
    if request.method == "POST":
        action = str(request.POST.get("action") or "mark_all").strip().lower()
        try:
            if action == "mark_one":
                ok = mark_single_notification_read(request.POST.get("notification_id"), user)
                _flash(
                    messages.success if ok else messages.error,
                    request,
                    "Alert marked as read." if ok else "Could not mark alert as read.",
                )
            else:
                mark_notifications_read(user)
                _flash(messages.success, request, "All alerts marked as read.")
        except Exception as exc:
            _flash(messages.error, request, f"Alert update failed: {exc}")
        return redirect("panels:notifications_history")

    active_tab = str(request.GET.get("tab") or "ALL").strip().upper()
    if active_tab not in ("ALL", "UNREAD", "READ", "REPLIES"):
        active_tab = "ALL"
    items, counts, err = list_notifications_history(user, active_tab)
    return render(
        request,
        "panels/notifications_history.html",
        {
            "page_title": "Notifications & Alert History",
            "notifications_items": items,
            "tab_counts": counts,
            "active_tab": active_tab,
            "db_error": err,
        },
    )


@role_required(["TEACHER", "ANALYST", "ADMIN"])
def student_360_summary_view(request, student_id):
    if request.method != "GET":
        return JsonResponse({"ok": False, "error": "Method not allowed."}, status=405)
    try:
        summary = get_student_360_summary(student_id)
    except Exception as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=500)
    if summary is None:
        return JsonResponse({"ok": False, "error": "Student record not found."}, status=404)
    return JsonResponse({"ok": True, "summary": summary})
