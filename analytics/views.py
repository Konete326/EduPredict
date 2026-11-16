from django.shortcuts import render
from core.decorators import role_required


@role_required(['ANALYST'])
def upload_dataset(request):
    return render(
        request,
        'base.html',
        {
            'page_title': 'Upload Dataset',
            'active_role': 'ANALYST',
        },
    )


@role_required(['ANALYST'])
def run_predictions(request):
    return render(
        request,
        'base.html',
        {
            'page_title': 'Run ML Predictions',
            'active_role': 'ANALYST',
        },
    )
