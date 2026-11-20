from django.http import JsonResponse
from core.decorators import login_required_custom
from panels.notification_services import get_live_notifications_feed


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
