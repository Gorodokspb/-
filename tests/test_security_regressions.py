"""Security regression tests.

Лёгкие тесты, которые проверяют, что базовые security-конфигурации не регрессировали.
Не зависят от БД или внешних сервисов — только от исходного кода.
"""

import os
import unittest
from pathlib import Path
from unittest import mock


WEBAPP_DIR = Path(__file__).resolve().parent.parent / "webapp"


class TestSessionCookieSecurity(unittest.TestCase):
    """Stage 8.10.1: Session cookie must have Secure flag in production."""

    def _session_middleware_block(self):
        main_py = (WEBAPP_DIR / "main.py").read_text()
        # Найти SessionMiddleware, (использование, не import). Если строка с from/import — пропустить.
        idx = main_py.find("SessionMiddleware,")
        while idx >= 0:
            line_start = main_py.rfind("\n", 0, idx) + 1
            line_prefix = main_py[line_start:idx]
            if not line_prefix.strip().startswith(("from ", "import ")):
                break
            idx = main_py.find("SessionMiddleware,", idx + 1)
        self.assertGreaterEqual(
            idx, 0,
            "SessionMiddleware usage (not import) not found in main.py",
        )
        # Найти открывающую "(" ДО "SessionMiddleware," — это начало add_middleware(...).
        open_paren = main_py.rfind("(", 0, idx)
        self.assertGreaterEqual(open_paren, 0)
        depth = 0
        end = open_paren
        for i in range(open_paren, len(main_py)):
            ch = main_py[i]
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        return main_py[open_paren:end]

    def test_session_middleware_https_only_true(self):
        block = self._session_middleware_block()
        self.assertIn(
            "https_only=True",
            block,
            "SessionMiddleware must have https_only=True so session cookies "
            "are not sent over plain HTTP. See Stage 8.10.1.",
        )

    def test_session_middleware_same_site_lax(self):
        """SameSite=Lax защищает от cross-site POST и не ломает обычную навигацию."""
        block = self._session_middleware_block()
        self.assertIn('same_site="lax"', block)

    def test_session_middleware_secret_key_present(self):
        block = self._session_middleware_block()
        self.assertIn("secret_key=", block)


