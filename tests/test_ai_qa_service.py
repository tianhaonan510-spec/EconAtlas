import unittest

import pandas as pd

from services.ai_qa_service import build_messages, prepare_evidence


class AIQAServiceTests(unittest.TestCase):
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
