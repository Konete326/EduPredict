from django.shortcuts import redirect, render

ROLE_DASHBOARDS = {
    'ADMIN': 'panels:admin_dashboard',
    'TEACHER': 'panels:teacher_dashboard',
    'STUDENT': 'panels:student_dashboard',
    'ANALYST': 'panels:analyst_dashboard',
}


def root_redirect(request):
    user = request.session.get('user')
    if isinstance(user, dict):
        role = str(user.get('role', '')).upper()
        target = ROLE_DASHBOARDS.get(role)
        if target:
            return redirect(target)
    return redirect('accounts:auth_view')


def auth_view(request):
    return render(
        request,
        'base.html',
        {
            'page_title': 'Sign In & Registration',
            'active_role': None,
        },
    )


def logout_view(request):
    request.session.flush()
    return redirect('accounts:auth_view')
