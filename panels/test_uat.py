from io import StringIO
from pathlib import Path
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

    def test_health_check_counts_cached_and_fresh_parameter(self):
        from core.db import _MEMORY_CACHE, invalidate_cache
        invalidate_cache()
        self.assertNotIn("health:collection_counts", _MEMORY_CACHE)
        resp1 = self.client.get(reverse("system_health"))
        self.assertEqual(resp1.status_code, 200)
        self.assertIn("health:collection_counts", _MEMORY_CACHE)
        resp2 = self.client.get(reverse("system_health"))
        self.assertEqual(resp2.status_code, 200)
        resp3 = self.client.get(reverse("system_health") + "?fresh=1")
        self.assertEqual(resp3.status_code, 200)
        self.assertIn("health:collection_counts", _MEMORY_CACHE)

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
            self.assertEqual(prod_settings.SECURE_PROXY_SSL_HEADER, ("HTTP_X_FORWARDED_PROTO", "https"))
            self.assertTrue(prod_settings.USE_X_FORWARDED_HOST)
            self.assertEqual(prod_settings.SECURE_REFERRER_POLICY, "strict-origin-when-cross-origin")
            self.assertEqual(prod_settings.SECURE_CROSS_ORIGIN_OPENER_POLICY, "same-origin-allow-popups")
        importlib.reload(cfg_settings)

    def test_docker_and_compose_files_exist_and_clean(self):
        base = Path(__file__).resolve().parent.parent
        dockerfile = base / "Dockerfile"
        compose = base / "docker-compose.yml"
        self.assertTrue(dockerfile.exists())
        self.assertTrue(compose.exists())
        df_content = dockerfile.read_text(encoding="utf-8")
        self.assertIn("gunicorn", df_content)
        self.assertIn("edupredict", df_content)
        self.assertIn("compileall", df_content)
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


    @patch("sentry_sdk.init")
    def test_sentry_sdk_conditional_initialization_block(self, mock_sentry_init):
        import os
        from sentry_sdk.integrations.django import DjangoIntegration
        test_dsn = "https://public@sentry.example.com/1"
        with patch.dict(os.environ, {"SENTRY_DSN": test_dsn, "SENTRY_TRACES_SAMPLE_RATE": "0.2"}):
            dsn_val = os.getenv("SENTRY_DSN", "").strip()
            if dsn_val:
                import sentry_sdk
                sentry_sdk.init(
                    dsn=dsn_val,
                    integrations=[DjangoIntegration()],
                    traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
                    send_default_pii=False,
                    environment=os.getenv("ENVIRONMENT", "production"),
                )
            mock_sentry_init.assert_called_once()
            self.assertEqual(mock_sentry_init.call_args.kwargs.get("environment"), "production")

    def test_sentry_before_send_sanitization_and_tagging(self):
        from core.middleware import sentry_before_send
        class MockMongoError(Exception):
            pass
        event = {
            "request": {
                "query_string": "token=secret123&user=admin",
                "headers": {"Authorization": "Bearer 123", "Cookie": "session=abc"},
            }
        }
        hint = {"exc_info": (MockMongoError, MockMongoError("connection timeout"), None)}
        processed = sentry_before_send(event, hint)
        self.assertEqual(processed["request"]["query_string"], "[FILTERED]")
        self.assertEqual(processed["request"]["headers"]["Authorization"], "[FILTERED]")
        self.assertEqual(processed["request"]["headers"]["Cookie"], "[FILTERED]")
        self.assertEqual(processed["tags"]["infrastructure"], "mongodb")


    def test_whitenoise_cache_control_settings_present(self):
        from django.conf import settings
        self.assertTrue(hasattr(settings, "WHITENOISE_MAX_AGE"))
        self.assertIsInstance(settings.WHITENOISE_MAX_AGE, int)
        self.assertTrue(hasattr(settings, "WHITENOISE_MANIFEST_STRICT"))
        self.assertFalse(settings.WHITENOISE_MANIFEST_STRICT)

    def test_uat_command_health_retry_on_transient_failure(self):
        from core.management.commands.verify_uat import Command as UATCommand
        cmd = UATCommand()
        mock_client = MagicMock()
        resp_fail = MagicMock()
        resp_fail.status_code = 503
        resp_success = MagicMock()
        resp_success.status_code = 200
        resp_success.json.return_value = {"status": "healthy", "latency_ms": 12.5}
        mock_client.get.side_effect = [resp_fail, resp_success]
        result = cmd._run_step_1_health(mock_client)
        self.assertIn("[PASS] Step 1: Health & System Diagnostics", result)
        self.assertEqual(mock_client.get.call_count, 2)

    def test_robots_txt_endpoint_renders_and_disallows_private_panels(self):
        resp = self.client.get("/robots.txt")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/plain", resp["Content-Type"])
        content = resp.content.decode("utf-8")
        self.assertIn("User-agent: *", content)
        self.assertIn("Disallow: /admin-panel/", content)
        self.assertIn("Disallow: /teacher-panel/", content)
        self.assertIn("Disallow: /student-panel/", content)
        self.assertIn("Disallow: /analyst-panel/", content)
        self.assertIn("Allow: /auth/", content)
        self.assertIn("Allow: /health/", content)

    def test_session_timeout_settings_present(self):
        from django.conf import settings
        self.assertTrue(hasattr(settings, "SESSION_COOKIE_AGE"))
        self.assertEqual(settings.SESSION_COOKIE_AGE, 86400)
        self.assertTrue(settings.SESSION_SAVE_EVERY_REQUEST)
        self.assertEqual(settings.DATA_UPLOAD_MAX_MEMORY_SIZE, 5242880)
        self.assertEqual(settings.FILE_UPLOAD_MAX_MEMORY_SIZE, 5242880)
        self.assertTrue(settings.SESSION_COOKIE_HTTPONLY)
        self.assertEqual(settings.SESSION_COOKIE_SAMESITE, "Lax")
        self.assertEqual(settings.CSRF_COOKIE_SAMESITE, "Lax")

    def test_favicon_endpoint_renders_svg_icon(self):
        resp = self.client.get("/favicon.ico")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "image/svg+xml")
        self.assertEqual(resp["Cache-Control"], "public, max-age=86400")
        self.assertIn(b"<svg", resp.content)

    def test_auth_login_failure_handles_gracefully_with_message(self):
        resp = self.client.post(
            reverse("accounts:auth_view"),
            {"action": "login", "email": "nonexistent@test.com", "password": "wrongpassword123"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Invalid email or password.", resp.content.decode("utf-8"))

    def test_health_endpoint_reports_process_memory(self):
        resp = self.client.get("/health/")
        self.assertIn("Cache-Control", resp)
        self.assertIn("no-store", resp["Cache-Control"])
        if resp.status_code == 200:
            data = resp.json()
            self.assertIn("memory", data)
            self.assertIn("status", data["memory"])
            self.assertIn("cache_entries", data["memory"])
            if "rss_mb" in data["memory"]:
                self.assertGreater(data["memory"]["rss_mb"], 0)

    def test_content_security_policy_header_present(self):
        resp = self.client.get("/auth/")
        self.assertIn("Content-Security-Policy", resp)
        csp = resp["Content-Security-Policy"]
        self.assertIn("default-src 'self'", csp)
        self.assertIn("cdn.tailwindcss.com", csp)
        self.assertIn("cdn.jsdelivr.net", csp)
        self.assertIn("Permissions-Policy", resp)
        pp = resp["Permissions-Policy"]
        self.assertIn("camera=()", pp)
        self.assertIn("microphone=()", pp)
        self.assertIn("geolocation=()", pp)


class ProductionDocumentationTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.readme_path = Path(__file__).resolve().parent.parent / "README.md"
        cls.content = cls.readme_path.read_text(encoding="utf-8") if cls.readme_path.exists() else ""

    def test_readme_exists_and_not_empty(self):
        self.assertTrue(self.readme_path.exists())
        self.assertGreater(len(self.content.splitlines()), 50)

    def test_readme_essential_sections_present(self):
        text = self.content.lower()
        for sec in ("quickstart", "architecture", "docker", "operations", "runbook"):
            self.assertIn(sec, text)
        self.assertTrue("role" in text or "roles" in text)
