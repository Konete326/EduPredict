from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect
from analytics.data_pipeline import ingest_dataset
from analytics.evaluation import DEFAULT_TEST_SIZE
from analytics.ml_engine import evaluate_models, run_prediction_pipeline
from analytics.preprocessing import DEFAULT_RANDOM_STATE, validate_eval_params
from core.db import get_cached, invalidate_cache, student_records_col
from core.decorators import role_required


def _get_actor_label(request):
    user = request.session.get('user') or {}
    return user.get('email') or user.get('full_name') or 'Analyst'


@role_required(['ANALYST', 'ADMIN'])
def upload_dataset(request):
    if request.method != 'POST':
        return redirect('panels:analyst_dashboard')

    mode = str(request.POST.get('mode', 'upload')).strip().lower()
    uploaded_by = _get_actor_label(request)

    try:
        if mode == 'sample':
            ingest_result = ingest_dataset(mode='sample', uploaded_by=uploaded_by)
        else:
            dataset_file = request.FILES.get('dataset_file')
            if not dataset_file:
                messages.error(request, 'Please choose a CSV or Excel (.xlsx) file.')
                return redirect('panels:analyst_dashboard')
            ingest_result = ingest_dataset(
                file_obj=dataset_file,
                uploaded_by=uploaded_by,
                mode='upload',
            )

        if ingest_result.get('status') != 'COMPLETED':
            invalidate_cache()
            messages.error(
                request,
                ingest_result.get('error') or 'Could not read this file. Please check the columns.',
            )
            return redirect('panels:analyst_dashboard')

        ml_result = run_prediction_pipeline()
        invalidate_cache()
        rows_processed = ingest_result.get('rows_processed', 0)
        fixed_count = ingest_result.get('missing_values_fixed', 0)
        preds_count = ml_result.get('predictions_generated', 0)
        messages.success(
            request,
            f'Loaded {rows_processed} rows ({fixed_count} blank cells fixed) and updated {preds_count} predictions.',
        )
    except Exception as exc:
        invalidate_cache()
        messages.error(request, f'File upload failed: {exc}')

    return redirect('panels:analyst_dashboard')


@role_required(['ANALYST', 'ADMIN'])
def run_predictions(request):
    if request.method != 'POST':
        return redirect('panels:analyst_dashboard')

    uploaded_by = _get_actor_label(request)
    try:
        if student_records_col().count_documents({}) == 0:
            ingest_dataset(mode='sample', uploaded_by=uploaded_by)

        ml_result = run_prediction_pipeline()
        invalidate_cache()
        if ml_result.get('status') == 'EMPTY':
            messages.warning(request, 'No student data found. Please upload a file first.')
        else:
            preds_count = ml_result.get('predictions_generated', 0)
            high_count = ml_result.get('high_risk_count', 0)
            anomalies_count = ml_result.get('anomalies_count', 0)
            messages.success(
                request,
                f'Updated {preds_count} predictions ({high_count} high risk, {anomalies_count} unusual).',
            )
    except Exception as exc:
        invalidate_cache()
        messages.error(request, f'Could not run predictions: {exc}')

    return redirect('panels:analyst_dashboard')


def _is_truthy(value):
    return str(value or '').strip().lower() in ('1', 'true', 'yes', 'on')


@role_required(['ANALYST', 'ADMIN'])
def model_evaluation(request):
    try:
        raw_test_size = request.GET.get('test_size')
        raw_random_state = request.GET.get('random_state')
        test_size_val = DEFAULT_TEST_SIZE if raw_test_size in (None, '') else raw_test_size
        random_state_val = DEFAULT_RANDOM_STATE if raw_random_state in (None, '') else raw_random_state
        ts, rs = validate_eval_params(test_size_val, random_state_val)
        refresh = _is_truthy(request.GET.get('refresh'))
        if ts == DEFAULT_TEST_SIZE and rs == DEFAULT_RANDOM_STATE:
            if refresh:
                invalidate_cache('analyst:')
            report = get_cached(
                'analyst:evaluation:default',
                lambda: evaluate_models(test_size=ts, random_state=rs),
                ttl=45.0,
            )
        else:
            report = evaluate_models(test_size=ts, random_state=rs)
        return JsonResponse(report, status=200)
    except ValueError as exc:
        return JsonResponse({'status': 'ERROR', 'error': str(exc)}, status=400)
    except Exception as exc:
        return JsonResponse({'status': 'ERROR', 'error': f'Evaluation failed: {exc}'}, status=500)
