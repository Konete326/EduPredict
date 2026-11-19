from django.conf import settings


class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        csp = getattr(settings, "SECURE_CONTENT_SECURITY_POLICY", None)
        if csp and "Content-Security-Policy" not in response:
            response["Content-Security-Policy"] = csp
        permissions_policy = getattr(settings, "SECURE_PERMISSIONS_POLICY", None)
        if permissions_policy and "Permissions-Policy" not in response:
            response["Permissions-Policy"] = permissions_policy
        return response


def sentry_before_send(event, hint):
    if "exc_info" in hint:
        exc_type, _, _ = hint["exc_info"]
        exc_name = getattr(exc_type, "__name__", "")
        if "Mongo" in exc_name or "ServerSelection" in exc_name or "Network" in exc_name:
            tags = event.setdefault("tags", {})
            tags["infrastructure"] = "mongodb"
            tags["error_category"] = "database_connectivity"
    request_data = event.get("request")
    if isinstance(request_data, dict):
        query_string = request_data.get("query_string")
        if isinstance(query_string, str) and any(k in query_string.lower() for k in ("password", "token", "secret", "key")):
            request_data["query_string"] = "[FILTERED]"
        headers = request_data.get("headers")
        if isinstance(headers, dict):
            for h in ("Authorization", "Cookie", "Set-Cookie", "X-Csrftoken"):
                if h in headers:
                    headers[h] = "[FILTERED]"
    return event
