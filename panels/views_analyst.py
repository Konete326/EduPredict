import csv
import pandas as pd
from django.http import HttpResponse
from django.shortcuts import render
from pymongo import DESCENDING
from analytics.data_pipeline import REQUIRED_COLUMNS
from analytics.ml_engine import _resolve_runtime_settings, compute_course_demand, evaluate_models
from analytics.model_health import get_analyst_accuracy_page_context
from core.db import datasets_log_col, get_cached, predictions_col, student_records_col
from core.decorators import role_required


def _safe_float(val, default=0.0):
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _load_analyst_snapshot():
    records = list(student_records_col().find({}, {'_id': 0}))
    pred_map = {}
    for pred in predictions_col().find({}, {'_id': 0}):
        sid = str(pred.get('student_id', '')).strip()
        if sid:
            pred_map[sid] = pred
    logs = list(datasets_log_col().find({}, {'_id': 0}).sort('uploaded_at', DESCENDING).limit(6))
    evaluation = None
    evaluation_error = None
    try:
        evaluation = get_cached(
            'analyst:evaluation:default',
            lambda: evaluate_models(records=records),
            ttl=45.0,
        )
    except Exception as exc:
        evaluation_error = str(exc)
    return records, pred_map, logs, evaluation, evaluation_error


def _build_joined_records(records, pred_map):
    joined = []
    for rec in records:
        sid = str(rec.get('student_id', '')).strip()
        if not sid:
            continue
        pred = pred_map.get(sid) or {}
        risk_level = str(pred.get('risk_level') or 'PENDING').strip().upper()
        raw_score = pred.get('dropout_risk_score')
        raw_pred_gpa = pred.get('predicted_gpa')
        joined.append({
            'student_id': sid,
            'full_name': str(rec.get('full_name') or sid),
            'batch': str(rec.get('batch') or 'Unassigned'),
            'course_code': str(rec.get('course_code') or 'GENERAL'),
            'attendance_pct': _safe_float(rec.get('attendance_pct'), 0.0),
            'internal_marks': _safe_float(rec.get('internal_marks'), 0.0),
            'assignment_score': _safe_float(rec.get('assignment_score'), 0.0),
            'lms_hours_weekly': _safe_float(rec.get('lms_hours_weekly'), 0.0),
            'previous_gpa': _safe_float(rec.get('previous_gpa'), 0.0),
            'predicted_gpa': _safe_float(raw_pred_gpa) if raw_pred_gpa is not None else None,
            'dropout_risk_score': _safe_float(raw_score) if raw_score is not None else None,
            'risk_level': risk_level,
            'is_anomaly': bool(pred.get('is_anomaly', False)),
            'anomaly_reason': str(pred.get('anomaly_reason') or ''),
            'recommendation': str(pred.get('recommendation') or 'Run prediction to get tips.'),
            'raw_record': rec,
        })
    return joined


def _apply_filters(joined, batch, course_code, risk_level):
    filtered = []
    for item in joined:
        if batch != 'ALL' and item['batch'] != batch:
            continue
        if course_code != 'ALL' and item['course_code'] != course_code:
            continue
        if risk_level == 'ANOMALY' and not item['is_anomaly']:
            continue
        if risk_level in ('HIGH', 'MEDIUM', 'LOW') and item['risk_level'] != risk_level:
            continue
        filtered.append(item)
    return filtered


def _export_csv_response(rows):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="edupredict_predictions.csv"'
    writer = csv.writer(response)
    writer.writerow([
        'student_id', 'full_name', 'batch', 'course_code', 'attendance_pct',
        'internal_marks', 'assignment_score', 'lms_hours_weekly', 'previous_gpa',
        'predicted_gpa', 'dropout_risk_score', 'risk_level', 'is_anomaly',
        'anomaly_reason', 'recommendation',
    ])
    for r in rows:
        writer.writerow([
            r['student_id'], r['full_name'], r['batch'], r['course_code'],
            f"{r['attendance_pct']:.1f}", f"{r['internal_marks']:.1f}",
            f"{r['assignment_score']:.1f}", f"{r['lms_hours_weekly']:.1f}",
            f"{r['previous_gpa']:.2f}",
            f"{r['predicted_gpa']:.2f}" if r['predicted_gpa'] is not None else '',
            f"{r['dropout_risk_score']:.4f}" if r['dropout_risk_score'] is not None else '',
            r['risk_level'], 'Yes' if r['is_anomaly'] else 'No',
            r['anomaly_reason'], r['recommendation'],
        ])
    return response


