import io
import json
import math
from unittest.mock import MagicMock, patch
import numpy as np
import pandas as pd
from django.test import Client, SimpleTestCase, TestCase
from django.urls import reverse
from analytics.data_pipeline import generate_sample_dataset_df, ingest_dataset, validate_dataset_columns
from analytics.evaluation import evaluate_model_suite
from analytics.preprocessing import (
    FEATURE_COLUMNS,
    MedianFallbackImputer,
    parse_binary_label,
    parse_gpa_label,
)
from analytics.ml_engine import (
    classify_dropout_risk,
    compute_course_demand,
    evaluate_models,
    run_prediction_pipeline,
)
from core.db import invalidate_cache


def _build_genuine_labelled_records(count=40, include_anomaly_labels=False):
    rng = np.random.default_rng(123)
    rows = []
    for idx in range(count):
        is_high_risk = idx % 2 == 1
        if is_high_risk:
            att = float(rng.uniform(35.0, 58.0))
            marks = float(rng.uniform(25.0, 48.0))
            assign = float(rng.uniform(30.0, 52.0))
            lms = float(rng.uniform(1.0, 5.0))
            prev_gpa = float(rng.uniform(1.2, 2.2))
            dropout = 1
        else:
            att = float(rng.uniform(78.0, 98.0))
            marks = float(rng.uniform(72.0, 95.0))
            assign = float(rng.uniform(74.0, 96.0))
            lms = float(rng.uniform(9.0, 18.0))
            prev_gpa = float(rng.uniform(3.0, 3.95))
            dropout = 0
        noise = float(rng.normal(0.0, 0.05))
        actual_gpa = float(
            np.clip(
                0.5 * prev_gpa + 0.25 * (marks / 25.0) + 0.15 * (assign / 25.0) + 0.10 * (att / 25.0) + noise,
                0.0,
                4.0,
            )
        )
        row = {
            "student_id": f"STD-GEN-{idx + 1:03d}",
            "full_name": f"Student {idx + 1}",
            "batch": "2026-A" if idx % 2 == 0 else "2026-B",
            "course_code": "CS-101" if idx % 3 else "DS-204",
            "attendance_pct": round(att, 2),
            "internal_marks": round(marks, 2),
            "assignment_score": round(assign, 2),
            "lms_hours_weekly": round(lms, 2),
            "previous_gpa": round(prev_gpa, 2),
            "dropout_label": dropout,
            "actual_gpa": round(actual_gpa, 3),
        }
        if include_anomaly_labels:
            row["anomaly_label"] = 1 if idx in (1, 3, 5, 7, 9, 11) else 0
        rows.append(row)
    return rows


