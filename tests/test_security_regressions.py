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


if __name__ == "__main__":
    unittest.main()