def _ordered_evaluation_models(evaluation):
    if not isinstance(evaluation, dict):
        return []
    models = evaluation.get('models') or {}
    order = ('dropout_classifier', 'gpa_regressor', 'anomaly_detector')
    return [models[key] for key in order if key in models]


def _compute_analyst_data(selected_batch, selected_course, selected_risk):
    records, pred_map, logs, evaluation, evaluation_error = get_cached('analyst:snapshot', _load_analyst_snapshot, ttl=45.0)
    joined = _build_joined_records(records, pred_map)
    batches = sorted({item['batch'] for item in joined if item['batch']})
    courses = sorted({item['course_code'] for item in joined if item['course_code']})
    filtered = _apply_filters(joined, selected_batch, selected_course, selected_risk)
    risk_order = {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2, 'PENDING': 3}
    filtered.sort(key=lambda x: (risk_order.get(x['risk_level'], 4), -(x['dropout_risk_score'] or 0.0)))
    gpa_vals = [r['predicted_gpa'] for r in filtered if r['predicted_gpa'] is not None]
    kpis = {
        'total_records': len(filtered),
        'high_risk_count': sum(1 for r in filtered if r['risk_level'] == 'HIGH'),
        'anomalies_count': sum(1 for r in filtered if r['is_anomaly']),
        'avg_predicted_gpa': f"{(sum(gpa_vals) / len(gpa_vals)):.2f}" if gpa_vals else '0.00',
    }
    risk_status_map = {'HIGH': 'danger', 'MEDIUM': 'warning', 'LOW': 'success'}
    prediction_rows = []
    for r in filtered:
        score_pct = int(round(r['dropout_risk_score'] * 100)) if r['dropout_risk_score'] is not None else 0
        risk_text = f"{r['risk_level']} ({score_pct}%)" if r['dropout_risk_score'] is not None else 'PENDING'
        prediction_rows.append([
            r['student_id'], r['full_name'], r['batch'], r['course_code'], f"{r['attendance_pct']:.1f}%",
            f"{r['previous_gpa']:.2f}", f"{r['predicted_gpa']:.2f}" if r['predicted_gpa'] is not None else '-',
            {'text': risk_text, 'status': risk_status_map.get(r['risk_level'], 'info')},
            {'text': 'Flagged' if r['is_anomaly'] else 'Normal', 'status': 'danger' if r['is_anomaly'] else 'success'},
            r['anomaly_reason'] if r['is_anomaly'] and r['anomaly_reason'] else r['recommendation'],
        ])
    dataset_rows = []
    for log in logs:
        status_val = str(log.get('status') or 'COMPLETED').upper()
        uploaded_at = log.get('uploaded_at')
        uploaded_text = uploaded_at.strftime('%Y-%m-%d %H:%M') if hasattr(uploaded_at, 'strftime') else '-'
        dataset_rows.append([
            str(log.get('filename') or 'dataset.csv'), int(log.get('rows_processed') or 0),
            int(log.get('missing_values_fixed') or 0),
            {'text': status_val, 'status': 'success' if status_val == 'COMPLETED' else 'danger'},
            uploaded_text,
        ])
    raw_filtered = [r['raw_record'] for r in filtered]
    course_demand = compute_course_demand(pd.DataFrame(raw_filtered)) if raw_filtered else []
    chart_data = {
        'dropout_counts': {
            'LOW': sum(1 for r in filtered if r['risk_level'] == 'LOW'),
            'MEDIUM': sum(1 for r in filtered if r['risk_level'] == 'MEDIUM'),
            'HIGH': sum(1 for r in filtered if r['risk_level'] == 'HIGH'),
        },
        'scatter_points': [
            {'x': round(r['attendance_pct'], 1), 'y': round(r['predicted_gpa'] if r['predicted_gpa'] is not None else r['previous_gpa'], 2), 'label': f"{r['student_id']} ({r['full_name']})", 'risk': r['risk_level']}
            for r in filtered[:250]
        ],
        'course_demand': course_demand,
    }
    return {
        'kpis': kpis, 'filter_options': {'batches': batches, 'courses': courses},
        'prediction_rows': prediction_rows, 'dataset_rows': dataset_rows,
        'chart_data': chart_data, 'filtered': filtered, 'evaluation': evaluation,
        'evaluation_models': _ordered_evaluation_models(evaluation),
        'evaluation_error': evaluation_error,
        'portal_settings': _resolve_runtime_settings(persist=True),
    }


