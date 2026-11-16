from django.contrib import messages
from django.shortcuts import redirect
from analytics.data_pipeline import ingest_dataset
from analytics.ml_engine import run_prediction_pipeline
from core.db import student_records_col
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
                messages.error(request, 'Please select a CSV or Excel (.xlsx) dataset file.')
                return redirect('panels:analyst_dashboard')
            ingest_result = ingest_dataset(
                file_obj=dataset_file,
                uploaded_by=uploaded_by,
                mode='upload',
            )

        if ingest_result.get('status') != 'COMPLETED':
            messages.error(
                request,
                ingest_result.get('error') or 'Dataset validation failed.',
            )
            return redirect('panels:analyst_dashboard')

        ml_result = run_prediction_pipeline()
        rows_processed = ingest_result.get('rows_processed', 0)
        fixed_count = ingest_result.get('missing_values_fixed', 0)
        preds_count = ml_result.get('predictions_generated', 0)
        messages.success(
            request,
            f'Ingested {rows_processed} records ({fixed_count} missing cells fixed) and generated {preds_count} ML predictions.',
        )
    except Exception as exc:
        messages.error(request, f'Dataset ingestion failed: {exc}')

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
        if ml_result.get('status') == 'EMPTY':
            messages.warning(request, 'No student records available for prediction.')
        else:
            preds_count = ml_result.get('predictions_generated', 0)
            high_count = ml_result.get('high_risk_count', 0)
            anomalies_count = ml_result.get('anomalies_count', 0)
            messages.success(
                request,
                f'ML pipeline updated {preds_count} predictions ({high_count} High Risk, {anomalies_count} Anomalies flagged).',
            )
    except Exception as exc:
        messages.error(request, f'ML prediction run failed: {exc}')

    return redirect('panels:analyst_dashboard')
