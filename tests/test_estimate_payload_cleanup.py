import unittest

from webapp.db import _normalize_editor_rows, _payload_item_to_editor_row


class EstimatePayloadCleanupTests(unittest.TestCase):
    def test_broken_compatrow_payload_item_is_dropped_from_editor_rows(self):
        broken_item = {
            "values": [
                "22,",
                "'name':",
                "10",
                "",
                "",
                "",
                "CompatRow({'id':",
            ],
            "tags": [],
        }

        editor_rows = _normalize_editor_rows([
            _payload_item_to_editor_row(broken_item, 0.0),
        ], 0.0)

        self.assertEqual(editor_rows, [])


if __name__ == "__main__":
    unittest.main()
