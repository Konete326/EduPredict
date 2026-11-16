REQUIRED_COLUMNS = (
    'student_id',
    'attendance_pct',
    'internal_marks',
    'lms_hours',
    'previous_gpa',
    'course_code',
)


def validate_dataset_columns(columns):
    present = {str(col).strip() for col in columns}
    missing = [col for col in REQUIRED_COLUMNS if col not in present]
    return {
        'valid': len(missing) == 0,
        'missing_columns': missing,
    }


def ingest_dataset_stub(file_obj, uploaded_by=''):
    return {
        'status': 'NOT_IMPLEMENTED_PHASE_1',
        'rows_processed': 0,
        'missing_values_fixed': 0,
        'uploaded_by': uploaded_by,
    }
