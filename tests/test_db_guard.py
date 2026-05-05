import unittest
from unittest.mock import patch, MagicMock

from tests.db_guard import guard_live_database, is_live_database, FORBIDDEN_DATABASES


class DatabaseGuardTests(unittest.TestCase):
    def test_guard_raises_on_live_database(self):
        with patch("tests.db_guard._current_database", return_value="dekorcrm"):
            with self.assertRaises(RuntimeError) as cm:
                guard_live_database()
            self.assertIn("Refusing to run destructive tests", str(cm.exception))
            self.assertIn("dekorcrm", str(cm.exception))

    def test_guard_allows_test_database(self):
        with patch("tests.db_guard._current_database", return_value="dekorcrm_test"):
            try:
                guard_live_database()
            except RuntimeError:
                self.fail("guard_live_database() raised on non-live database")

    def test_guard_case_insensitive(self):
        with patch("tests.db_guard._current_database", return_value="DekorCRM"):
            with self.assertRaises(RuntimeError):
                guard_live_database()

    def test_is_live_database_true_on_live(self):
        with patch("tests.db_guard._current_database", return_value="dekorcrm"):
            self.assertTrue(is_live_database())

    def test_is_live_database_false_on_test(self):
        with patch("tests.db_guard._current_database", return_value="dekorcrm_test"):
            self.assertFalse(is_live_database())

    def test_forbidden_databases_contains_dekorcrm(self):
        self.assertIn("dekorcrm", FORBIDDEN_DATABASES)


if __name__ == "__main__":
    unittest.main()