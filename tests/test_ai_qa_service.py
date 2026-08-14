import unittest

import pandas as pd

from services.ai_qa_service import build_messages, prepare_evidence, resolve_query_intent


class AIQAServiceTests(unittest.TestCase):
    def setUp(self):
        self.catalog = pd.DataFrame({
            "country_code": ["CN", "CN", "US"],
            "indicator_code": ["CPI_YOY_M", "GDP_REAL_GROWTH_YOY_A", "CPI_YOY_M"],
            "indicator_name_zh": ["居民消费价格指数同比", "实际GDP增速", "居民消费价格指数同比"],
            "indicator_name_en": ["Consumer Price Index YoY", "Real GDP Growth", "Consumer Price Index YoY"],
        })

    def test_resolves_natural_language_and_relative_years(self):
        intent = resolve_query_intent("分析中国近五年通胀趋势", self.catalog, current_year=2026)
        self.assertEqual(intent, {"country": "CN", "indicator": "CPI_YOY_M", "start_year": 2022, "end_year": 2026})

    def test_follow_up_reuses_previous_context(self):
        previous = {"country": "CN", "indicator": "GDP_REAL_GROWTH_YOY_A", "start_year": 2020, "end_year": 2026}
        intent = resolve_query_intent("为什么会这样？", self.catalog, previous, current_year=2026)
        self.assertEqual(intent["indicator"], "GDP_REAL_GROWTH_YOY_A")

    def test_evidence_is_limited_and_traceable(self):
        data = pd.DataFrame(
            {
                "date": [f"2024-{month:02d}" for month in range(1, 13)],
                "value": range(12),
                "unit": ["%"] * 12,
                "frequency": ["M"] * 12,
                "observation_type": ["historical"] * 12,
                "source_organization": ["Official"] * 12,
                "source_dataset": ["Dataset"] * 12,
                "source_url": ["https://example.com"] * 12,
            }
        )
        evidence, text = prepare_evidence(data, max_rows=5)
        self.assertEqual(len(evidence), 5)
        self.assertIn("[E1]", text)
        self.assertIn("来源=Official / Dataset", text)

    def test_prompt_forbids_ungrounded_values(self):
        messages = build_messages("最近趋势如何？", "中国", "居民消费价格", "[E1] 日期=2024；数值=1.0 %")
        self.assertIn("只能依据", messages[0]["content"])
        self.assertIn("[E1]", messages[1]["content"])


if __name__ == "__main__":
    unittest.main()
