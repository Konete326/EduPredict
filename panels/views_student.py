from django.shortcuts import render
from core.decorators import role_required


@role_required(['STUDENT'])
def student_dashboard(request):
    return render(
        request,
        'base.html',
        {
            'page_title': 'Student Dashboard',
            'active_role': 'STUDENT',
        },
    )


@role_required(['STUDENT'])
def student_report(request):
    return render(
        request,
        'base.html',
        {
            'page_title': 'Academic Report Card',
            'active_role': 'STUDENT',
        },
    )
