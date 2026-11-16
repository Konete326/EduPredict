from django.shortcuts import render
from core.decorators import role_required


@role_required(['TEACHER'])
def teacher_dashboard(request):
    return render(
        request,
        'base.html',
        {
            'page_title': 'Teacher Dashboard',
            'active_role': 'TEACHER',
        },
    )


@role_required(['TEACHER'])
def teacher_students(request):
    return render(
        request,
        'base.html',
        {
            'page_title': 'Student Performance Tracker',
            'active_role': 'TEACHER',
        },
    )


@role_required(['TEACHER'])
def teacher_ingest(request):
    return render(
        request,
        'base.html',
        {
            'page_title': 'Class Data Ingestion',
            'active_role': 'TEACHER',
        },
    )
