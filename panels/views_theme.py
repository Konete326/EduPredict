import json
from django.contrib import messages
from django.contrib.messages.api import MessageFailure
from django.http import JsonResponse
from django.shortcuts import redirect
from django.utils.http import url_has_allowed_host_and_scheme
from core.theme_services import get_user_theme_prefs, save_user_theme_prefs


def _parse_payload(request):
    content_type = str(request.content_type or request.META.get("CONTENT_TYPE") or "").strip().lower()
    is_json = content_type.startswith("application/json")
    if is_json:
        try:
            body = request.body.decode("utf-8") if request.body else "{}"
            parsed = json.loads(body or "{}")
            return (parsed if isinstance(parsed, dict) else {}), True
        except Exception:
            return {}, True
    return {key: request.POST.get(key) for key in request.POST}, False


def _flash_success(request, text):
    try:
        messages.success(request, text)
    except MessageFailure:
        pass


def theme_preferences_view(request):
    if request.method == "GET":
        return JsonResponse({"ok": True, "theme_prefs": get_user_theme_prefs(request)})
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "Method not allowed."}, status=405)

    payload, is_json = _parse_payload(request)
    prefs = save_user_theme_prefs(request, payload)
    x_req = str(request.headers.get("X-Requested-With") or request.META.get("HTTP_X_REQUESTED_WITH") or "").strip()
    if is_json or x_req == "EduPredict-Theme":
        return JsonResponse({"ok": True, "theme_prefs": prefs})

    action = str(payload.get("action") or "").strip().lower()
    _flash_success(request, "Theme settings reset to default." if action == "reset" else "Theme settings updated.")
    referer = request.META.get("HTTP_REFERER", "")
    next_url = referer if referer and url_has_allowed_host_and_scheme(referer, allowed_hosts={request.get_host()}) else "/"
    return redirect(next_url)
