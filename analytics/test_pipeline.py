import io
from unittest.mock import MagicMock, patch
import pandas as pd
from django.test import SimpleTestCase
from analytics.data_pipeline import generate_sample_dataset_df, ingest_dataset, validate_dataset_columns
from analytics.ml_engine import (
    _build_recommendation,
    classify_dropout_risk,
    compute_course_demand,
    run_prediction_pipeline,
)
from analytics.tests import _build_genuine_labelled_records


class PredictionPipelineAndDataPipelineTests(SimpleTestCase):
    def test_existing_prediction_pipeline_on_unlabelled_records(self):
        sample_df = generate_sample_dataset_df(30)
        res = run_prediction_pipeline(records=sample_df, persist=False)

        self.assertEqual(res["status"], "COMPLETED")
        self.assertEqual(res["predictions_generated"], 30)
        total_risks = res["high_risk_count"] + res["medium_risk_count"] + res["low_risk_count"]
        self.assertEqual(total_risks, 30)
        self.assertEqual(res["training_modes"]["dropout_classifier"], "synthetic_anchor_and_heuristic_fallback")
        self.assertEqual(res["training_modes"]["gpa_regressor"], "synthetic_anchor_and_heuristic_fallback")
        self.assertEqual(res["evaluation"]["status"], "NO_GENUINE_LABELS")
        self.assertTrue(len(res["course_demand"]) >= 1)
        self.assertEqual(len(res["predictions"]), 30)

    def test_prediction_pipeline_uses_genuine_labels_when_available(self):
        records = _build_genuine_labelled_records(30)
        res = run_prediction_pipeline(records=records, persist=False)
        self.assertEqual(res["status"], "COMPLETED")
        self.assertEqual(res["predictions_generated"], 30)
        self.assertEqual(res["training_modes"]["dropout_classifier"], "genuine_labels")
        self.assertEqual(res["training_modes"]["gpa_regressor"], "genuine_labels")
        self.assertEqual(res["evaluation"]["models"]["dropout_classifier"]["status"], "EVALUATED")
        self.assertEqual(res["evaluation"]["models"]["gpa_regressor"]["status"], "EVALUATED")

    def test_empty_records_and_helpers(self):
        empty_res = run_prediction_pipeline(records=[], persist=False)
        self.assertEqual(empty_res["status"], "EMPTY")
        self.assertEqual(empty_res["predictions_generated"], 0)
        self.assertEqual(classify_dropout_risk(0.75), "HIGH")
        self.assertEqual(classify_dropout_risk(0.50), "MEDIUM")
        self.assertEqual(classify_dropout_risk(0.15), "LOW")
        self.assertEqual(compute_course_demand(pd.DataFrame()), [])
        self.assertTrue(validate_dataset_columns(["roll_no", "marks", "att"])["valid"])

    def test_prediction_pipeline_applies_custom_portal_settings(self):
        sample_df = generate_sample_dataset_df(16)
        res = run_prediction_pipeline(
            records=sample_df,
            persist=False,
            portal_settings={
                "high_risk_threshold": 60, "medium_risk_threshold": 30,
                "anomaly_drop_pct": 20, "min_attendance_pct": 85, "auto_student_alerts": True, "auto_teacher_alerts": False,
            },
        )
        self.assertEqual(res["applied_settings"]["high_risk_threshold"], 60)
        self.assertEqual(res["applied_settings"]["medium_risk_threshold"], 30)
        self.assertEqual(res["applied_settings"]["min_attendance_pct"], 85)
        self.assertFalse(res["applied_settings"]["auto_teacher_alerts"])
        self.assertEqual(classify_dropout_risk(0.62, 0.60, 0.30), "HIGH")
        self.assertEqual(classify_dropout_risk(0.32, 0.60, 0.30), "MEDIUM")
        self.assertEqual(_build_recommendation("MEDIUM", False, 80.0, 75.0, 75.0, 10.0, min_att=85.0), "Attend the next 4 consecutive lectures to lift attendance above 90%.")

        risky = [{"student_id": "STD-RISK-1", "full_name": "Risk Student", "course_code": "CS-101", "attendance_pct": 35.0, "internal_marks": 25.0, "assignment_score": 30.0, "lms_hours_weekly": 1.0, "previous_gpa": 1.2}]
        with patch("analytics.ml_engine.predictions_col") as mock_preds, patch("analytics.ml_engine.notifications_col") as mock_notifs:
            run_prediction_pipeline(
                records=risky, persist=True,
                portal_settings={"high_risk_threshold": 60, "medium_risk_threshold": 30, "anomaly_drop_pct": 20, "auto_student_alerts": True, "auto_teacher_alerts": False},
            )
            mock_preds.return_value.bulk_write.assert_called_once()
            mock_notifs.return_value.bulk_write.assert_called_once()
            ops = mock_notifs.return_value.bulk_write.call_args[0][0]
            roles = [op._filter["target_role"] for op in ops]
            self.assertEqual(roles, ["STUDENT"])

    @patch("analytics.data_pipeline.ensure_indexes")
    @patch("analytics.data_pipeline.datasets_log_col")
    @patch("analytics.data_pipeline.student_records_col")
    def test_ingest_dataset_preserves_optional_genuine_labels_and_counts_inf(
        self, mock_records_col, mock_logs_col, mock_indexes
    ):
        mock_col = MagicMock()
        mock_col.find.return_value = []
        mock_records_col.return_value = mock_col
        mock_logs_col.return_value = MagicMock()

        csv_text = (
            "student_id,marks,attendance,actual_dropout,final_gpa\n"
            "STD-1,88,92,0,3.65\n"
            "STD-2,inf,45,yes,1.80\n"
            "STD-3,70,80,,\n"
        )
        file_obj = io.BytesIO(csv_text.encode("utf-8"))
        file_obj.name = "historical_outcomes.csv"

        result = ingest_dataset(file_obj=file_obj, uploaded_by="analyst@edu.pk", mode="upload")
        self.assertEqual(result["status"], "COMPLETED")
        self.assertEqual(result["rows_processed"], 3)
        self.assertGreaterEqual(result["missing_values_fixed"], 1)
        self.assertEqual(result["labels_detected"]["dropout_label"], 2)
        self.assertEqual(result["labels_detected"]["actual_gpa"], 2)
        ops = mock_col.bulk_write.call_args[0][0]
        third_doc = ops[2]._doc["$set"]
        self.assertIsNone(third_doc["dropout_label"])
        self.assertIsNone(third_doc["actual_gpa"])
