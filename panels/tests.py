from unittest.mock import MagicMock, patch
from django.test import Client, TestCase
from django.urls import reverse
from analytics.data_pipeline import generate_sample_dataset_df
from analytics.tests import _build_genuine_labelled_records
from core.db import invalidate_cache


class AnalystDashboardEvaluationTests(TestCase):
    def setUp(self):
        invalidate_cache()

    def _login_as(self, role, user_id="USR-TEST-1"):
        client = Client()
        session = client.session
        session["user"] = {
            "user_id": user_id,
            "role": role,
            "email": f"{role.lower()}@edupredict.edu",
            "full_name": f"Test {role.title()}",
        }
        session.save()
        return client

    @patch("core.context_processors.notifications_col")
    @patch("core.db.MongoDBClient.check_health")
    @patch("panels.views_analyst.datasets_log_col")
    @patch("panels.views_analyst.predictions_col")
    @patch("panels.views_analyst.student_records_col")
    def test_analyst_dashboard_shows_genuine_evaluation_metrics_single_load(
        self, mock_records, mock_preds, mock_logs, mock_health, mock_notifs
    ):
        records = _build_genuine_labelled_records(40, include_anomaly_labels=True)
        records_col = MagicMock()
        records_col.find.return_value = records
        mock_records.return_value = records_col

        preds_col = MagicMock()
        preds_col.find.return_value = [
            {
                "student_id": r["student_id"],
                "predicted_gpa": r["actual_gpa"],
                "dropout_risk_score": 0.8 if r["dropout_label"] else 0.1,
                "risk_level": "HIGH" if r["dropout_label"] else "LOW",
                "is_anomaly": False,
                "anomaly_reason": "",
                "recommendation": "Keep steady progress.",
            }
            for r in records
        ]
        mock_preds.return_value = preds_col

        logs_cursor = MagicMock()
        logs_cursor.sort.return_value.limit.return_value = []
        logs_col = MagicMock()
        logs_col.find.return_value = logs_cursor
        mock_logs.return_value = logs_col
        mock_health.return_value = {"connected": True, "error": None}
        notifs_col = MagicMock()
        notifs_col.count_documents.return_value = 0
        notifs_cursor = MagicMock()
        notifs_cursor.sort.return_value.limit.return_value = []
        notifs_col.find.return_value = notifs_cursor
        mock_notifs.return_value = notifs_col

        client = self._login_as("ANALYST")
        resp = client.get(reverse("panels:analyst_dashboard"))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode("utf-8")

        self.assertEqual(records_col.find.call_count, 1)
        self.assertIn('id="ml-evaluation-section"', html)
        self.assertIn("Dropout Risk Classifier (RandomForestClassifier)", html)
        self.assertIn("GPA Forecaster (Ridge)", html)
        self.assertIn("Anomaly Detector (IsolationForest)", html)
        self.assertIn("COMPLETED", html)
        self.assertIn("EVALUATED", html)
        self.assertIn("Confusion Matrix", html)
        self.assertIn("Accuracy", html)
        self.assertIn("Precision", html)
        self.assertIn("Recall", html)
        self.assertIn("F1-Score", html)
        self.assertIn("MAE", html)
        self.assertIn("MSE", html)
        self.assertIn("RMSE", html)
        self.assertIn("R&sup2; Score", html)
        self.assertIn("32", html)
        self.assertIn("8", html)
        self.assertIn("Data &amp; Predictions Hub", html)
        self.assertIn("Student Predictions", html)
        self.assertIn('href="/analyst-panel/#ml-evaluation-section"', html)
        self.assertNotIn('data-coming-title="AI Accuracy"', html)

        with patch("analytics.ml_engine.student_records_col") as mock_ml_records:
            eval_resp = client.get(reverse("analytics:model_evaluation"))
            self.assertEqual(eval_resp.status_code, 200)
            self.assertEqual(mock_ml_records.call_count, 0)

    @patch("core.context_processors.notifications_col")
    @patch("core.db.MongoDBClient.check_health")
    @patch("panels.views_analyst.datasets_log_col")
    @patch("panels.views_analyst.predictions_col")
    @patch("panels.views_analyst.student_records_col")
    def test_analyst_dashboard_handles_unlabelled_data_honestly(
        self, mock_records, mock_preds, mock_logs, mock_health, mock_notifs
    ):
        sample_records = generate_sample_dataset_df(30).to_dict(orient="records")
        records_col = MagicMock()
        records_col.find.return_value = sample_records
        mock_records.return_value = records_col

        preds_col = MagicMock()
        preds_col.find.return_value = []
        mock_preds.return_value = preds_col

        logs_cursor = MagicMock()
        logs_cursor.sort.return_value.limit.return_value = []
        logs_col = MagicMock()
        logs_col.find.return_value = logs_cursor
        mock_logs.return_value = logs_col
        mock_health.return_value = {"connected": True, "error": None}
        notifs_col = MagicMock()
        notifs_col.count_documents.return_value = 0
        notifs_cursor = MagicMock()
        notifs_cursor.sort.return_value.limit.return_value = []
        notifs_col.find.return_value = notifs_cursor
        mock_notifs.return_value = notifs_col

        client = self._login_as("ANALYST")
        resp = client.get(reverse("panels:analyst_dashboard"))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode("utf-8")

        self.assertIn("NO_GENUINE_LABELS", html)
        self.assertIn("UNAVAILABLE", html)
        self.assertIn("UNSUPERVISED", html)
        self.assertIn("Metrics Unavailable", html)
        self.assertIn("Unsupervised Mode", html)
        self.assertNotIn("Confusion Matrix", html)
        self.assertIn("did not manufacture accuracy scores", html)

    @patch("core.context_processors.notifications_col")
    @patch("core.db.MongoDBClient.check_health")
    @patch("panels.views_analyst.evaluate_models", side_effect=RuntimeError("Eval engine test failure"))
    @patch("panels.views_analyst.datasets_log_col")
    @patch("panels.views_analyst.predictions_col")
    @patch("panels.views_analyst.student_records_col")
    def test_dashboard_survives_evaluation_error_gracefully(
        self, mock_records, mock_preds, mock_logs, mock_eval, mock_health, mock_notifs
    ):
        records_col = MagicMock()
        records_col.find.return_value = []
        mock_records.return_value = records_col
        mock_preds.return_value.find.return_value = []
        mock_logs.return_value.find.return_value.sort.return_value.limit.return_value = []
        mock_health.return_value = {"connected": True, "error": None}
        notifs_col = MagicMock()
        notifs_col.count_documents.return_value = 0
        notifs_col.find.return_value.sort.return_value.limit.return_value = []
        mock_notifs.return_value = notifs_col

        client = self._login_as("ANALYST")
        resp = client.get(reverse("panels:analyst_dashboard"))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode("utf-8")
        self.assertIn("Could not evaluate models: Eval engine test failure", html)
        self.assertIn("Data &amp; Predictions Hub", html)

    def test_unauthorized_users_cannot_access_analyst_evaluation(self):
        anon = Client()
        self.assertEqual(anon.get(reverse("panels:analyst_dashboard")).status_code, 302)
        self.assertEqual(anon.get(reverse("analytics:model_evaluation")).status_code, 302)

        student = self._login_as("STUDENT")
        self.assertRedirects(
            student.get(reverse("panels:analyst_dashboard")),
            reverse("panels:student_dashboard"),
            fetch_redirect_response=False,
        )
        self.assertRedirects(
            student.get(reverse("analytics:model_evaluation")),
            reverse("panels:student_dashboard"),
            fetch_redirect_response=False,
        )

        teacher = self._login_as("TEACHER")
        self.assertRedirects(
            teacher.get(reverse("analytics:model_evaluation")),
            reverse("panels:teacher_dashboard"),
            fetch_redirect_response=False,
        )
