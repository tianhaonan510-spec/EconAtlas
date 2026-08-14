"""Lightweight SDMX-style semantic model and alignment constraints.

The project deliberately keeps this module dependency-light so that the same
rules run in GitHub Actions, the local collector and the 512 MB Render service.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import re
from typing import Any


FREQUENCY_ORDER = {"D": 1, "W": 2, "M": 3, "Q": 4, "A": 5}


def _text(*values: Any) -> str:
    return " ".join(str(value or "") for value in values).lower()


def normalize_unit(value: Any) -> str:
    unit = re.sub(r"\s+", " ", str(value or "").strip().lower())
    aliases = {
        "percent": "%", "percentage": "%", "pct": "%",
        "usd": "current usd", "us dollars": "current usd",
        "people": "persons", "person": "persons",
    }
    return aliases.get(unit, unit)


def unit_family(value: Any) -> str:
    unit = normalize_unit(value)
    if "% of gdp" in unit:
        return "ratio_gdp"
    if "%" in unit or "percent" in unit:
        return "percent"
    if "index" in unit:
        return "index"
    if "currency per" in unit or "per eur" in unit or "per usd" in unit:
        return "exchange_rate"
    if "usd" in unit or "lcu" in unit or "dollar" in unit or "cny" in unit:
        return "currency"
    if "person" in unit or "population" in unit:
        return "persons"
    if "year" in unit:
        return "years"
    if "kwh" in unit or "oil equivalent" in unit:
        return "physical"
    return unit or "unknown"


def infer_domain(code: str, name_zh: str = "", name_en: str = "") -> str:
    text = _text(code, name_zh, name_en)
    rules = [
        ("national_accounts", ("gdp", "gni", "capital formation", "savings")),
        ("prices", ("cpi", "ppi", "deflator", "price", "inflation")),
        ("labour", ("unemployment", "payroll", "employment", "labor", "labour")),
        ("external_sector", ("export", "import", "trade", "current account", "reserve", "exchange rate")),
        ("fiscal", ("government", "gov_", "tax", "military expenditure", "debt")),
        ("money_finance", ("money", "credit", "fed funds", "treasury", "financing")),
        ("industry_consumption", ("industrial", "retail", "pmi", "housing")),
        ("population_social", ("population", "life expectancy", "school", "internet")),
        ("energy", ("energy", "electric")),
        ("investment", ("fdi", "fixed asset investment")),
    ]
    return next((domain for domain, words in rules if any(word in text for word in words)), "other")


def infer_concept(code: str, name_zh: str = "", name_en: str = "") -> str:
    upper = str(code or "").upper()
    concepts = [
        "GDP", "GNI", "CPI", "PPI", "UNEMPLOYMENT", "EXPORTS", "IMPORTS",
        "EXCHANGE_RATE", "POPULATION", "INDUSTRIAL_OUTPUT", "INDUSTRIAL_PRODUCTION",
        "RETAIL_SALES", "M1", "M2", "PMI", "CURRENT_ACCOUNT", "GOV_DEBT",
    ]
    for concept in concepts:
        if concept in upper:
            return concept.lower()
    words = [word for word in re.split(r"[^A-Z0-9]+", upper) if word and word not in {"A", "Q", "M", "D", "YOY", "USD", "CURRENT", "REAL", "CN", "US"}]
    return "_".join(words[:3]).lower() or "unspecified"


def infer_measure(calculation: Any, unit: Any, code: str = "") -> str:
    calc = str(calculation or "").lower()
    upper = str(code or "").upper()
    if "ytd" in calc or "YTD" in upper:
        return "ytd_growth"
    if "yoy" in calc or "YOY" in upper:
        return "year_on_year_growth"
    if "average" in calc:
        return "period_average"
    if calc == "flow" or upper.endswith("FLOW_M"):
        return "flow"
    if unit_family(unit) in {"ratio_gdp", "percent"} and "rate" in upper.lower():
        return "rate"
    return "level"


def infer_price_basis(unit: Any, code: str = "", name_en: str = "") -> str:
    text = _text(unit, code, name_en)
    if "constant" in text or "real" in text:
        return "constant_price"
    if "current" in text or "nominal" in text:
        return "current_price"
    return "not_applicable"


def infer_stock_flow(calculation: Any, code: str = "", name_en: str = "") -> str:
    text = _text(calculation, code, name_en)
    if "flow" in text or "export" in text or "import" in text or "revenue" in text or "expense" in text:
        return "flow"
    if "stock" in text or "reserve" in text or "debt" in text or "population" in text or "money" in text:
        return "stock"
    return "not_specified"


def infer_currency(unit: Any) -> str:
    upper = str(unit or "").upper()
    for code in ("USD", "EUR", "CNY", "LCU"):
        if code in upper:
            return code
    return "NA"


def semantic_dimensions(code: str, name_zh: str, name_en: str, unit: Any, frequency: Any,
                        seasonal_adjustment: Any, calculation: Any) -> dict[str, str]:
    return {
        "domain": infer_domain(code, name_zh, name_en),
        "concept": infer_concept(code, name_zh, name_en),
        "measure": infer_measure(calculation, unit, code),
        "unit_family": unit_family(unit),
        "price_basis": infer_price_basis(unit, code, name_en),
        "stock_flow": infer_stock_flow(calculation, code, name_en),
        "currency": infer_currency(unit),
        "frequency_code": str(frequency or "").upper(),
        "seasonal_adjustment_code": str(seasonal_adjustment or "").upper(),
        "calculation_code": str(calculation or ""),
    }


def semantic_signature(dimensions: dict[str, Any]) -> str:
    keys = ("domain", "concept", "measure", "unit_family", "price_basis", "stock_flow", "currency", "frequency_code", "seasonal_adjustment_code")
    return "|".join(str(dimensions.get(key, "")) for key in keys)


def _compatible_frequency(source: Any, target: Any) -> bool:
    source, target = str(source or "").upper(), str(target or "").upper()
    return not source or not target or source == target


def _compatible_seasonal(source: Any, target: Any) -> bool:
    source, target = str(source or "").upper(), str(target or "").upper()
    return not source or not target or source == target or "NA" in {source, target}


def _compatible_measure(source: Any, target: Any) -> bool:
    source, target = str(source or "").lower(), str(target or "").lower()
    return not source or not target or source == target


@dataclass(frozen=True)
class ConstraintResult:
    passed: bool
    violations: tuple[str, ...]


def hard_constraints(source: dict[str, Any], target: dict[str, Any]) -> ConstraintResult:
    violations: list[str] = []
    source_family, target_family = unit_family(source.get("unit")), unit_family(target.get("unit"))
    if source_family != "unknown" and target_family != "unknown" and source_family != target_family:
        violations.append(f"单位族不兼容:{source_family}!={target_family}")
    if not _compatible_frequency(source.get("frequency"), target.get("frequency")):
        violations.append(f"频率不一致:{source.get('frequency')}!={target.get('frequency')}")
    if not _compatible_measure(source.get("measure"), target.get("measure")):
        violations.append(f"计算口径不一致:{source.get('measure')}!={target.get('measure')}")
    if not _compatible_seasonal(source.get("seasonal_adjustment"), target.get("seasonal_adjustment")):
        violations.append(f"季调口径不一致:{source.get('seasonal_adjustment')}!={target.get('seasonal_adjustment')}")
    return ConstraintResult(not violations, tuple(violations))


def bounded_score(value: Any, fallback: float = 0.0) -> float:
    try:
        number = float(value)
        if math.isnan(number):
            return fallback
        return max(0.0, min(1.0, number))
    except (TypeError, ValueError):
        return fallback

