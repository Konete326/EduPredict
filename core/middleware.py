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
