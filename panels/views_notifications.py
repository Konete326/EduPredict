from django.http import JsonResponse
from core.decorators import login_required_custom, role_required
from panels.notification_services import get_live_notifications_feed
from panels.phase62_services import get_student_360_summary


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