class ModelEvaluationTests(SimpleTestCase):
    def test_genuine_classification_and_regression_metrics(self):
        records = _build_genuine_labelled_records(40, include_anomaly_labels=True)
        report = evaluate_models(records=records, test_size=0.25, random_state=42)

        self.assertEqual(report["status"], "COMPLETED")
        self.assertEqual(report["dataset_summary"]["total_records"], 40)
        self.assertEqual(report["dataset_summary"]["genuine_dropout_labels"], 40)
        self.assertEqual(report["dataset_summary"]["genuine_gpa_labels"], 40)

        clf = report["models"]["dropout_classifier"]
        self.assertEqual(clf["status"], "EVALUATED")
        self.assertTrue(clf["uses_genuine_labels"])
        self.assertEqual(clf["train_samples"], 30)
        self.assertEqual(clf["test_samples"], 10)
        cm = clf["metrics"]["confusion_matrix"]
        self.assertEqual(cm["tn"] + cm["fp"] + cm["fn"] + cm["tp"], 10)
        for key in ("accuracy", "precision", "recall", "f1_score"):
            self.assertGreaterEqual(clf["metrics"][key], 0.0)
            self.assertLessEqual(clf["metrics"][key], 1.0)
        self.assertGreaterEqual(clf["metrics"]["accuracy"], 0.8)

        reg = report["models"]["gpa_regressor"]
        self.assertEqual(reg["status"], "EVALUATED")
        self.assertTrue(reg["uses_genuine_labels"])
        self.assertEqual(reg["train_samples"], 30)
        self.assertEqual(reg["test_samples"], 10)
        self.assertGreaterEqual(reg["metrics"]["mae"], 0.0)
        self.assertGreaterEqual(reg["metrics"]["mse"], 0.0)
        self.assertAlmostEqual(reg["metrics"]["rmse"], math.sqrt(reg["metrics"]["mse"]), places=3)
        self.assertGreater(reg["metrics"]["r2_score"], 0.7)

        anom = report["models"]["anomaly_detector"]
        self.assertEqual(anom["status"], "EVALUATED")
        self.assertTrue(anom["uses_genuine_labels"])
        self.assertIn("confusion_matrix", anom["metrics"])

    def test_unlabelled_sample_data_does_not_manufacture_metrics(self):
        sample_df = generate_sample_dataset_df(60)
        report = evaluate_models(records=sample_df, test_size=0.2, random_state=42)

        self.assertEqual(report["status"], "NO_GENUINE_LABELS")
        self.assertEqual(report["models"]["dropout_classifier"]["status"], "UNAVAILABLE")
        self.assertFalse(report["models"]["dropout_classifier"]["uses_genuine_labels"])
        self.assertIsNone(report["models"]["dropout_classifier"]["metrics"])
        self.assertTrue(len(report["models"]["dropout_classifier"]["limitations"]) >= 1)

        self.assertEqual(report["models"]["gpa_regressor"]["status"], "UNAVAILABLE")
        self.assertFalse(report["models"]["gpa_regressor"]["uses_genuine_labels"])
        self.assertIsNone(report["models"]["gpa_regressor"]["metrics"])

        self.assertEqual(report["models"]["anomaly_detector"]["status"], "UNSUPERVISED")
        self.assertIsNone(report["models"]["anomaly_detector"]["metrics"])
        self.assertTrue(len(report["warnings"]) >= 1)

    def test_reproducibility_with_random_state(self):
        records = _build_genuine_labelled_records(36)
        first = evaluate_models(records=records, test_size=0.25, random_state=7)
        second = evaluate_models(records=records, test_size=0.25, random_state=7)
        self.assertEqual(first["models"]["dropout_classifier"]["metrics"], second["models"]["dropout_classifier"]["metrics"])
        self.assertEqual(first["models"]["gpa_regressor"]["metrics"], second["models"]["gpa_regressor"]["metrics"])

    def test_no_data_leakage_in_imputer(self):
        x_train = np.array([
            [80.0, 70.0, 75.0, 10.0, 3.0],
            [82.0, 72.0, 77.0, 12.0, 3.2],
            [np.nan, 74.0, 79.0, np.nan, 3.4],
        ])
        x_test = np.array([
            [10.0, 10.0, 10.0, 1.0, 0.5],
            [np.nan, 10.0, 10.0, np.nan, 0.5],
        ])
        imputer = MedianFallbackImputer([80.0, 70.0, 75.0, 8.0, 3.0])
        imputer.fit(x_train)
        transformed_test = imputer.transform(x_test)
        self.assertEqual(transformed_test[1, 0], 81.0)
        self.assertEqual(transformed_test[1, 3], 11.0)

    def test_missing_invalid_feature_cells_and_all_nan_column(self):
        records = _build_genuine_labelled_records(30)
        for idx, row in enumerate(records):
            row["lms_hours_weekly"] = None
            if idx % 5 == 0:
                row["attendance_pct"] = "N/A"
            if idx % 7 == 0:
                row["internal_marks"] = float("inf")
        records[0]["dropout_label"] = "invalid_status"
        records[1]["actual_gpa"] = 9.5

        report = evaluate_model_suite(records, test_size=0.2, random_state=42)
        self.assertEqual(report["models"]["dropout_classifier"]["status"], "EVALUATED")
        self.assertEqual(report["models"]["dropout_classifier"]["dataset_info"]["valid_labelled_rows"], 29)
        self.assertEqual(report["models"]["gpa_regressor"]["status"], "EVALUATED")
        self.assertEqual(report["models"]["gpa_regressor"]["dataset_info"]["valid_labelled_rows"], 29)
        self.assertTrue(len(report["models"]["dropout_classifier"]["warnings"]) >= 1)

    def test_insufficient_and_single_class_labels(self):
        small_records = _build_genuine_labelled_records(8)
        small_report = evaluate_models(records=small_records)
        self.assertEqual(small_report["models"]["dropout_classifier"]["status"], "INSUFFICIENT_DATA")
        self.assertIsNone(small_report["models"]["dropout_classifier"]["metrics"])
        self.assertEqual(small_report["models"]["gpa_regressor"]["status"], "INSUFFICIENT_DATA")
        self.assertIsNone(small_report["models"]["gpa_regressor"]["metrics"])

        single_class = _build_genuine_labelled_records(20)
        for row in single_class:
            row["dropout_label"] = 0
        single_report = evaluate_models(records=single_class)
        self.assertEqual(single_report["models"]["dropout_classifier"]["status"], "INSUFFICIENT_DATA")
        self.assertIsNone(single_report["models"]["dropout_classifier"]["metrics"])

    def test_invalid_inputs_raise_clear_errors(self):
        with self.assertRaises(ValueError):
            evaluate_models(records="invalid-payload")
        with self.assertRaises(ValueError):
            evaluate_models(records=[{"student_id": "S1", "full_name": "Only Name"}])
        with self.assertRaises(ValueError):
            evaluate_models(records=_build_genuine_labelled_records(20), test_size=1.5)
        with self.assertRaises(ValueError):
            evaluate_models(records=_build_genuine_labelled_records(20), test_size=0.0)
        with self.assertRaises(ValueError):
            evaluate_models(records=_build_genuine_labelled_records(20), random_state=-5)

    def test_label_parsers(self):
        self.assertEqual(parse_binary_label("yes"), 1)
        self.assertEqual(parse_binary_label("Dropped_Out"), 1)
        self.assertEqual(parse_binary_label("retained"), 0)
        self.assertEqual(parse_binary_label(False), 0)
        self.assertIsNone(parse_binary_label("unknown"))
        self.assertEqual(parse_gpa_label("3.45"), 3.45)
        self.assertIsNone(parse_gpa_label(4.5))
        self.assertIsNone(parse_gpa_label(float("nan")))


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


