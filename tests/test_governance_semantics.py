from __future__ import annotations

import unittest

from governance.semantic_model import hard_constraints, semantic_dimensions, semantic_signature


class GovernanceSemanticTests(unittest.TestCase):
    def test_semantic_signature_contains_governance_dimensions(self):
        dimensions = semantic_dimensions(
            "CPI_YOY_M", "居民消费价格指数同比", "Consumer price inflation",
            "%", "M", "NSA", "YoY",
        )
        self.assertEqual(dimensions["domain"], "prices")
        self.assertEqual(dimensions["measure"], "year_on_year_growth")
        self.assertIn("prices|cpi|year_on_year_growth|percent", semantic_signature(dimensions))

    def test_hard_constraints_reject_incompatible_frequency_or_unit(self):
        source = {"unit": "%", "frequency": "M", "measure": "year_on_year_growth", "seasonal_adjustment": "NSA"}
        target = {"unit": "current USD", "frequency": "A", "measure": "level", "seasonal_adjustment": "NSA"}
        result = hard_constraints(source, target)
        self.assertFalse(result.passed)
        self.assertGreaterEqual(len(result.violations), 3)

    def test_hard_constraints_accept_exact_semantics(self):
        item = {"unit": "%", "frequency": "M", "measure": "year_on_year_growth", "seasonal_adjustment": "NSA"}
        self.assertTrue(hard_constraints(item, item).passed)


if __name__ == "__main__":
    unittest.main()
