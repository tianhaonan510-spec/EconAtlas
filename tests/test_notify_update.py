import unittest

from scripts.notify_update import render_message


class NotifyUpdateTests(unittest.TestCase):
    def test_render_message_contains_result_and_summary(self):
        title, body = render_message(
            {
                "status": "success",
                "started_at": "2026-08-13 09:00:00",
                "finished_at": "2026-08-13 09:05:00",
                "duration_seconds": 300,
                "message": "Data update completed successfully.",
                "data_summary": {"row_count": 65578, "indicator_count": 64, "country_count": 18},
            },
            "owner/econatlas",
            "https://github.com/owner/econatlas/actions/runs/1",
        )
        self.assertIn("SUCCESS", title)
        self.assertIn("65578", body)
        self.assertIn("64 项指标", body)
        self.assertIn("actions/runs/1", body)


if __name__ == "__main__":
    unittest.main()
