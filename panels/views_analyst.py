from django.shortcuts import render
from core.decorators import role_required


@role_required(['ANALYST'])
def analyst_dashboard(request):
    return render(
        request,
        'base.html',
        {
            'page_title': 'Analyst Dashboard',
            'active_role': 'ANALYST',
        },
    )
