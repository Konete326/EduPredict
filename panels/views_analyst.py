from django.shortcuts import render


def analyst_dashboard(request):
    return render(
        request,
        'base.html',
        {
            'page_title': 'Analyst Dashboard',
            'active_role': 'ANALYST',
        },
    )
