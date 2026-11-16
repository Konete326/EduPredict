from django.shortcuts import render


def teacher_dashboard(request):
    return render(
        request,
        'base.html',
        {
            'page_title': 'Teacher Dashboard',
            'active_role': 'TEACHER',
        },
    )


def teacher_students(request):
    return render(
        request,
        'base.html',
        {
            'page_title': 'Student Performance Tracker',
            'active_role': 'TEACHER',
        },
    )


def teacher_ingest(request):
    return render(
        request,
        'base.html',
        {
            'page_title': 'Class Data Ingestion',
            'active_role': 'TEACHER',
        },
    )
