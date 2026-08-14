# -*- coding: utf-8 -*-
from typing import Any, Literal, Optional
import os
from datetime import date
from pathlib import Path

import pandas as pd

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from config import DB_PATH
from api_service.panel import PANEL_HTML
from services.ai_qa_service import ask_deepseek, build_messages, prepare_evidence, resolve_query_intent, route_with_deepseek
from services.query_service import build_batch_response, build_query_response, read_sql


class QueryItem(BaseModel):
    country: str = Field(..., description="Country or region code, e.g. US, CN, AR")
    indicator: str = Field(..., description="Standard indicator code, e.g. CPI_YOY_A")
    start: Optional[str] = Field(None, description="Start date or year, e.g. 2015 or 2020-01")
    end: Optional[str] = Field(None, description="End date or year, e.g. 2024 or 2024-12")
    frequency: Optional[str] = Field(None, description="Frequency code: D/W/M/Q/A")
    source: Optional[str] = Field(None, description="Source organization, e.g. IMF, World Bank, FRED")


class BatchQueryRequest(BaseModel):
    queries: list[QueryItem]


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=1000)
    context: Optional[dict[str, Any]] = None
    history: list[ChatTurn] = Field(default_factory=list, max_length=20)


class ReportRequest(BaseModel):
    country: str = Field(..., min_length=2, max_length=8)
    indicator: str = Field(..., min_length=2, max_length=120)


def _records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    return frame.astype(object).where(frame.notna(), None).to_dict(orient="records")


