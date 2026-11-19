from io import StringIO
from unittest.mock import MagicMock, patch
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import Client, TestCase
from django.urls import reverse


class SystemHealthEndpointTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_health_check_live_success(self):
        response = self.client.get(reverse("system_health"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("status"), "healthy")
        self.assertEqual(data.get("database"), "connected")
        self.assertIn("latency_ms", data)
        self.assertIn("counts", data)
        self.assertIn("users", data["counts"])
        self.assertIn("student_records", data["counts"])
        self.assertIn("cache", data)
        self.assertIn("memory", data)

    @patch("core.views_health.get_client")
    def test_health_check_db_ping_failure(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.admin.command.side_effect = RuntimeError("Atlas ping timeout")
        mock_get_client.return_value = mock_client

        response = self.client.get(reverse("system_health"))
        self.assertEqual(response.status_code, 503)
        data = response.json()
        self.assertEqual(data.get("status"), "unhealthy")
        self.assertEqual(data.get("database"), "disconnected")
        self.assertIn("Atlas ping timeout", data.get("error", ""))

    @patch("core.views_health.get_client")
    def test_health_check_client_none(self, mock_get_client):
        mock_get_client.return_value = None

        response = self.client.get(reverse("system_health"))
        self.assertEqual(response.status_code, 503)
        data = response.json()
        self.assertEqual(data.get("status"), "unhealthy")
        self.assertEqual(data.get("database"), "disconnected")
        self.assertEqual(data.get("error"), "MongoDB client unavailable")


class VerifyUATManagementCommandTests(TestCase):
    def test_verify_uat_command_full_run(self):
        out = StringIO()
        call_command("verify_uat", stdout=out)
        output_str = out.getvalue()
        self.assertIn("EduPredict End-to-End User Acceptance Test (UAT) Suite", output_str)
        self.assertIn("[PASS] Step 1: Health & System Diagnostics", output_str)
        self.assertIn("[PASS] Step 2: Auth & RBAC", output_str)
        self.assertIn("[PASS] Step 3: Admin Operations", output_str)
        self.assertIn("[PASS] Step 4: Teacher Operations", output_str)
        self.assertIn("[PASS] Step 5: Analyst Operations", output_str)
        self.assertIn("[PASS] Step 6: Student Operations", output_str)
        self.assertIn("[PASS] Step 7: Support & Theme Studio", output_str)
        self.assertIn("7/7 passed", output_str)
        self.assertIn("System 100% Operational", output_str)

    @patch("core.management.commands.verify_uat.Client.get")
    def test_verify_uat_health_failure_raises_command_error(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 503
        mock_resp.json.return_value = {"status": "unhealthy"}
        mock_get.return_value = mock_resp

        out = StringIO()
        with self.assertRaises(CommandError) as ctx:
            call_command("verify_uat", stdout=out)
        self.assertIn("Health check failed", str(ctx.exception))

    @patch("core.management.commands.verify_uat.Client.post")
    def test_verify_uat_auth_failure_raises_command_error(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        out = StringIO()
        with self.assertRaises(CommandError) as ctx:
            call_command("verify_uat", stdout=out)
        self.assertIn("Admin login failed", str(ctx.exception))


class StaticFilesAndProductionConfigTests(TestCase):
    def test_whitenoise_middleware_configured(self):
        from django.conf import settings
        self.assertIn("whitenoise.middleware.WhiteNoiseMiddleware", settings.MIDDLEWARE)
        self.assertTrue(hasattr(settings, "STATIC_ROOT"))
        self.assertIn("staticfiles", settings.STORAGES)

    def test_static_asset_serving_or_dry_run(self):
        out = StringIO()
        call_command("collectstatic", dry_run=True, interactive=False, stdout=out)
        self.assertIn("static files copied", out.getvalue())

    def test_production_security_headers_enabled_when_debug_false(self):
        import importlib
        from config import settings as cfg_settings
        self.assertTrue(hasattr(cfg_settings, "STATIC_ROOT"))
        with patch.dict("os.environ", {"DEBUG": "False", "SECURE_SSL_REDIRECT": "True", "SESSION_COOKIE_SECURE": "True", "CSRF_COOKIE_SECURE": "True"}):
            prod_settings = importlib.reload(cfg_settings)
            self.assertFalse(prod_settings.DEBUG)
            self.assertTrue(prod_settings.SECURE_BROWSER_XSS_FILTER)
            self.assertTrue(prod_settings.SECURE_CONTENT_TYPE_NOSNIFF)
            self.assertEqual(prod_settings.X_FRAME_OPTIONS, "DENY")
            self.assertEqual(prod_settings.SECURE_HSTS_SECONDS, 31536000)
            self.assertTrue(prod_settings.SECURE_SSL_REDIRECT)
            self.assertTrue(prod_settings.SESSION_COOKIE_SECURE)
            self.assertTrue(prod_settings.CSRF_COOKIE_SECURE)
        importlib.reload(cfg_settings)

    def test_docker_and_compose_files_exist_and_clean(self):
        from pathlib import Path
        base = Path(__file__).resolve().parent.parent
        dockerfile = base / "Dockerfile"
        compose = base / "docker-compose.yml"
        self.assertTrue(dockerfile.exists())
        self.assertTrue(compose.exists())
        df_content = dockerfile.read_text(encoding="utf-8")
        self.assertIn("gunicorn", df_content)
        self.assertIn("edupredict", df_content)
        self.assertIn("HEALTHCHECK", df_content)
        self.assertIn("http://localhost:8000/health/", df_content)
        self.assertNotIn("#", df_content)
        compose_content = compose.read_text(encoding="utf-8")
        self.assertIn("8000:8000", compose_content)
        self.assertIn("healthcheck:", compose_content)
        self.assertNotIn("#", compose_content)

    @patch("core.db.MongoClient")
    def test_mongodb_client_connection_pooling_options(self, mock_mongo_client):
        from core.db import MongoDBClient
        client_inst = MongoDBClient()
        with patch.dict("os.environ", {
            "MONGODB_MAX_POOL_SIZE": "75",
            "MONGODB_MIN_POOL_SIZE": "10",
            "MONGODB_MAX_IDLE_TIME_MS": "30000",
            "MONGODB_SOCKET_TIMEOUT_MS": "15000",
            "MONGODB_SERVER_SELECTION_TIMEOUT_MS": "4000",
            "MONGODB_CONNECT_TIMEOUT_MS": "4000",
        }):
            client_inst._build_client("mongodb://test-uri:27017")
            mock_mongo_client.assert_called_with(
                "mongodb://test-uri:27017",
                maxPoolSize=75,
                minPoolSize=10,
                maxIdleTimeMS=30000,
                socketTimeoutMS=15000,
                serverSelectionTimeoutMS=4000,
                connectTimeoutMS=4000,
            )

    def test_theme_aware_500_error_page_renders_cleanly(self):
        from django.template.loader import render_to_string
        from django.test import RequestFactory
        from django.views.defaults import server_error
        content = render_to_string("500.html")
        self.assertIn("Error 500", content)
        self.assertIn("Internal Server Issue", content)
        self.assertIn("/health/", content)
        self.assertNotIn("<!--", content)
        rf = RequestFactory()
        req = rf.get("/some-broken-path/")
        resp = server_error(req)
        self.assertEqual(resp.status_code, 500)
        self.assertIn(b"Error 500", resp.content)
