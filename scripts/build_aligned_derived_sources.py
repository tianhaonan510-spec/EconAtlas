# -*- coding: utf-8 -*-
"""Build aligned observations for cross-source indicator comparison.

The rows generated here are based on already collected official/API source
series. They make common macro indicators comparable by applying transparent
frequency or unit transformations such as YoY growth, annual averages and
exchange-rate inversion.
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd

from config import COUNTRIES, DATA_RAW

OUT_FILE = DATA_RAW / "aligned_derived_raw.csv"

BASE_COLUMNS = [
    "series_id",
    "country_code",
    "country_iso2",
    "country_iso3",
    "country_name_zh",
    "country_name_en",
    "indicator_code",
    "indicator_name_zh",
    "indicator_name_en",
    "date",
    "frequency",
    "unit",
    "seasonal_adjustment",
    "calculation",
    "value",
    "source_organization",
    "source_dataset",
    "source_indicator_code",
    "source_indicator_name",
    "source_url",
    "last_updated",
    "status",
    "retrieved_at",
    "data_version",
]


def _country(code: str) -> dict:
    return COUNTRIES[code]


def _base_row(country_code: str, indicator_code: str, source: str) -> dict:
    country = _country(country_code)
    now = datetime.now()
    return {
        "series_id": f"{country_code}.{indicator_code}.{source}.ALIGNED",
        "country_code": country_code,
        "country_iso2": country["iso2"],
        "country_iso3": country["iso3"],
        "country_name_zh": country["zh"],
        "country_name_en": country["en"],
        "indicator_code": indicator_code,
        "last_updated": now.strftime("%Y-%m-%d"),
        "status": "derived_aligned",
        "retrieved_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "data_version": now.strftime("%Y-%m-%d"),
    }


def _read_raw(name: str) -> pd.DataFrame:
    path = DATA_RAW / name
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, encoding="utf-8-sig", low_memory=False)


def _append_row(rows: list[dict], row: dict) -> None:
    value = pd.to_numeric(row.get("value"), errors="coerce")
    if pd.isna(value):
        return
    row["value"] = float(value)
    rows.append(row)


def _fred_monthly_index_to_yoy(
    source_indicator: str,
    source_series_code: str,
    target_indicator: str,
    zh: str,
    en: str,
    source_indicator_name: str,
    seasonal_adjustment: str,
) -> list[dict]:
    df = _read_raw("fred_raw.csv")
    if df.empty:
        return []
    df = df[(df["country_code"] == "US") & (df["indicator_code"] == source_indicator)].copy()
    if df.empty:
        return []

    df["date_dt"] = pd.to_datetime(df["date"] + "-01", errors="coerce")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.sort_values("date_dt")
    df["yoy"] = df["value"].pct_change(periods=12, fill_method=None) * 100
    df = df[df["yoy"].notna()].copy()

    rows = []
    for _, item in df.iterrows():
        row = _base_row("US", target_indicator, "FRED")
        row.update(
            {
                "indicator_name_zh": zh,
                "indicator_name_en": en,
                "date": item["date"],
                "frequency": "M",
                "unit": "%",
                "seasonal_adjustment": seasonal_adjustment,
                "calculation": "YoY",
                "value": item["yoy"],
                "source_organization": "FRED",
                "source_dataset": f"Federal Reserve Economic Data (derived from {source_series_code})",
                "source_indicator_code": f"{source_series_code}.YOY",
                "source_indicator_name": source_indicator_name,
                "source_url": f"https://fred.stlouisfed.org/series/{source_series_code}",
            }
        )
        _append_row(rows, row)
    return rows


def _fred_monthly_to_annual(
    source_indicator: str,
    source_series_code: str,
    target_indicator: str,
    zh: str,
    en: str,
    unit: str = "%",
    calculation: str = "annual_average",
) -> list[dict]:
    df = _read_raw("fred_raw.csv")
    if df.empty:
        return []
    df = df[(df["country_code"] == "US") & (df["indicator_code"] == source_indicator)].copy()
    if df.empty:
        return []

    df["year"] = pd.to_datetime(df["date"] + "-01", errors="coerce").dt.year
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    annual = df.groupby("year", as_index=False)["value"].mean()
    annual = annual[annual["value"].notna()].copy()

    rows = []
    for _, item in annual.iterrows():
        row = _base_row("US", target_indicator, "FRED")
        row.update(
            {
                "indicator_name_zh": zh,
                "indicator_name_en": en,
                "date": str(int(item["year"])),
                "frequency": "A",
                "unit": unit,
                "seasonal_adjustment": "SA",
                "calculation": calculation,
                "value": item["value"],
                "source_organization": "FRED",
                "source_dataset": f"Federal Reserve Economic Data (annual average from {source_series_code})",
                "source_indicator_code": f"{source_series_code}.AAVG",
                "source_indicator_name": f"{en} annual average derived from monthly FRED series",
                "source_url": f"https://fred.stlouisfed.org/series/{source_series_code}",
            }
        )
        _append_row(rows, row)
    return rows


def _monthly_rows_to_annual(rows: list[dict], target_indicator: str, calculation: str = "annual_average") -> list[dict]:
    if not rows:
        return []
    df = pd.DataFrame(rows)
    df["year"] = pd.to_datetime(df["date"] + "-01", errors="coerce").dt.year
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    group_cols = [
        "country_code",
        "source_organization",
        "source_dataset",
        "source_indicator_code",
        "source_indicator_name",
        "source_url",
        "indicator_name_zh",
        "indicator_name_en",
        "unit",
        "seasonal_adjustment",
    ]
    annual = df.groupby(group_cols + ["year"], dropna=False, as_index=False)["value"].mean()

    out = []
    for _, item in annual.iterrows():
        source_short = "NBS" if "National Bureau" in item["source_organization"] else str(item["source_organization"])
        row = _base_row(item["country_code"], target_indicator, source_short)
        row.update(
            {
                "indicator_name_zh": item["indicator_name_zh"],
                "indicator_name_en": item["indicator_name_en"],
                "date": str(int(item["year"])),
                "frequency": "A",
                "unit": item["unit"],
                "seasonal_adjustment": item["seasonal_adjustment"],
                "calculation": calculation,
                "value": item["value"],
                "source_organization": item["source_organization"],
                "source_dataset": f"{item['source_dataset']} (annualized)",
                "source_indicator_code": f"{item['source_indicator_code']}.AAVG",
                "source_indicator_name": f"{item['source_indicator_name']} annual average",
                "source_url": item["source_url"],
            }
        )
        _append_row(out, row)
    return out


def _china_monthly_to_common(source_indicator: str, target_indicator: str, zh: str, en: str) -> list[dict]:
    df = _read_raw("china_official_raw.csv")
    if df.empty:
        return []
    df = df[(df["country_code"] == "CN") & (df["indicator_code"] == source_indicator)].copy()
    if df.empty:
        return []

    rows = []
    for _, item in df.iterrows():
        source_code = str(item.get("source_indicator_code", source_indicator))
        row = _base_row("CN", target_indicator, "NBS")
        row.update(
            {
                "indicator_name_zh": zh,
                "indicator_name_en": en,
                "date": item["date"],
                "frequency": "M",
                "unit": "%",
                "seasonal_adjustment": "NSA",
                "calculation": "YoY",
                "value": item["value"],
                "source_organization": "National Bureau of Statistics of China",
                "source_dataset": "National Bureau of Statistics monthly data (aligned)",
                "source_indicator_code": f"{source_code}.ALIGNED",
                "source_indicator_name": f"China {en} aligned to common {target_indicator}",
                "source_url": item.get("source_url"),
            }
        )
        _append_row(rows, row)
    return rows


def _ecb_eurusd_to_exchange_rate_usd() -> list[dict]:
    df = _read_raw("ecb_raw.csv")
    if df.empty:
        return []
    df = df[df["indicator_code"] == "EUR_USD_EXCHANGE_RATE_D"].copy()
    if df.empty:
        return []

    rows = []
    for _, item in df.iterrows():
        value = pd.to_numeric(item["value"], errors="coerce")
        if pd.isna(value) or value == 0:
            continue
        row = _base_row("EA", "EXCHANGE_RATE_USD_D", "ECB")
        row.update(
            {
                "indicator_name_zh": "本币兑美元汇率",
                "indicator_name_en": "Exchange rates against USD",
                "date": item["date"],
                "frequency": "D",
                "unit": "local currency per USD",
                "seasonal_adjustment": "NSA",
                "calculation": "inverse_level",
                "value": 1 / value,
                "source_organization": "ECB",
                "source_dataset": "Euro foreign exchange reference rates (inverted)",
                "source_indicator_code": "EXR.D.USD.EUR.SP00.A.INV",
                "source_indicator_name": "EUR per USD derived from ECB USD per EUR reference rate",
                "source_url": item.get("source_url"),
            }
        )
        _append_row(rows, row)
    return rows


def _daily_exchange_to_period(rows: list[dict], target_indicator: str, freq: str, period_format: str) -> list[dict]:
    if not rows:
        return []
    df = pd.DataFrame(rows)
    df["date_dt"] = pd.to_datetime(df["date"], errors="coerce")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df[df["date_dt"].notna() & df["value"].notna()].copy()
    if freq == "M":
        df["period"] = df["date_dt"].dt.to_period("M").astype(str)
    else:
        df["period"] = df["date_dt"].dt.year.astype(str)

    group_cols = [
        "country_code",
        "source_organization",
        "source_dataset",
        "source_indicator_code",
        "source_indicator_name",
        "source_url",
    ]
    grouped = df.groupby(group_cols + ["period"], dropna=False, as_index=False)["value"].mean()

    out = []
    for _, item in grouped.iterrows():
        source_short = str(item["source_organization"])
        row = _base_row(item["country_code"], target_indicator, source_short)
        row.update(
            {
                "indicator_name_zh": "本币兑美元汇率",
                "indicator_name_en": "Exchange rates against USD",
                "date": item["period"],
                "frequency": freq,
                "unit": "local currency per USD",
                "seasonal_adjustment": "NSA",
                "calculation": "period_average",
                "value": item["value"],
                "source_organization": item["source_organization"],
                "source_dataset": f"{item['source_dataset']} ({period_format} average)",
                "source_indicator_code": f"{item['source_indicator_code']}.{freq}AVG",
                "source_indicator_name": f"{item['source_indicator_name']} {period_format} average",
                "source_url": item["source_url"],
            }
        )
        _append_row(out, row)
    return out


def _bis_exchange_rows() -> list[dict]:
    df = _read_raw("bis_raw.csv")
    if df.empty:
        return []
    df = df[df["indicator_code"] == "EXCHANGE_RATE_USD_D"].copy()
    if df.empty:
        return []
    rows = []
    for _, item in df.iterrows():
        row = item.to_dict()
        row["calculation"] = "level"
        _append_row(rows, row)
    return rows


def build_aligned_derived_sources() -> pd.DataFrame:
    rows: list[dict] = []

    cpi_m = _fred_monthly_index_to_yoy(
        "US_CPI_INDEX_M",
        "CPIAUCSL",
        "CPI_YOY_M",
        "居民消费价格指数同比",
        "Consumer Price Index YoY",
        "U.S. CPI YoY derived from CPIAUCSL",
        "SA",
    )
    cpi_m.extend(_china_monthly_to_common("CN_CPI_YOY_M", "CPI_YOY_M", "居民消费价格指数同比", "Consumer Price Index YoY"))
    rows.extend(cpi_m)
    rows.extend(_monthly_rows_to_annual(cpi_m, "CPI_YOY_A"))

    ppi_m = _fred_monthly_index_to_yoy(
        "US_PPI_INDEX_M",
        "PPIACO",
        "PPI_YOY_M",
        "生产者价格指数同比",
        "Producer Price Index YoY",
        "U.S. PPI YoY derived from PPIACO",
        "NSA",
    )
    ppi_m.extend(_china_monthly_to_common("CN_PPI_YOY_M", "PPI_YOY_M", "生产者价格指数同比", "Producer Price Index YoY"))
    rows.extend(ppi_m)
    rows.extend(_monthly_rows_to_annual(ppi_m, "PPI_YOY_A"))

    industry_m = _fred_monthly_index_to_yoy(
        "US_INDUSTRIAL_PRODUCTION_M",
        "INDPRO",
        "INDUSTRIAL_OUTPUT_YOY_M",
        "工业生产同比",
        "Industrial Output YoY",
        "U.S. industrial production YoY derived from INDPRO",
        "SA",
    )
    industry_m.extend(_china_monthly_to_common("CN_INDUSTRIAL_VALUE_ADDED_YOY_M", "INDUSTRIAL_OUTPUT_YOY_M", "工业生产同比", "Industrial Output YoY"))
    rows.extend(industry_m)
    rows.extend(_monthly_rows_to_annual(industry_m, "INDUSTRIAL_OUTPUT_YOY_A"))

    rows.extend(
        _fred_monthly_to_annual(
            "US_UNEMPLOYMENT_RATE_M",
            "UNRATE",
            "UNEMPLOYMENT_RATE_A",
            "失业率",
            "Unemployment Rate",
        )
    )

    ecb_daily = _ecb_eurusd_to_exchange_rate_usd()
    rows.extend(ecb_daily)
    exchange_daily = _bis_exchange_rows() + ecb_daily
    rows.extend(_daily_exchange_to_period(exchange_daily, "EXCHANGE_RATE_USD_M", "M", "monthly"))
    rows.extend(_daily_exchange_to_period(exchange_daily, "EXCHANGE_RATE_USD_A", "A", "annual"))

    out = pd.DataFrame(rows)
    for col in BASE_COLUMNS:
        if col not in out.columns:
            out[col] = None
    out = out[BASE_COLUMNS]
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT_FILE, index=False, encoding="utf-8-sig")
    print(f"[AlignedDerived] saved: {OUT_FILE}, shape={out.shape}")
    return out


if __name__ == "__main__":
    build_aligned_derived_sources()
