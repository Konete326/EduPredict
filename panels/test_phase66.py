import ast
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse
import accounts.services as acc_svc
from core.context_processors import STATIC_ASSET_VERSION, global_context
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

    def test_phase69_mobile_stream_cards_search_sync_and_v17_cache_bust(self):
        base_dir = Path(settings.BASE_DIR)
        app_js = (base_dir / "static" / "js" / "app.js").read_text(encoding="utf-8")
        dir_js = (base_dir / "static" / "js" / "directory_ui.js").read_text(encoding="utf-8")
        self.assertIn("refreshSearchText", app_js)
        self.assertIn("_paginationController", app_js)
        self.assertIn("[data-mobile-card]", dir_js)
        self.assertIn("refreshSearchText()", dir_js)

        node_script = r"""
const fs = require('fs'), vm = require('vm'), assert = require('assert');
class El {
  constructor(t, a = {}, tx = '') { this.tag = t.toLowerCase(); this.attrs = { ...a }; this.children = []; this._text = String(tx); this.parentNode = null; this.parentElement = null; this.dataset = {}; this.style = {}; const cls = new Set((a.class || '').split(/\s+/).filter(Boolean)); this.classList = { add: (...x) => x.forEach((c) => c && cls.add(c)), remove: (...x) => x.forEach((c) => cls.delete(c)), contains: (c) => cls.has(c), toggle: (c, f) => { const on = f === undefined ? !cls.has(c) : Boolean(f); on ? cls.add(c) : cls.delete(c); return on; } }; }
  append(...ns) { ns.forEach((n) => { n.parentNode = this; n.parentElement = this; this.children.push(n); }); } appendChild(n) { this.append(n); return n; } getAttribute(k) { return k in this.attrs ? String(this.attrs[k]) : null; } setAttribute(k, v) { this.attrs[k] = String(v); } removeAttribute(k) { delete this.attrs[k]; } hasAttribute(k) { return k in this.attrs; } addEventListener() {}
  get cells() { return this.children.filter((c) => c.tag === 'td' || c.tag === 'th'); } get textContent() { return this.children.length ? this.children.map((c) => c.textContent).join('') : this._text; } set textContent(v) { this.children = []; this._text = v == null ? '' : String(v); }
  closest(s) { for (let p = this; p; p = p.parentElement) if (s.trim().split(/\s+/).every((k) => mOne(p, k))) return p; return null; } querySelector(s) { return this.querySelectorAll(s)[0] || null; }
  querySelectorAll(s) { const ps = s.split(',').map((x) => x.trim()).filter(Boolean), out = [], seen = new Set(); const w = (n) => n.children.forEach((c) => { if (ps.some((p) => mDesc(c, p, this)) && !seen.has(c)) { seen.add(c); out.push(c); } w(c); }); w(this); return out; }
}
const mOne = (el, tok) => { const re = /:not\(([^)]+)\)/g; let m; while ((m = re.exec(tok))) if (mOne(el, m[1])) return false; const b = tok.replace(re, ''), tm = b.match(/^[a-z0-9-]+/i); if (tm && el.tag !== tm[0].toLowerCase()) return false; for (const cm of b.matchAll(/\.([a-z0-9_-]+)/gi)) if (!el.classList.contains(cm[1])) return false; for (const am of b.matchAll(/\[([a-z0-9_-]+)(?:="([^"]*)")?\]/gi)) if (!(am[1] in el.attrs) || (am[2] !== undefined && String(el.attrs[am[1]]) !== am[2])) return false; return true; };
const mDesc = (el, sel, root) => { const segs = sel.trim().split(/\s+/); if (!mOne(el, segs[segs.length - 1])) return false; let cur = el.parentElement; for (let i = segs.length - 2; i >= 0; i--) { while (cur && cur !== root && !mOne(cur, segs[i])) cur = cur.parentElement; if (!cur || (cur === root && !mOne(cur, segs[i]))) return false; cur = cur.parentElement; } return true; };
const root = new El('html'), body = new El('body'), box = new El('div', { 'data-paginated-container': '', 'data-page-size': '5' }), tbl = new El('table', { id: 'analyst-predictions-table' }), tbody = new El('tbody'); root.append(body);
const mkB = (t) => { const p = new El('span', { class: 'inline-flex' }); p.append(new El('span', { class: 'rounded-full bg-[var(--status-success)]' }), new El('span', {}, t)); return p; };
const mkR = (s, r, a, tip) => { const tr = new El('tr', { 'data-page-item': '' }); [s, 'N', '2026-A', 'CS-101', '88.0%', '3.20', '3.10'].forEach((v) => tr.append(new El('td', {}, v))); const rT = new El('td'), aT = new El('td'); rT.append(mkB(r)); aT.append(mkB(a)); tr.append(rT, aT, new El('td', {}, tip)); return tr; };
const mkC = (s, r, a, tip) => { const c = new El('div', { 'data-mobile-card': '', 'data-page-item': '' }); [s, 'N', '2026-A', 'CS-101', '88.0%', '3.20', '3.10', { b: r }, { b: a }, tip].forEach((v) => { const rw = new El('div', { class: 'flex' }), bx = new El('div', { class: 'min-w-0 text-right' }); if (v && v.b) bx.append(mkB(v.b)); else bx.textContent = v; rw.append(new El('span', {}, 'L'), bx); c.append(rw); }); return c; };
const tr1 = mkR('STD-1', 'LOW (15%)', 'Normal', 'Steady'), tr2 = mkR('STD-2', 'LOW (10%)', 'Normal', 'On track'), c1 = mkC('STD-1', 'LOW (15%)', 'Normal', 'Steady'), c2 = mkC('STD-2', 'LOW (10%)', 'Normal', 'On track'); tbody.append(tr1, tr2); tbl.append(tbody); box.append(tbl, c1, c2); body.append(box);
const findId = (n, id) => { if (n.attrs.id === id) return n; for (const c of n.children) { const f = findId(c, id); if (f) return f; } return null; };
const doc = { readyState: 'complete', cookie: '', documentElement: root, body, createElement: (t) => new El(t), addEventListener: () => {}, getElementById: (id) => findId(root, id), querySelector: (s) => root.querySelector(s), querySelectorAll: (s) => root.querySelectorAll(s) };
const win = { innerWidth: 1280, addEventListener: () => {}, dispatchEvent: () => {}, setTimeout: () => 0, clearTimeout: () => {}, setInterval: () => 0, clearInterval: () => {}, requestAnimationFrame: (f) => f(), localStorage: { getItem: () => null, setItem: () => {} }, Event: function (t) { this.type = t; }, CustomEvent: function (t, d) { this.type = t; this.detail = d; }, document: doc }; win.window = win;
const ctx = vm.createContext({ ...win, window: win, document: doc, console }); vm.runInContext(fs.readFileSync(process.argv[1], 'utf8'), ctx); vm.runInContext(fs.readFileSync(process.argv[2], 'utf8'), ctx);
assert.strictEqual(typeof box._paginationController.refreshSearchText, 'function'); box._paginationController.applySearch('flagged'); assert.ok(tr1.classList.contains('hidden') && c1.classList.contains('hidden'));
win.syncStreamPredictionTable([{ student_id: 'STD-1', attendance_pct: 61.5, predicted_gpa: 2.35, risk_level: 'HIGH', risk_text: 'HIGH (88%)', is_anomaly: true, tip: 'Urgent lab check' }]);
[4, 6, 7, 8, 9].forEach((k, i) => { const exp = ['61.5%', '2.35', 'HIGH (88%)', 'Flagged', 'Urgent lab check'][i]; assert.strictEqual(tr1.cells[k].textContent, exp); assert.strictEqual(c1.children[k].querySelector('div.text-right').textContent, exp); });
assert.ok(c1.children[7].querySelector('span.rounded-full').classList.contains('bg-[var(--status-danger)]') && c1.children[8].querySelector('span.rounded-full').classList.contains('bg-[var(--status-danger)]'));
assert.ok(!tr1.classList.contains('hidden') && !c1.classList.contains('hidden') && tr2.classList.contains('hidden') && c2.classList.contains('hidden'));
box._paginationController.applySearch('urgent lab check'); assert.ok(!tr1.classList.contains('hidden') && !c1.classList.contains('hidden'));
"""
        proc = subprocess.run(["node", "-e", node_script, str(base_dir / "static" / "js" / "app.js"), str(base_dir / "static" / "js" / "directory_ui.js")], capture_output=True, text=True, check=False)
        self.assertEqual(proc.returncode, 0, msg=proc.stderr or proc.stdout)
        for rel in ("templates/base.html", "templates/accounts/auth.html"):
            src = (base_dir / rel).read_text(encoding="utf-8")
            self.assertNotIn("?v=16", src)
            versions = re.findall(r"%\}\?v=(\d+)", src)
            self.assertTrue(versions and all(v == "17" for v in versions), rel)
        analyst_html = self._login_analyst().get(reverse("panels:analyst_dashboard")).content.decode("utf-8")
        self.assertNotIn("?v=16", analyst_html)
        for asset in ("global.css?v=17", "app.js?v=17", "directory_ui.js?v=17"):
            self.assertIn(asset, analyst_html)
        auth_html = Client().get(reverse("accounts:auth_view")).content.decode("utf-8")
        self.assertNotIn("?v=16", auth_html)
        for asset in ("global.css?v=17", "app.js?v=17", "theme_studio.js?v=17", "auth_wizard.js?v=17"):
            self.assertIn(asset, auth_html)

    def test_phase70_mobile_card_id_matching_and_unified_v17_assets(self):
        base_dir = Path(settings.BASE_DIR)
        dir_js = (base_dir / "static" / "js" / "directory_ui.js").read_text(encoding="utf-8")
        self.assertIn("cardMap", dir_js)
        self.assertIn("cardMap.get(sid)", dir_js)

        node_script = r"""
const fs = require('fs'), vm = require('vm'), assert = require('assert');
class El {
  constructor(t, a = {}, tx = '') { this.tag = t.toLowerCase(); this.attrs = { ...a }; this.children = []; this._text = String(tx); this.parentNode = null; this.parentElement = null; this.dataset = {}; this.style = {}; const cls = new Set((a.class || '').split(/\s+/).filter(Boolean)); this.classList = { add: (...x) => x.forEach((c) => c && cls.add(c)), remove: (...x) => x.forEach((c) => cls.delete(c)), contains: (c) => cls.has(c), toggle: (c, f) => { const on = f === undefined ? !cls.has(c) : Boolean(f); on ? cls.add(c) : cls.delete(c); return on; } }; }
  append(...ns) { ns.forEach((n) => { n.parentNode = this; n.parentElement = this; this.children.push(n); }); } appendChild(n) { this.append(n); return n; } getAttribute(k) { return k in this.attrs ? String(this.attrs[k]) : null; } setAttribute(k, v) { this.attrs[k] = String(v); } removeAttribute(k) { delete this.attrs[k]; } hasAttribute(k) { return k in this.attrs; } addEventListener() {}
  get cells() { return this.children.filter((c) => c.tag === 'td' || c.tag === 'th'); } get textContent() { return this.children.length ? this.children.map((c) => c.textContent).join('') : this._text; } set textContent(v) { this.children = []; this._text = v == null ? '' : String(v); }
  closest(s) { for (let p = this; p; p = p.parentElement) if (s.trim().split(/\s+/).every((k) => mOne(p, k))) return p; return null; } querySelector(s) { return this.querySelectorAll(s)[0] || null; }
  querySelectorAll(s) { const ps = s.split(',').map((x) => x.trim()).filter(Boolean), out = [], seen = new Set(); const w = (n) => n.children.forEach((c) => { if (ps.some((p) => mDesc(c, p, this)) && !seen.has(c)) { seen.add(c); out.push(c); } w(c); }); w(this); return out; }
}
const mOne = (el, tok) => { const re = /:not\(([^)]+)\)/g; let m; while ((m = re.exec(tok))) if (mOne(el, m[1])) return false; const b = tok.replace(re, ''), tm = b.match(/^[a-z0-9-]+/i); if (tm && el.tag !== tm[0].toLowerCase()) return false; for (const cm of b.matchAll(/\.([a-z0-9_-]+)/gi)) if (!el.classList.contains(cm[1])) return false; for (const am of b.matchAll(/\[([a-z0-9_-]+)(?:="([^"]*)")?\]/gi)) if (!(am[1] in el.attrs) || (am[2] !== undefined && String(el.attrs[am[1]]) !== am[2])) return false; return true; };
const mDesc = (el, sel, root) => { const segs = sel.trim().split(/\s+/); if (!mOne(el, segs[segs.length - 1])) return false; let cur = el.parentElement; for (let i = segs.length - 2; i >= 0; i--) { while (cur && cur !== root && !mOne(cur, segs[i])) cur = cur.parentElement; if (!cur || (cur === root && !mOne(cur, segs[i]))) return false; cur = cur.parentElement; } return true; };
const root = new El('html'), body = new El('body'), box = new El('div', { 'data-paginated-container': '', 'data-page-size': '5' }), tbl = new El('table', { id: 'analyst-predictions-table' }), tbody = new El('tbody'); root.append(body);
const mkB = (t) => { const p = new El('span', { class: 'inline-flex' }); p.append(new El('span', { class: 'rounded-full bg-[var(--status-success)]' }), new El('span', {}, t)); return p; };
const mkR = (s, r, a, tip) => { const tr = new El('tr', { 'data-page-item': '' }); [s, 'N', '2026-A', 'CS-101', '88.0%', '3.20', '3.10'].forEach((v) => tr.append(new El('td', {}, v))); const rT = new El('td'), aT = new El('td'); rT.append(mkB(r)); aT.append(mkB(a)); tr.append(rT, aT, new El('td', {}, tip)); return tr; };
const mkC = (s, r, a, tip) => { const c = new El('div', { 'data-mobile-card': '', 'data-page-item': '' }); [s, 'N', '2026-A', 'CS-101', '88.0%', '3.20', '3.10', { b: r }, { b: a }, tip].forEach((v) => { const rw = new El('div', { class: 'flex' }), bx = new El('div', { class: 'min-w-0 text-right' }); if (v && v.b) bx.append(mkB(v.b)); else bx.textContent = v; rw.append(new El('span', {}, 'L'), bx); c.append(rw); }); return c; };
const tr1 = mkR('STD-1', 'LOW (15%)', 'Normal', 'Steady'), tr2 = mkR('STD-2', 'LOW (10%)', 'Normal', 'On track'), c1 = mkC('STD-1', 'LOW (15%)', 'Normal', 'Steady'), c2 = mkC('STD-2', 'LOW (10%)', 'Normal', 'On track'); tbody.append(tr1, tr2); tbl.append(tbody); box.append(tbl, c2, c1); body.append(box);
const findId = (n, id) => { if (n.attrs.id === id) return n; for (const c of n.children) { const f = findId(c, id); if (f) return f; } return null; };
const doc = { readyState: 'complete', cookie: '', documentElement: root, body, createElement: (t) => new El(t), addEventListener: () => {}, getElementById: (id) => findId(root, id), querySelector: (s) => root.querySelector(s), querySelectorAll: (s) => root.querySelectorAll(s) };
const win = { innerWidth: 1280, addEventListener: () => {}, dispatchEvent: () => {}, setTimeout: () => 0, clearTimeout: () => {}, setInterval: () => 0, clearInterval: () => {}, requestAnimationFrame: (f) => f(), localStorage: { getItem: () => null, setItem: () => {} }, Event: function (t) { this.type = t; }, CustomEvent: function (t, d) { this.type = t; this.detail = d; }, document: doc }; win.window = win;
const ctx = vm.createContext({ ...win, window: win, document: doc, console }); vm.runInContext(fs.readFileSync(process.argv[1], 'utf8'), ctx); vm.runInContext(fs.readFileSync(process.argv[2], 'utf8'), ctx);
win.syncStreamPredictionTable([{ student_id: 'STD-1', attendance_pct: 61.5, predicted_gpa: 2.35, risk_level: 'HIGH', risk_text: 'HIGH (88%)', is_anomaly: true, tip: 'Urgent lab check' }]);
[4, 6, 7, 8, 9].forEach((k, i) => {
  const exp1 = ['61.5%', '2.35', 'HIGH (88%)', 'Flagged', 'Urgent lab check'][i];
  const exp2 = ['88.0%', '3.10', 'LOW (10%)', 'Normal', 'On track'][i];
  assert.strictEqual(tr1.cells[k].textContent, exp1);
  assert.strictEqual(c1.children[k].querySelector('div.text-right').textContent, exp1);
  assert.strictEqual(tr2.cells[k].textContent, exp2);
  assert.strictEqual(c2.children[k].querySelector('div.text-right').textContent, exp2);
});
assert.ok(c1.children[7].querySelector('span.rounded-full').classList.contains('bg-[var(--status-danger)]') && c1.children[8].querySelector('span.rounded-full').classList.contains('bg-[var(--status-danger)]'));
assert.ok(c2.children[7].querySelector('span.rounded-full').classList.contains('bg-[var(--status-success)]') && c2.children[8].querySelector('span.rounded-full').classList.contains('bg-[var(--status-success)]'));
"""
        proc = subprocess.run(["node", "-e", node_script, str(base_dir / "static" / "js" / "app.js"), str(base_dir / "static" / "js" / "directory_ui.js")], capture_output=True, text=True, check=False)
        self.assertEqual(proc.returncode, 0, msg=proc.stderr or proc.stdout)

        tpl_src = (base_dir / "templates" / "panels" / "analyst_dashboard.html").read_text(encoding="utf-8")
        self.assertIn("analyst_evaluation.js' %}?v=17\"", tpl_src)
        self.assertNotIn("analyst_evaluation.js' %}?v=1\"", tpl_src)
        self.assertEqual(re.findall(r"analyst_evaluation\.js'\s*%\}\?v=(\d+)", tpl_src), ["17"])

        analyst_html = self._login_analyst().get(reverse("panels:analyst_dashboard")).content.decode("utf-8")
        self.assertIn("analyst_evaluation.js?v=17", analyst_html)
        self.assertNotIn('analyst_evaluation.js?v=1"', analyst_html)
        self.assertEqual(re.findall(r"analyst_evaluation\.js\?v=(\d+)", analyst_html), ["17"])

    def test_phase71_central_asset_version_and_mobile_data_card_id(self):
        base_dir = Path(settings.BASE_DIR)
        self.assertEqual(STATIC_ASSET_VERSION, "17")
        req = RequestFactory().get("/")
        req.session = {}
        ctx = global_context(req)
        self.assertEqual(ctx.get("asset_version"), STATIC_ASSET_VERSION)
        for rel in ("templates/base.html", "templates/accounts/auth.html", "templates/panels/analyst_dashboard.html"):
            src = (base_dir / rel).read_text(encoding="utf-8")
            versions = re.findall(r"%\}\?v=(\d+)", src)
            self.assertTrue(versions and all(v == STATIC_ASSET_VERSION for v in versions), rel)
        dt_src = (base_dir / "templates" / "components" / "data_table.html").read_text(encoding="utf-8")
        self.assertIn("data-card-id=", dt_src)
        analyst = self._login_analyst()
        self.assertEqual(analyst.post(reverse("analytics:stream_tick")).status_code, 200)
        analyst_html = analyst.get(reverse("panels:analyst_dashboard")).content.decode("utf-8")
        card_ids = re.findall(r'data-mobile-card[^>]*data-card-id="(STD-[^"]+)"', analyst_html)
        self.assertTrue(len(card_ids) > 0)
        node_script = r"""
const fs = require('fs'), vm = require('vm'), assert = require('assert');
class El {
  constructor(t, a = {}, tx = '') { this.tag = t.toLowerCase(); this.attrs = { ...a }; this.children = []; this._text = String(tx); this.parentNode = null; this.parentElement = null; this.dataset = {}; this.style = {}; const cls = new Set((a.class || '').split(/\s+/).filter(Boolean)); this.classList = { add: (...x) => x.forEach((c) => c && cls.add(c)), remove: (...x) => x.forEach((c) => cls.delete(c)), contains: (c) => cls.has(c), toggle: (c, f) => { const on = f === undefined ? !cls.has(c) : Boolean(f); on ? cls.add(c) : cls.delete(c); return on; } }; }
  append(...ns) { ns.forEach((n) => { n.parentNode = this; n.parentElement = this; this.children.push(n); }); } appendChild(n) { this.append(n); return n; } getAttribute(k) { return k in this.attrs ? String(this.attrs[k]) : null; } setAttribute(k, v) { this.attrs[k] = String(v); } removeAttribute(k) { delete this.attrs[k]; } hasAttribute(k) { return k in this.attrs; } addEventListener() {}
  get cells() { return this.children.filter((c) => c.tag === 'td' || c.tag === 'th'); } get textContent() { return this.children.length ? this.children.map((c) => c.textContent).join('') : this._text; } set textContent(v) { this.children = []; this._text = v == null ? '' : String(v); }
  closest(s) { for (let p = this; p; p = p.parentElement) if (s.trim().split(/\s+/).every((k) => mOne(p, k))) return p; return null; } querySelector(s) { return this.querySelectorAll(s)[0] || null; }
  querySelectorAll(s) { const ps = s.split(',').map((x) => x.trim()).filter(Boolean), out = [], seen = new Set(); const w = (n) => n.children.forEach((c) => { if (ps.some((p) => mDesc(c, p, this)) && !seen.has(c)) { seen.add(c); out.push(c); } w(c); }); w(this); return out; }
}
const mOne = (el, tok) => { const re = /:not\(([^)]+)\)/g; let m; while ((m = re.exec(tok))) if (mOne(el, m[1])) return false; const b = tok.replace(re, ''), tm = b.match(/^[a-z0-9-]+/i); if (tm && el.tag !== tm[0].toLowerCase()) return false; for (const cm of b.matchAll(/\.([a-z0-9_-]+)/gi)) if (!el.classList.contains(cm[1])) return false; for (const am of b.matchAll(/\[([a-z0-9_-]+)(?:="([^"]*)")?\]/gi)) if (!(am[1] in el.attrs) || (am[2] !== undefined && String(el.attrs[am[1]]) !== am[2])) return false; return true; };
const mDesc = (el, sel, root) => { const segs = sel.trim().split(/\s+/); if (!mOne(el, segs[segs.length - 1])) return false; let cur = el.parentElement; for (let i = segs.length - 2; i >= 0; i--) { while (cur && cur !== root && !mOne(cur, segs[i])) cur = cur.parentElement; if (!cur || (cur === root && !mOne(cur, segs[i]))) return false; cur = cur.parentElement; } return true; };
const root = new El('html'), body = new El('body'), box = new El('div', { 'data-paginated-container': '', 'data-page-size': '5' }), tbl = new El('table', { id: 'analyst-predictions-table' }), tbody = new El('tbody'); root.append(body);
const mkB = (t) => { const p = new El('span', { class: 'inline-flex' }); p.append(new El('span', { class: 'rounded-full bg-[var(--status-success)]' }), new El('span', {}, t)); return p; };
const mkR = (s, r, a, tip) => { const tr = new El('tr', { 'data-page-item': '' }); [s, 'N', '2026-A', 'CS-101', '88.0%', '3.20', '3.10'].forEach((v) => tr.append(new El('td', {}, v))); const rT = new El('td'), aT = new El('td'); rT.append(mkB(r)); aT.append(mkB(a)); tr.append(rT, aT, new El('td', {}, tip)); return tr; };
const mkC = (cid, hdrText, r, a, tip) => { const c = new El('div', { 'data-mobile-card': '', 'data-page-item': '', 'data-card-id': cid }); [hdrText, 'N', '2026-A', 'CS-101', '88.0%', '3.20', '3.10', { b: r }, { b: a }, tip].forEach((v) => { const rw = new El('div', { class: 'flex' }), bx = new El('div', { class: 'min-w-0 text-right' }); if (v && v.b) bx.append(mkB(v.b)); else bx.textContent = v; rw.append(new El('span', {}, 'L'), bx); c.append(rw); }); return c; };
const tr1 = mkR('STD-1', 'LOW (15%)', 'Normal', 'Steady'), tr2 = mkR('STD-2', 'LOW (10%)', 'Normal', 'On track');
const c1 = mkC('STD-1', 'STD-1 · VIP Badge', 'LOW (15%)', 'Normal', 'Steady'), c2 = mkC('STD-2', 'STD-2 · Honors', 'LOW (10%)', 'Normal', 'On track');
tbody.append(tr1, tr2); tbl.append(tbody); box.append(tbl, c2, c1); body.append(box);
const findId = (n, id) => { if (n.attrs.id === id) return n; for (const c of n.children) { const f = findId(c, id); if (f) return f; } return null; };
const doc = { readyState: 'complete', cookie: '', documentElement: root, body, createElement: (t) => new El(t), addEventListener: () => {}, getElementById: (id) => findId(root, id), querySelector: (s) => root.querySelector(s), querySelectorAll: (s) => root.querySelectorAll(s) };
const win = { innerWidth: 1280, addEventListener: () => {}, dispatchEvent: () => {}, setTimeout: () => 0, clearTimeout: () => {}, setInterval: () => 0, clearInterval: () => {}, requestAnimationFrame: (f) => f(), localStorage: { getItem: () => null, setItem: () => {} }, Event: function (t) { this.type = t; }, CustomEvent: function (t, d) { this.type = t; this.detail = d; }, document: doc }; win.window = win;
const ctx = vm.createContext({ ...win, window: win, document: doc, console }); vm.runInContext(fs.readFileSync(process.argv[1], 'utf8'), ctx); vm.runInContext(fs.readFileSync(process.argv[2], 'utf8'), ctx);
win.syncStreamPredictionTable([{ student_id: 'STD-1', attendance_pct: 61.5, predicted_gpa: 2.35, risk_level: 'HIGH', risk_text: 'HIGH (88%)', is_anomaly: true, tip: 'Urgent lab check' }]);
[4, 6, 7, 8, 9].forEach((k, i) => {
  const exp1 = ['61.5%', '2.35', 'HIGH (88%)', 'Flagged', 'Urgent lab check'][i];
  const exp2 = ['88.0%', '3.10', 'LOW (10%)', 'Normal', 'On track'][i];
  assert.strictEqual(tr1.cells[k].textContent, exp1);
  assert.strictEqual(c1.children[k].querySelector('div.text-right').textContent, exp1);
  assert.strictEqual(c2.children[k].querySelector('div.text-right').textContent, exp2);
});
"""
        proc = subprocess.run(["node", "-e", node_script, str(base_dir / "static" / "js" / "app.js"), str(base_dir / "static" / "js" / "directory_ui.js")], capture_output=True, text=True, check=False)
        self.assertEqual(proc.returncode, 0, msg=proc.stderr or proc.stdout)

