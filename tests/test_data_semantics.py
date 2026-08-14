from __future__ import annotations

import unittest

import pandas as pd

from main_collect import apply_observation_semantics


class ObservationSemanticsTests(unittest.TestCase):
    def test_empty_rows_are_removed_and_source_status_is_preserved(self):
        frame = pd.DataFrame(
            [
                {"date": "2024", "value": "1.5", "source_organization": "World Bank", "status": "final"},
                {"date": "2024", "value": None, "source_organization": "World Bank", "status": "final"},
            ]
        )
        result = apply_observation_semantics(frame)
        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]["source_status"], "final")
        self.assertEqual(result.iloc[0]["observation_type"], "historical")

    def test_imf_future_values_are_forecasts(self):
        future_year = pd.Timestamp.now().year + 1
        frame = pd.DataFrame(
            [{"date": str(future_year), "value": 2.0, "source_organization": "IMF", "status": "official"}]
        )
        result = apply_observation_semantics(frame)
        self.assertEqual(result.iloc[0]["observation_type"], "forecast")
        self.assertEqual(result.iloc[0]["processing_level"], "standardized")

    def test_derived_values_are_explicit(self):
        frame = pd.DataFrame(
            [{"date": "2024", "value": 2.0, "source_organization": "FRED", "status": "derived_aligned"}]
        )
        result = apply_observation_semantics(frame)
        self.assertEqual(result.iloc[0]["observation_type"], "derived")

    def test_sdmx_normal_and_break_flags_are_not_mislabeled_as_estimates(self):
        frame = pd.DataFrame([{"date": "2024", "value": 1.0, "source_organization": "BIS", "status": "A", "source_status": "A"}])
        result = apply_observation_semantics(frame)
        self.assertEqual(result.iloc[0]["source_status"], "A")
        self.assertEqual(result.iloc[0]["release_status"], "final")

        frame = pd.DataFrame([{"date": "2024", "value": 1.0, "source_organization": "BIS", "status": "B", "source_status": "B"}])
        result = apply_observation_semantics(frame)
        self.assertEqual(result.iloc[0]["release_status"], "final")

    def test_any_future_value_is_separated_as_forecast(self):
        frame = pd.DataFrame([{"date": "2099", "value": 1.0, "source_organization": "BIS", "status": "A", "source_status": "A"}])
        result = apply_observation_semantics(frame)
        self.assertEqual(result.iloc[0]["observation_type"], "forecast")
        self.assertEqual(result.iloc[0]["processing_level"], "standardized")


if __name__ == "__main__":
    unittest.main()
