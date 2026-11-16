from django.shortcuts import render
from core.decorators import role_required


@role_required(['ADMIN'])
def admin_dashboard(request):
    return render(
        request,
        'base.html',
        {
            'page_title': 'Admin Dashboard',
            'active_role': 'ADMIN',
        },
    )


@role_required(['ADMIN'])
def admin_users(request):
    return render(
        request,
        'base.html',
        {
            'page_title': 'User Management',
            'active_role': 'ADMIN',
        },
    )


@role_required(['ADMIN'])
def admin_courses(request):
    return render(
        request,
        'base.html',
        {
            'page_title': 'Courses & Batches',
            'active_role': 'ADMIN',
        },
    )


@role_required(['ADMIN'])
def admin_tickets(request):
    return render(
        request,
        'base.html',
        {
            'page_title': 'Support Tickets',
            'active_role': 'ADMIN',
        },
    )
