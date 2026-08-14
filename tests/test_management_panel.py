import unittest

from api_service.app import (
    ReportRequest,
    alignment_candidates,
    asset_ratings,
    dashboard_summary,
    generate_report,
    lineage,
    quality_status,
    report_pdf,
    risk_alerts,
)
from api_service.panel import PANEL_HTML
from services.query_service import build_query_response


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

    def test_pdf_report_is_downloadable(self):
        response = report_pdf(country="CN", indicator="CPI_YOY_M")
        self.assertEqual(response.media_type, "application/pdf")
        self.assertTrue(response.body.startswith(b"%PDF"))
        self.assertIn("attachment", response.headers["content-disposition"])

    def test_default_json_query_excludes_forecast(self):
        current = build_query_response("AR", "CPI_YOY_A")
        explicit = build_query_response("AR", "CPI_YOY_A", include_forecast=True)
        current_series = current["series"] if isinstance(current["series"], list) else [current["series"]]
        explicit_series = explicit["series"] if isinstance(explicit["series"], list) else [explicit["series"]]
        current_years = [int(str(row["date"])[:4]) for series in current_series for row in series["observations"]]
        explicit_years = [int(str(row["date"])[:4]) for series in explicit_series for row in series["observations"]]
        self.assertLessEqual(max(current_years), 2026)
        self.assertGreater(max(explicit_years), 2026)

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

    def test_all_original_competition_modules_are_preserved(self):
        modules = [
            "指标查询", "指标字典", "数据质量", "JSON输出", "一致性分析", "治理驾驶舱",
            "指标血缘", "治理规则", "API服务中心", "数据资产目录", "风险预警", "智能问答",
            "智能分析", "智能报告", "资产评级", "指标对齐审核",
        ]
        for module in modules:
            with self.subTest(module=module):
                self.assertIn(module, PANEL_HTML)
        self.assertIn("'json-output':jsonOutput", PANEL_HTML)
        self.assertIn("'indicator-query':indicatorQuery", PANEL_HTML)

    def test_restored_governance_data_sources_exist(self):
        self.assertGreater(lineage()["count"], 0)
        self.assertGreater(alignment_candidates()["count"], 0)
        self.assertGreater(asset_ratings()["count"], 0)

    def test_quality_scope_excludes_forecasts(self):
        quality = quality_status()
        self.assertEqual(quality["scope"], "released_data")
        self.assertGreater(quality["forecast_rows_excluded"], 0)
        self.assertTrue(all(int(str(row["date"])[:4]) <= 2026 for row in quality["outliers"] if row.get("date")))


if __name__ == "__main__":
    unittest.main()
