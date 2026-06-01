"""Security regression tests.

Лёгкие тесты, которые проверяют, что базовые security-конфигурации не регрессировали.
Не зависят от БД или внешних сервисов — только от исходного кода.
"""

import unittest
from pathlib import Path


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


if __name__ == "__main__":
    unittest.main()
