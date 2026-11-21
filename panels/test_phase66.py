import ast
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse
import accounts.services as acc_svc
from core.context_processors import global_context
from core.db import DEFAULT_PORTAL_BRANDING, invalidate_cache, resolve_portal_branding
import panels.admin_audit_services as audit_svc
import panels.admin_seed as admin_seed
from panels.pdf_services import _resolve_pdf_branding
from panels.test_admin import _MemCol


class Phase66IntegrationTests(TestCase):
    def setUp(self):
        invalidate_cache()
        self.addCleanup(invalidate_cache)
        now = datetime(2026, 11, 21, 9, 0, tzinfo=timezone.utc)
        self.cols = {
            "users": _MemCol([{
                "user_id": "USR-1000", "full_name": "System Administrator", "email": "admin@gmail.com",
                "password_hash": make_password("admin123"), "role": "ADMIN", "department": "Administration",
                "batch": "ALL", "is_active": True, "approval_status": "APPROVED", "created_at": now,
            }]),
            "student_records": _MemCol(), "predictions": _MemCol(), "datasets_log": _MemCol(),
            "notifications": _MemCol(), "activity_logs": _MemCol(), "courses": _MemCol(),
            "support_tickets": _MemCol(), "system_settings": _MemCol(),
        }
        for p in (
            patch("core.db.MongoDBClient.get_collection", side_effect=lambda name: self.cols.setdefault(name, _MemCol())),
            patch("core.db.MongoDBClient.check_health", return_value={"connected": True, "error": None}),
            patch.object(acc_svc, "_INDEXES_ENSURED", True),
            patch.object(acc_svc, "_DEFAULT_ADMIN_ENSURED", True),
            patch.object(admin_seed, "_ADMIN_SEED_DONE", True),
            patch.object(audit_svc, "_AUDIT_SEED_DONE", True),
        ):
            p.start()
            self.addCleanup(p.stop)

    def _login_analyst(self):
        client = Client()
        session = client.session
        session["user"] = {"user_id": "USR-AN66", "role": "ANALYST", "email": "analyst66@edupredict.edu", "full_name": "Phase66 Analyst"}
        session.save()
        return client

    def test_core_context_no_panels_imports_and_resolve_portal_branding(self):
        ctx_src = (Path(settings.BASE_DIR) / "core" / "context_processors.py").read_text(encoding="utf-8")
        tree = ast.parse(ctx_src)
        imported = [a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names]
        imported += [n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module]
        self.assertTrue(imported)
        self.assertFalse(any(m == "panels" or m.startswith("panels.") for m in imported))

        self.assertEqual(resolve_portal_branding(db_connected=False), DEFAULT_PORTAL_BRANDING)
        self.assertEqual(resolve_portal_branding({"institution_name": " ", "current_term": ""}, db_connected=False), DEFAULT_PORTAL_BRANDING)

        self.cols["system_settings"].insert_one({"setting_key": "portal_config", "institution_name": "Metro University", "current_term": "Summer 2027"})
        invalidate_cache()
        self.assertEqual(resolve_portal_branding(db_connected=True), ("Metro University", "Summer 2027"))
        self.assertEqual(resolve_portal_branding({"institution_name": "Custom Campus"}, db_connected=True), ("Custom Campus", "Summer 2027"))
        ctx = global_context(RequestFactory().get(reverse("panels:analyst_dashboard")))
        self.assertEqual((ctx["portal_institution_name"], ctx["portal_current_term"]), ("Metro University", "Summer 2027"))

    def test_stream_tick_scatter_points_and_analyst_dashboard_live_kpi_sync(self):
        analyst = self._login_analyst()
        resp = analyst.post(reverse("analytics:stream_tick"))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["ok"])
        self.assertIsInstance(data.get("avg_predicted_gpa"), str)
        self.assertRegex(data["avg_predicted_gpa"], r"^\d+\.\d{2}$")
        self.assertTrue(0.0 <= float(data["avg_predicted_gpa"]) <= 4.0)

        scatter_points = data.get("scatter_points")
        self.assertIsInstance(scatter_points, list)
        self.assertTrue(1 <= len(scatter_points) <= 60)
        for pt in scatter_points:
            self.assertTrue({"x", "y", "label", "risk"} <= set(pt.keys()))
            self.assertIsInstance(pt["x"], (int, float))
            self.assertIsInstance(pt["y"], (int, float))
            self.assertIsInstance(pt["label"], str)
            self.assertTrue(pt["label"])
            self.assertIn(pt["risk"], ("LOW", "MEDIUM", "HIGH", "PENDING"))

        dash_resp = analyst.get(reverse("panels:analyst_dashboard"))
        self.assertEqual(dash_resp.status_code, 200)
        html = dash_resp.content.decode("utf-8")
        for expected in (
            "chart-correlation-scatter",
            "Chart.getChart(document.getElementById('chart-correlation-scatter'))",
            "data-kpi-label",
            "[data-kpi-counter]",
            "Average Pred. GPA",
            "data.scatter_points",
            "data.avg_predicted_gpa",
        ):
            self.assertIn(expected, html)

    def test_phase67_kpi_data_value_spa_hook_and_pdf_branding_delegation(self):
        pdf_src = (Path(settings.BASE_DIR) / "panels" / "pdf_services.py").read_text(encoding="utf-8")
        tree = ast.parse(pdf_src)
        first_body_line = min(n.lineno for n in tree.body if not isinstance(n, (ast.Import, ast.ImportFrom)))
        import_nodes = [n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]
        self.assertTrue(import_nodes and all(n.lineno < first_body_line for n in import_nodes))
        self.assertTrue(any(
            isinstance(n, ast.ImportFrom) and n.module == "core.db"
            and any(a.name == "resolve_portal_branding" for a in n.names)
            and n.lineno < first_body_line
            for n in tree.body
        ))

        with patch("panels.pdf_services.resolve_portal_branding", return_value=("Delegated Campus", "Winter 2028")) as mock_resolve:
            self.assertEqual(_resolve_pdf_branding({"batch": "2026-A"}), ("Delegated Campus", "Winter 2028"))
        mock_resolve.assert_called_once_with({"batch": "2026-A"}, db_connected=True)

        self.cols["system_settings"].insert_one({
            "setting_key": "portal_config", "institution_name": "Metro Campus 67", "current_term": "Autumn 2027",
        })
        invalidate_cache()
        self.assertEqual(_resolve_pdf_branding({}), ("Metro Campus 67", "Autumn 2027"))

        with patch("panels.pdf_services.get_portal_settings", return_value={"settings_data": {"institution_name": "Mocked Settings Tech", "current_term": "Spring 2029"}}):
            self.assertEqual(_resolve_pdf_branding({}), ("Mocked Settings Tech", "Spring 2029"))
            self.assertEqual(_resolve_pdf_branding({"institution_name": "Payload Campus"}), ("Payload Campus", "Spring 2029"))

        analyst = self._login_analyst()
        dash_resp = analyst.get(reverse("panels:analyst_dashboard"))
        self.assertEqual(dash_resp.status_code, 200)
        html = dash_resp.content.decode("utf-8")
        self.assertIn("setAttribute('data-kpi-value'", html)
        self.assertIn("window.initAnalystPage", html)

    def test_phase68_spa_stream_hook_and_live_predictions_table_sync(self):
        analyst = self._login_analyst()
        resp = analyst.post(reverse("analytics:stream_tick"))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["ok"])
        events = data.get("events")
        self.assertIsInstance(events, list)
        self.assertTrue(events)
        for ev in events:
            self.assertTrue({"predicted_gpa", "dropout_risk_score", "risk_text", "tip"} <= set(ev.keys()))
            self.assertIsInstance(ev["predicted_gpa"], (int, float))
            self.assertTrue(0.0 <= ev["predicted_gpa"] <= 4.0)
            self.assertIsInstance(ev["dropout_risk_score"], (int, float))
            self.assertTrue(0.0 <= ev["dropout_risk_score"] <= 1.0)
            self.assertRegex(ev["risk_text"], r"^(HIGH|MEDIUM|LOW) \(\d+%\)$")
            self.assertIsInstance(ev["tip"], str)
            self.assertTrue(ev["tip"])

        dir_js = (Path(settings.BASE_DIR) / "static" / "js" / "directory_ui.js").read_text(encoding="utf-8")
        self.assertIn("function syncStreamPredictionTable(events)", dir_js)
        self.assertIn("analyst-predictions-table", dir_js)
        self.assertRegex(dir_js, r"Object\.assign\(\s*window\b[^;]*\bsyncStreamPredictionTable\b")
        reinit_block = dir_js[dir_js.index("window.reinitEduPredictUI"):]
        self.assertIn("clearInterval(window._epAnalystStreamTimer)", reinit_block)
        self.assertIn("window._epAnalystStreamTimer = null", reinit_block)
        self.assertIn("byId('live-stream-toggle-btn')", reinit_block)
        self.assertIn("window.initAnalystPage()", reinit_block)

        dash_resp = analyst.get(reverse("panels:analyst_dashboard"))
        self.assertEqual(dash_resp.status_code, 200)
        html = dash_resp.content.decode("utf-8")
        self.assertIn('id="analyst-predictions-table"', html)
        self.assertIn("window.syncStreamPredictionTable(data.events)", html)