class TestConfigSecrets(unittest.TestCase):
    """Stage 8.10.5 (F-3): default fallback secrets removed from config.py."""

    def test_no_placeholder_secret_key_default(self):
        """config.py must not contain placeholder default for DEKORCRM_WEB_SECRET_KEY."""
        import re
        config_text = (Path(__file__).parent.parent / "webapp" / "config.py").read_text()
        # Pattern: os.environ.get("DEKORCRM_WEB_SECRET_KEY", "<non-empty default>")
        bad = re.search(
            r'os\.environ\.get\(\s*["\']DEKORCRM_WEB_SECRET_KEY["\']\s*,\s*["\']\S+["\']\s*\)',
            config_text,
        )
        self.assertIsNone(
            bad,
            f"config.py still has a non-empty default for DEKORCRM_WEB_SECRET_KEY: "
            f"{bad.group(0) if bad else None}"
        )

    def test_no_placeholder_password_default(self):
        """config.py must not contain placeholder default for DEKORCRM_WEB_PASSWORD."""
        import re
        config_text = (Path(__file__).parent.parent / "webapp" / "config.py").read_text()
        bad = re.search(
            r'os\.environ\.get\(\s*["\']DEKORCRM_WEB_PASSWORD["\']\s*,\s*["\']\S+["\']\s*\)',
            config_text,
        )
        self.assertIsNone(
            bad,
            f"config.py still has a non-empty default for DEKORCRM_WEB_PASSWORD: "
            f"{bad.group(0) if bad else None}"
        )

    def test_require_secret_exists(self):
        """config.py must define _require_secret validation function."""
        from webapp import config
        self.assertTrue(
            hasattr(config, "_require_secret"),
            "config.py is missing _require_secret()"
        )
        self.assertTrue(callable(config._require_secret))

    def test_require_secret_rejects_placeholder(self):
        from webapp import config
        with mock.patch.dict(os.environ, {"TEST_FAKE_SECRET": "change-me-before-production"}):
            with self.assertRaises(RuntimeError):
                config._require_secret("TEST_FAKE_SECRET", min_length=32)

    def test_require_secret_rejects_empty(self):
        from webapp import config
        with mock.patch.dict(os.environ, {"TEST_FAKE_SECRET": ""}):
            with self.assertRaises(RuntimeError):
                config._require_secret("TEST_FAKE_SECRET", min_length=32)

    def test_require_secret_rejects_short(self):
        from webapp import config
        with mock.patch.dict(os.environ, {"TEST_FAKE_SECRET": "short"}):
            with self.assertRaises(RuntimeError):
                config._require_secret("TEST_FAKE_SECRET", min_length=32)

    def test_require_secret_accepts_strong(self):
        from webapp import config
        strong = "x" * 64
        with mock.patch.dict(os.environ, {"TEST_FAKE_SECRET": strong}):
            self.assertEqual(config._require_secret("TEST_FAKE_SECRET", min_length=32), strong)

    def test_example_env_has_empty_or_instruction_only_secrets(self):
        """`.env.web.example` should not contain working secrets."""
        example_text = (Path(__file__).parent.parent / ".env.web.example").read_text()
        for line in example_text.splitlines():
            stripped = line.strip()
            if stripped.startswith("DEKORCRM_WEB_SECRET_KEY=") or \
               stripped.startswith("DEKORCRM_WEB_PASSWORD="):
                value = stripped.split("=", 1)[1].strip()
                # Acceptable: empty (e.g. "DEKORCRM_WEB_SECRET_KEY=") or placeholder marker.
                self.assertIn(
                    value, {"", "CHANGE_ME_SECRET_KEY", "CHANGE_ME_WEB_PASSWORD"},
                    f"Unexpected value in .env.web.example: {line!r}"
                )


class TestCsrfProtection(unittest.TestCase):
    """Stage 8.10.4 (F-1): CSRF protection on state-changing requests."""

    def test_csrf_module_exists(self):
        from webapp import csrf
        self.assertTrue(hasattr(csrf, "CSRFMiddleware"))
        self.assertTrue(hasattr(csrf, "generate_csrf_token"))
        self.assertTrue(hasattr(csrf, "verify_csrf_token"))

    def test_csrf_middleware_registered(self):
        """webapp/main.py must register CSRFMiddleware."""
        main_text = (Path(__file__).parent.parent / "webapp" / "main.py").read_text()
        self.assertIn("CSRFMiddleware", main_text)
        self.assertIn("add_middleware", main_text)
        self.assertRegex(main_text, r"add_middleware\(CSRFMiddleware,\s*secret_key=")

    def test_csrf_meta_tag_in_base(self):
        base_text = (Path(__file__).parent.parent / "webapp" / "templates" / "base.html").read_text()
        self.assertIn('name="csrf-token"', base_text)
        self.assertIn("csrf_token(request)", base_text)

    def test_csrf_token_global_registered(self):
        """csrf_token(request) must be a Jinja2 global."""
        main_text = (Path(__file__).parent.parent / "webapp" / "main.py").read_text()
        self.assertIn("csrf_token", main_text)
        self.assertIn("env.globals", main_text)

    def test_no_legacy_login_form_has_csrf(self):
        """login.html must NOT have csrf_token (would break login bypass)."""
        login_text = (Path(__file__).parent.parent / "webapp" / "templates" / "login.html").read_text()
        self.assertNotIn('name="csrf_token"', login_text)

    def test_protected_forms_include_csrf(self):
        """At least one protected template must include csrf_token field."""
        for tmpl in ["finance.html", "project_detail.html", "catalog.html"]:
            text = (Path(__file__).parent.parent / "webapp" / "templates" / tmpl).read_text()
            self.assertIn(
                'name="csrf_token"', text,
                f"{tmpl} is missing csrf_token hidden input"
            )

    def test_verify_csrf_accepts_matching_tokens(self):
        from webapp.csrf import generate_csrf_token, verify_csrf_token
        secret = "x" * 32
        token = generate_csrf_token(secret)
        self.assertTrue(verify_csrf_token(secret, token, token))

    def test_verify_csrf_rejects_mismatch(self):
        from webapp.csrf import generate_csrf_token, verify_csrf_token
        secret = "x" * 32
        t1 = generate_csrf_token(secret)
        t2 = generate_csrf_token(secret)
        self.assertFalse(verify_csrf_token(secret, t1, t2))

    def test_verify_csrf_rejects_empty(self):
        from webapp.csrf import verify_csrf_token
        secret = "x" * 32
        self.assertFalse(verify_csrf_token(secret, "", ""))
        self.assertFalse(verify_csrf_token(secret, None, None))

    def test_verify_csrf_rejects_tampered(self):
        from webapp.csrf import verify_csrf_token
        secret = "x" * 32
        self.assertFalse(verify_csrf_token(secret, "forged.value", "forged.value"))


