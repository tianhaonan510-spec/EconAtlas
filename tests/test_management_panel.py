import unittest

from api_service.app import ReportRequest, dashboard_summary, generate_report, risk_alerts
from api_service.panel import PANEL_HTML


class ManagementPanelTests(unittest.TestCase):
    def test_current_summary_excludes_forecast_scenarios(self):
        summary = dashboard_summary()
        self.assertNotIn("forecasts", summary["totals"])
        self.assertGreater(summary["forecast_scenario"]["rows"], 0)
        self.assertLessEqual(int(str(summary["totals"]["latest_date"])[:4]), 2026)

    def test_report_uses_only_released_data(self):
        report = generate_report(ReportRequest(country="CN", indicator="CPI_YOY_M"))
        self.assertNotIn("error", report)
        self.assertTrue(report["forecast_excluded"])
        self.assertTrue(all(row["observation_type"] != "forecast" for row in report["series"]))

    def test_risk_page_uses_report_data(self):
        risk = risk_alerts()
        self.assertIn("quality_warnings", risk)
        self.assertIn("outlier_count", risk)

    def test_chat_has_no_secondary_conversation_sidebar(self):
        self.assertNotIn("chat-side", PANEL_HTML)
        self.assertNotIn("搜索会话标题", PANEL_HTML)

    def test_original_showcase_logo_shape_is_restored(self):
        self.assertIn("EconAtlas 原版标志", PANEL_HTML)
        self.assertIn("clip-path:polygon", PANEL_HTML)


if __name__ == "__main__":
    unittest.main()
