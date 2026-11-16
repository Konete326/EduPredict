MODEL_VERSION = 'phase1-stub-v0'


def classify_dropout_risk(score):
    if score >= 0.70:
        return 'HIGH'
    if score >= 0.35:
        return 'MEDIUM'
    return 'LOW'


def run_prediction_pipeline_stub(records=None):
    return {
        'status': 'NOT_IMPLEMENTED_PHASE_1',
        'model_version': MODEL_VERSION,
        'predictions_generated': 0,
        'records_received': len(records) if records else 0,
    }
