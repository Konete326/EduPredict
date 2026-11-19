import os
import sys
import time
from django.http import HttpResponse, JsonResponse
from core.decorators import rate_limit
from core.db import (
    _MEMORY_CACHE,
    courses_col,
    get_client,
    notifications_col,
    predictions_col,
    student_records_col,
    support_tickets_col,
    users_col,
)


def _get_process_memory_mb():
    try:
        if sys.platform == "win32":
            import ctypes
            from ctypes import wintypes
            class PROCESS_MEMORY_COUNTERS_EX(ctypes.Structure):
                _fields_ = [
                    ("cb", wintypes.DWORD),
                    ("PageFaultCount", wintypes.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t),
                    ("PrivateUsage", ctypes.c_size_t),
                ]
            counters = PROCESS_MEMORY_COUNTERS_EX()
            counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS_EX)
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            psapi = ctypes.WinDLL("psapi", use_last_error=True)
            psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESS_MEMORY_COUNTERS_EX), wintypes.DWORD]
            psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
            if psapi.GetProcessMemoryInfo(kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
                return round(counters.WorkingSetSize / (1024 * 1024), 2)
        else:
            if os.path.exists("/proc/self/status"):
                with open("/proc/self/status", "r", encoding="utf-8") as f:
                    for line in f:
                        if line.startswith("VmRSS:"):
                            parts = line.split()
                            if len(parts) >= 2:
                                return round(float(parts[1]) / 1024, 2)
            import resource
            usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            if sys.platform == "darwin":
                return round(usage / (1024 * 1024), 2)
            return round(usage / 1024, 2)
    except Exception:
        return None
    return None


def _build_memory_payload():
    payload = {
        "status": "healthy",
        "cache_entries": len(_MEMORY_CACHE),
    }
    rss_mb = _get_process_memory_mb()
    if rss_mb is not None:
        payload["rss_mb"] = rss_mb
    return payload


@rate_limit(max_requests=120, window_seconds=60)
def health_check(request):
    started_at = time.monotonic()
    client = get_client()
    if client is None:
        return JsonResponse(
            {
                "status": "unhealthy",
                "database": "disconnected",
                "error": "MongoDB client unavailable",
                "cache": {
                    "entries": len(_MEMORY_CACHE),
                    "status": "active",
                },
                "memory": _build_memory_payload(),
            },
            status=503,
        )

    try:
        client.admin.command("ping")
        latency_ms = round((time.monotonic() - started_at) * 1000, 2)
    except Exception as exc:
        return JsonResponse(
            {
                "status": "unhealthy",
                "database": "disconnected",
                "error": str(exc),
                "cache": {
                    "entries": len(_MEMORY_CACHE),
                    "status": "active",
                },
                "memory": _build_memory_payload(),
            },
            status=503,
        )

    counts = {}
    collectors = [
        ("users", users_col),
        ("student_records", student_records_col),
        ("predictions", predictions_col),
        ("courses", courses_col),
        ("notifications", notifications_col),
        ("support_tickets", support_tickets_col),
    ]

    for name, getter in collectors:
        try:
            col = getter()
            counts[name] = col.count_documents({})
        except Exception:
            counts[name] = 0

    return JsonResponse(
        {
            "status": "healthy",
            "database": "connected",
            "latency_ms": latency_ms,
            "counts": counts,
            "collections": counts,
            "cache": {
                "entries": len(_MEMORY_CACHE),
                "status": "active",
            },
            "memory": _build_memory_payload(),
        },
        status=200,
    )


def robots_txt(request):
    lines = [
        "User-agent: *",
        "Disallow: /admin/",
        "Disallow: /admin-panel/",
        "Disallow: /teacher-panel/",
        "Disallow: /student-panel/",
        "Disallow: /analyst-panel/",
        "Allow: /auth/",
        "Allow: /health/",
        "Allow: /$",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain; charset=utf-8")


def favicon_view(request):
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'
        '<rect width="32" height="32" rx="8" fill="#2563eb"/>'
        '<path d="M16 7L6 12l10 5 10-5-10-5zM8 16.5l8 4 8-4M10 20l6 3 6-3" '
        'fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'
        '</svg>'
    )
    return HttpResponse(svg, content_type="image/svg+xml")