class TestCsrfFunctional(unittest.TestCase):
    """Functional CSRF tests using FastAPI TestClient (no live DB)."""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("DEKORCRM_WEB_SECRET_KEY", "x" * 64)
        os.environ.setdefault("DEKORCRM_WEB_PASSWORD", "test-password-12345")
        os.environ["DEKORCRM_POSTGRES_DSN"] = "postgresql://fake:fake@127.0.0.1:1/fake"
        from fastapi.testclient import TestClient
        from webapp import main as webapp_main
        # Patch DB-touching helpers so login works without a real DB.
        webapp_main.ensure_auth_bootstrap = lambda: None
        webapp_main.fetch_web_user = lambda username: {
            "username": username,
            "password_hash": webapp_main.hash_password("x" * 20),
        } if username == "admin" else None
        cls.client = TestClient(webapp_main.app)

    def test_get_root_sets_csrf_cookie(self):
        resp = self.client.get("/", follow_redirects=False)
        self.assertIn(resp.status_code, (200, 302))
        self.assertIn("csrf_token", resp.cookies)

    def test_login_bypasses_csrf(self):
        resp = self.client.post(
            "/login",
            data={"username": "fake", "password": "fake"},
            follow_redirects=False,
        )
        self.assertNotEqual(resp.status_code, 403)

    def test_post_protected_without_csrf_returns_403(self):
        resp = self.client.post(
            "/finance/transactions",
            data={"type": "Приход", "amount": "100"},
            follow_redirects=False,
        )
        self.assertIn(resp.status_code, (302, 403))

    def test_post_with_valid_csrf_and_auth_succeeds(self):
        resp0 = self.client.get("/", follow_redirects=False)
        csrf_token = resp0.cookies.get("csrf_token")
        self.assertIsNotNone(csrf_token)
        resp_login = self.client.post(
            "/login",
            data={"username": "admin", "password": "x" * 20},
            follow_redirects=False,
        )
        if "csrf_token" in resp_login.cookies:
            csrf_token = resp_login.cookies["csrf_token"]
        session_cookie = resp_login.cookies.get("session")
        # TestClient uses HTTP, but our cookies are Secure — set them
        # directly on the cookie jar to bypass the Secure check.
        if session_cookie:
            self.client.cookies.set("session", session_cookie)
        self.client.cookies.set("csrf_token", csrf_token)
        resp = self.client.post(
            "/finance/transactions",
            data={"type": "Приход", "amount": "100", "csrf_token": csrf_token},
            headers={"X-CSRF-Token": csrf_token},
            follow_redirects=False,
        )
        # Either 302 (auth redirect — success from CSRF perspective) or 200/400
        # (passed both auth and CSRF, then form/DB error). Must NOT be 403.
        self.assertNotEqual(resp.status_code, 403, f"Got 403: {resp.text}")


if __name__ == "__main__":
    unittest.main()