class EvaluationViewTests(TestCase):
    def setUp(self):
        invalidate_cache()

    @patch("analytics.ml_engine.student_records_col")
    def test_evaluation_endpoint_returns_json_and_handles_invalid_params(self, mock_records_col):
        mock_col = MagicMock()
        mock_col.find.return_value = _build_genuine_labelled_records(25)
        mock_records_col.return_value = mock_col

        client = Client()
        session = client.session
        session["user"] = {"user_id": "USR-AN-1", "role": "ANALYST", "email": "analyst@edu.pk", "full_name": "Analyst"}
        session.save()

        url = reverse("analytics:model_evaluation")
        ok_resp = client.get(url)
        self.assertEqual(ok_resp.status_code, 200)
        payload = json.loads(ok_resp.content.decode("utf-8"))
        self.assertEqual(payload["models"]["dropout_classifier"]["status"], "EVALUATED")
        self.assertEqual(payload["models"]["gpa_regressor"]["status"], "EVALUATED")
        self.assertEqual(mock_col.find.call_count, 1)

        cached_resp = client.get(url)
        self.assertEqual(cached_resp.status_code, 200)
        self.assertEqual(mock_col.find.call_count, 1)

        custom_resp = client.get(f"{url}?test_size=0.4&random_state=7")
        self.assertEqual(custom_resp.status_code, 200)
        custom_payload = json.loads(custom_resp.content.decode("utf-8"))
        self.assertEqual(custom_payload["test_size"], 0.4)
        self.assertEqual(custom_payload["random_state"], 7)
        self.assertEqual(custom_payload["models"]["dropout_classifier"]["test_samples"], 10)
        self.assertEqual(mock_col.find.call_count, 2)

        refresh_resp = client.get(f"{url}?refresh=1")
        self.assertEqual(refresh_resp.status_code, 200)
        self.assertEqual(mock_col.find.call_count, 3)

        bad_resp = client.get(f"{url}?test_size=1.5")
        self.assertEqual(bad_resp.status_code, 400)
        err_payload = json.loads(bad_resp.content.decode("utf-8"))
        self.assertEqual(err_payload["status"], "ERROR")

        student_client = Client()
        s_session = student_client.session
        s_session["user"] = {"user_id": "USR-ST-1", "role": "STUDENT", "email": "s@edu.pk", "full_name": "Student"}
        s_session.save()
        denied_resp = student_client.get(url)
        self.assertEqual(denied_resp.status_code, 302)

    @patch("analytics.data_pipeline.ensure_indexes")
    @patch("analytics.data_pipeline.datasets_log_col")
    @patch("analytics.data_pipeline.student_records_col")
    @patch("analytics.ml_engine.student_records_col")
    def test_dataset_update_invalidates_evaluation_cache(
        self, mock_ml_records, mock_pipe_records, mock_logs, mock_indexes
    ):
        mock_ml_col = MagicMock()
        mock_ml_col.find.return_value = _build_genuine_labelled_records(20)
        mock_ml_records.return_value = mock_ml_col

        client = Client()
        session = client.session
        session["user"] = {"user_id": "USR-AN-1", "role": "ANALYST", "email": "analyst@edu.pk", "full_name": "Analyst"}
        session.save()

        url = reverse("analytics:model_evaluation")
        first = json.loads(client.get(url).content.decode("utf-8"))
        self.assertEqual(first["dataset_summary"]["total_records"], 20)
        self.assertEqual(mock_ml_col.find.call_count, 1)

        mock_pipe_col = MagicMock()
        mock_pipe_col.find.return_value = []
        mock_pipe_records.return_value = mock_pipe_col
        mock_logs.return_value = MagicMock()
        csv_file = io.BytesIO(b"student_id,marks,attendance,actual_dropout,final_gpa\nS1,85,90,0,3.5\n")
        csv_file.name = "new_batch.csv"
        ingest_res = ingest_dataset(file_obj=csv_file, uploaded_by="analyst@edu.pk", mode="upload")
        self.assertEqual(ingest_res["status"], "COMPLETED")

        mock_ml_col.find.return_value = _build_genuine_labelled_records(30)
        second = json.loads(client.get(url).content.decode("utf-8"))
        self.assertEqual(second["dataset_summary"]["total_records"], 30)
        self.assertEqual(mock_ml_col.find.call_count, 2)

    def test_zero_variance_gpa_reports_none_r2(self):
        records = _build_genuine_labelled_records(20)
        for row in records:
            row["actual_gpa"] = 3.0
        report = evaluate_models(records=records, test_size=0.2, random_state=42)
        gpa_res = report["models"]["gpa_regressor"]
        self.assertEqual(gpa_res["status"], "EVALUATED")
        self.assertIsNone(gpa_res["metrics"]["r2_score"])
        self.assertTrue(any("zero variance" in msg.lower() for msg in gpa_res["limitations"]))
