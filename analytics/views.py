from django.shortcuts import render


def upload_dataset(request):
    return render(
        request,
        'base.html',
        {
            'page_title': 'Upload Dataset',
            'active_role': 'ANALYST',
        },
    )


def run_predictions(request):
    return render(
        request,
        'base.html',
        {
            'page_title': 'Run ML Predictions',
            'active_role': 'ANALYST',
        },
    )