@role_required(['ANALYST', 'ADMIN'])
def analyst_accuracy(request):
    session_user = request.session.get('user') or {}
    active_role = str(session_user.get('role') or 'ANALYST').upper()
    try:
        data = get_analyst_accuracy_page_context()
    except Exception as exc:
        data = {
            'kpis': {}, 'model_info': {'version': 'untrained', 'generated': 'Never', 'features': []},
            'risk_counts': {'LOW': 0, 'MEDIUM': 0, 'HIGH': 0}, 'error_buckets': {},
            'demand_headers': [], 'demand_rows': [], 'upload_headers': [], 'upload_rows': [],
            'display': {'gpa_mae': 'N/A', 'stable_share': 'N/A', 'risk_agreement': 'N/A'},
            'chart_data': {}, 'db_error': str(exc),
        }
    return render(request, 'panels/analyst_accuracy.html', {
        'page_title': 'AI Accuracy', 'active_role': active_role, 'kpis': data['kpis'],
        'model_info': data['model_info'], 'risk_counts': data['risk_counts'],
        'error_buckets': data['error_buckets'], 'gpa_mae_display': data['display']['gpa_mae'],
        'stable_share_display': data['display']['stable_share'],
        'risk_agreement_display': data['display']['risk_agreement'],
        'demand_headers': data['demand_headers'], 'demand_rows': data['demand_rows'],
        'upload_headers': data['upload_headers'], 'upload_rows': data['upload_rows'],
        'chart_data': data['chart_data'], 'db_error': data['db_error'],
    })


@role_required(['ANALYST', 'ADMIN'])
def analyst_dashboard(request):
    selected_batch = str(request.GET.get('batch', 'ALL')).strip() or 'ALL'
    selected_course = str(request.GET.get('course_code', 'ALL')).strip() or 'ALL'
    selected_risk = str(request.GET.get('risk_level', 'ALL')).strip().upper() or 'ALL'
    if request.GET.get('export') == 'csv':
        data = _compute_analyst_data(selected_batch, selected_course, selected_risk)
        return _export_csv_response(data['filtered'])

    session_user = request.session.get('user') or {}
    user_id = str(session_user.get('user_id') or '').strip()
    active_role = str(session_user.get('role') or 'ANALYST').upper()
    cache_key = f"analyst:page:{user_id}:{active_role}:{selected_batch}:{selected_course}:{selected_risk}"

    def _render():
        data = _compute_analyst_data(selected_batch, selected_course, selected_risk)
        resp = render(request, 'panels/analyst_dashboard.html', {
            'page_title': 'Data Dashboard', 'active_role': active_role, 'kpis': data['kpis'],
            'filter_options': data['filter_options'],
            'selected_filters': {'batch': selected_batch, 'course_code': selected_course, 'risk_level': selected_risk},
            'prediction_headers': ['Student ID', 'Name', 'Batch', 'Course', 'Attendance', 'Past GPA', 'Next GPA', 'Risk Level', 'Unusual', 'Tip'],
            'prediction_rows': data['prediction_rows'],
            'dataset_headers': ['File Name', 'Rows', 'Fixed', 'Status', 'Date'],
            'dataset_rows': data['dataset_rows'], 'chart_data': data['chart_data'],
            'evaluation': data['evaluation'], 'evaluation_models': data['evaluation_models'],
            'evaluation_error': data['evaluation_error'], 'portal_settings': data['portal_settings'],
            'required_columns': REQUIRED_COLUMNS,
            'db_error': None,
        })
        return resp.content, resp.get('Content-Type', 'text/html; charset=utf-8')

    content, content_type = get_cached(cache_key, _render, ttl=45.0)
    return HttpResponse(content, content_type=content_type)