app = FastAPI(
    title="EconAtlas 全球宏观经济指标数据要素服务",
    version="1.2.0",
    description="面向全球宏观经济指标的数据采集、标准化治理与结构化 JSON API 服务。",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api")
def api_home() -> dict[str, Any]:
    return {
        "name": "EconAtlas",
        "description": "全球宏观经济指标数据要素采集、标准化治理与结构化服务平台",
        "version": "1.2.0",
        "db_path": str(DB_PATH),
        "db_exists": DB_PATH.exists(),
        "endpoints": {
            "query": "/query?country=US&indicator=CPI_YOY_A&start=2020&end=2024&frequency=A",
            "batch_query": "POST /batch_query",
            "metadata": "/metadata",
            "health": "/health",
        },
    }


@app.get("/", response_class=HTMLResponse)
def workspace() -> HTMLResponse:
    return HTMLResponse(PANEL_HTML)


@app.get("/dashboard-summary")
def dashboard_summary() -> dict[str, Any]:
    try:
        totals = read_sql(
            """
            SELECT COUNT(*) AS rows,
                   SUM(CASE WHEN value IS NOT NULL THEN 1 ELSE 0 END) AS valid_rows,
                   COUNT(DISTINCT country_code) AS countries,
                   COUNT(DISTINCT indicator_code) AS indicators,
                   COUNT(DISTINCT source_organization) AS sources,
                   MIN(date) AS earliest_date, MAX(date) AS latest_date
            FROM macro_observations
            WHERE observation_type != 'forecast'
            """
        ).iloc[0]
        forecast = read_sql(
            """SELECT COUNT(*) AS rows, MIN(date) AS earliest_date, MAX(date) AS latest_date
               FROM macro_observations WHERE observation_type = 'forecast'"""
        ).iloc[0]
        source_counts = read_sql(
            """SELECT source_organization AS source, COUNT(*) AS rows
               FROM macro_observations WHERE observation_type != 'forecast'
               GROUP BY source_organization ORDER BY rows DESC"""
        )
        frequency_counts = read_sql(
            """SELECT frequency, COUNT(*) AS rows FROM macro_observations
               WHERE observation_type != 'forecast'
               GROUP BY frequency ORDER BY rows DESC"""
        )
        return {
            "totals": {key: (None if pd.isna(value) else value.item() if hasattr(value, "item") else value) for key, value in totals.items()},
            "forecast_scenario": {key: (None if pd.isna(value) else value.item() if hasattr(value, "item") else value) for key, value in forecast.items()},
            "as_of_date": date.today().isoformat(),
            "source_counts": source_counts.to_dict(orient="records"),
            "frequency_counts": frequency_counts.to_dict(orient="records"),
            "deepseek_configured": bool(os.environ.get("DEEPSEEK_API_KEY", "").strip()),
        }
    except Exception as exc:
        return {"error": str(exc)}


@app.get("/assets")
def assets(limit: int = Query(80, ge=1, le=300)) -> dict[str, Any]:
    try:
        data = read_sql(
            """
            SELECT country_code, country_name_zh, indicator_code, indicator_name_zh,
                   frequency, unit, source_organization,
                   COUNT(*) AS observations, MIN(date) AS start_date, MAX(date) AS end_date,
                   SUM(CASE WHEN value IS NOT NULL THEN 1 ELSE 0 END) AS valid_observations
            FROM macro_observations
            WHERE observation_type != 'forecast'
            GROUP BY country_code, country_name_zh, indicator_code, indicator_name_zh,
                     frequency, unit, source_organization
            ORDER BY observations DESC LIMIT ?
            """,
            [limit],
        )
        return {"assets": data.where(data.notna(), None).to_dict(orient="records"), "count": len(data)}
    except Exception as exc:
        return {"assets": [], "count": 0, "error": str(exc)}


@app.get("/catalog")
def catalog() -> dict[str, Any]:
    countries = read_sql(
        """SELECT country_code, COALESCE(MAX(country_name_zh), country_code) AS name
           FROM macro_observations WHERE observation_type != 'forecast'
           GROUP BY country_code ORDER BY country_code"""
    )
    indicators = read_sql(
        """SELECT indicator_code, COALESCE(MAX(indicator_name_zh), indicator_code) AS name,
                  COALESCE(MAX(unit), '') AS unit, COUNT(*) AS observations
           FROM macro_observations WHERE observation_type != 'forecast'
           GROUP BY indicator_code ORDER BY indicator_code"""
    )
    return {"countries": _records(countries), "indicators": _records(indicators)}


@app.get("/quality-status")
def quality_status() -> dict[str, Any]:
    base = Path(DB_PATH).parent
    files = {
        "checks": base / "quality_report.csv",
        "consistency": base / "quality_consistency_report.csv",
        "coverage": base / "quality_coverage_report.csv",
        "outliers": base / "quality_outlier_report.csv",
    }
    result: dict[str, Any] = {}
    for key, path in files.items():
        frame = pd.read_csv(path) if path.exists() else pd.DataFrame()
        result[key] = _records(frame.head(200))
        result[f"{key}_count"] = int(len(frame))
        result[f"{key}_warnings"] = int((frame.get("status", pd.Series(dtype=str)).astype(str).str.lower() == "warning").sum())
    return result


@app.get("/risk-alerts")
def risk_alerts() -> dict[str, Any]:
    quality = quality_status()
    outliers = pd.DataFrame(quality["outliers"])
    consistency = pd.DataFrame(quality["consistency"])
    warnings = consistency[consistency.get("status", pd.Series(index=consistency.index, dtype=str)).astype(str).str.lower() == "warning"] if not consistency.empty else consistency
    return {
        "quality_warnings": quality["checks_warnings"],
        "consistency_warnings": quality["consistency_warnings"],
        "outlier_count": quality["outliers_count"],
        "alerts": _records(warnings.head(100)),
        "outliers": _records(outliers.head(100)),
    }


@app.post("/reports/generate")
def generate_report(payload: ReportRequest) -> dict[str, Any]:
    data = read_sql(
        """SELECT date, value, unit, frequency, source_organization, source_dataset,
                  country_name_zh, indicator_name_zh, observation_type
           FROM macro_observations
           WHERE country_code = ? AND indicator_code = ? AND observation_type != 'forecast'
                 AND value IS NOT NULL
           ORDER BY date""",
        [payload.country.upper(), payload.indicator],
    )
    if data.empty:
        return {"error": "当前条件没有可生成报告的历史或已发布数据。"}
    recent = data.tail(24).copy()
    latest = float(recent.iloc[-1]["value"])
    first = float(recent.iloc[0]["value"])
    trend = "上升" if latest > first else "下降" if latest < first else "平稳"
    country_name = str(recent.iloc[-1]["country_name_zh"] or payload.country)
    indicator_name = str(recent.iloc[-1]["indicator_name_zh"] or payload.indicator)
    unit = str(recent.iloc[-1]["unit"] or "")
    sources = sorted(recent["source_organization"].dropna().astype(str).unique().tolist())
    summary = (
        f"{country_name}的{indicator_name}在最近{len(recent)}条已发布观测中整体呈{trend}态势。"
        f"最新值为{latest:g}{unit}，样本均值为{float(recent['value'].mean()):g}{unit}。"
        "本结论仅使用历史值和截至当前日期已发布的数据，不使用预测值。"
    )
    markdown = f"""# {country_name} {indicator_name}分析报告

## 报告摘要

{summary}

## 核心统计

- 指标代码：{payload.indicator}
- 时间范围：{recent.iloc[0]['date']}—{recent.iloc[-1]['date']}
- 有效观测：{len(recent)} 条
- 最新值：{latest:g}{unit}
- 均值：{float(recent['value'].mean()):g}{unit}
- 最大值：{float(recent['value'].max()):g}{unit}
- 最小值：{float(recent['value'].min()):g}{unit}
- 数据来源：{'、'.join(sources)}

## 数据治理说明

报告基于 EconAtlas 标准库生成，已排除 observation_type=forecast 的预测记录，并保留来源与口径字段。
"""
    return {
        "country": payload.country.upper(), "country_name": country_name,
        "indicator": payload.indicator, "indicator_name": indicator_name,
        "summary": summary, "markdown": markdown,
        "stats": {"count": len(recent), "latest": latest, "mean": float(recent["value"].mean()), "min": float(recent["value"].min()), "max": float(recent["value"].max()), "unit": unit, "start": str(recent.iloc[0]["date"]), "end": str(recent.iloc[-1]["date"])},
        "sources": sources, "series": _records(recent), "forecast_excluded": True,
    }


@app.post("/chat")
def chat(payload: ChatRequest) -> dict[str, Any]:
    try:
        history = [item.model_dump() for item in payload.history]
        decision = route_with_deepseek(payload.question, history, payload.context)
        if decision.route in {"general", "clarify"}:
            return {
                "answer": decision.answer, "route": decision.route,
                "context": payload.context or {}, "evidence": [],
            }
        observations = read_sql("SELECT * FROM macro_observations")
        observations["date_year"] = observations["date"].astype(str).str[:4].astype("Int64")
        intent = resolve_query_intent(payload.question, observations, payload.context)
        subset = observations[
            (observations["country_code"] == intent["country"])
            & (observations["indicator_code"] == intent["indicator"])
            & (observations["date_year"].between(intent["start_year"], intent["end_year"]))
        ].copy()
        evidence, evidence_text = prepare_evidence(subset)
        if evidence.empty:
            return {"answer": "当前标准库中没有检索到与该问题匹配的数据，请调整国家、指标或年份。", "context": intent, "evidence": []}
        first = subset.iloc[0]
        country_label = str(first.get("country_name_zh") or intent["country"])
        indicator_label = str(first.get("indicator_name_zh") or intent["indicator"])
        answer = ask_deepseek(build_messages(payload.question, country_label, indicator_label, evidence_text))
        records = evidence.where(evidence.notna(), None).to_dict(orient="records")
        return {"answer": answer.text, "model": answer.model, "route": "data", "context": intent, "evidence": records}
    except Exception as exc:
        return {"answer": None, "error": str(exc), "context": payload.context or {}, "evidence": []}


@app.get("/health")
def health_check() -> dict[str, Any]:
    return {"status": "ok", "db_exists": DB_PATH.exists()}


@app.get("/metadata")
def metadata() -> dict[str, Any]:
    try:
        df = read_sql("SELECT * FROM macro_observations WHERE observation_type != 'forecast'")
        forecast_count = int(read_sql(
            "SELECT COUNT(*) AS rows FROM macro_observations WHERE observation_type = 'forecast'"
        ).iloc[0]["rows"])
        frequencies = sorted(df["frequency"].dropna().astype(str).unique().tolist())
        return {
            "data_asset": {
                "table": "macro_observations",
                "rows": int(len(df)),
                "countries": int(df["country_code"].nunique()),
                "indicators": int(df["indicator_code"].nunique()),
                "sources": int(df["source_organization"].nunique()),
                "frequencies": frequencies,
                "as_of_date": date.today().isoformat(),
                "forecast_rows_excluded": forecast_count,
            },
            "sources": sorted(df["source_organization"].dropna().unique().tolist()),
            "indicators": sorted(df["indicator_code"].dropna().unique().tolist()),
            "countries": sorted(df["country_code"].dropna().unique().tolist()),
            "error": None,
        }
    except Exception as exc:
        return {
            "data_asset": None,
            "sources": [],
            "indicators": [],
            "countries": [],
            "error": {"message": str(exc)},
        }


@app.get("/query")
def query_macro(
    country: str = Query(..., description="国家或地区代码，例如 US、CN、AR"),
    indicator: str = Query(..., description="标准指标代码，例如 CPI_YOY_A"),
    start: Optional[str] = Query(None, description="开始日期或年份，例如 2015 或 2020-01"),
    end: Optional[str] = Query(None, description="结束日期或年份，例如 2024 或 2024-12"),
    frequency: Optional[str] = Query(None, description="频率代码，例如 D、M、Q、A"),
    source: Optional[str] = Query(None, description="数据来源，例如 IMF、World Bank、FRED"),
) -> dict[str, Any]:
    try:
        return build_query_response(country, indicator, start, end, frequency, source)
    except Exception as exc:
        return {
            "request": {
                "country": country,
                "indicator_code": indicator,
                "start_date": start,
                "end_date": end,
                "frequency": frequency,
                "source": source,
            },
            "series": None,
            "error": {"message": str(exc)},
        }


@app.post("/batch_query")
def batch_query(payload: BatchQueryRequest) -> dict[str, Any]:
    return build_batch_response([item.dict() for item in payload.queries])
