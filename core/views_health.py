import time
from django.http import JsonResponse
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
            "memory": {
                "status": "healthy",
                "cache_entries": len(_MEMORY_CACHE),
            },
        },
        status=200,
    )
