# -*- coding: utf-8 -*-
from typing import Any, Literal, Optional
import os
import json
import time
from datetime import date, datetime
from html import escape as html_escape
from io import BytesIO
from pathlib import Path

import pandas as pd

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, Field

from config import DB_PATH
from api_service.panel import PANEL_HTML
from services.ai_qa_service import ask_deepseek, build_messages, prepare_evidence, resolve_query_intent, route_with_deepseek
from services.query_service import build_batch_response, build_query_response, read_sql

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    from reportlab.graphics.shapes import Drawing, PolyLine, String
    REPORTLAB_AVAILABLE = True
except ImportError:  # pragma: no cover - deployment dependency guard
    REPORTLAB_AVAILABLE = False


class QueryItem(BaseModel):
    country: str = Field(..., description="Country or region code, e.g. US, CN, AR")
    indicator: str = Field(..., description="Standard indicator code, e.g. CPI_YOY_A")
    start: Optional[str] = Field(None, description="Start date or year, e.g. 2015 or 2020-01")
    end: Optional[str] = Field(None, description="End date or year, e.g. 2024 or 2024-12")
    frequency: Optional[str] = Field(None, description="Frequency code: D/W/M/Q/A")
    source: Optional[str] = Field(None, description="Source organization, e.g. IMF, World Bank, FRED")
    include_forecast: bool = Field(False, description="Explicitly include forecast scenarios; defaults to false")


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


class AlignmentReviewRequest(BaseModel):
    candidate_id: str = Field(..., min_length=8, max_length=64)
    decision: Literal["approved", "rejected", "needs_review"]
    reviewer: str = Field("competition-reviewer", min_length=2, max_length=80)
    note: str = Field("", max_length=500)


# Reuse the just-generated report when the user immediately downloads its PDF.
# This prevents a second DeepSeek request and keeps the PDF button responsive.
REPORT_CACHE: dict[tuple[str, str], tuple[float, dict[str, Any]]] = {}


def _records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    return frame.astype(object).where(frame.notna(), None).to_dict(orient="records")


app = FastAPI(
    title="EconAtlas 全球宏观经济指标数据要素服务",
    version="2.2.0",
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
        "version": "2.2.0",
        "db_path": str(DB_PATH),
        "db_exists": DB_PATH.exists(),
        "endpoints": {
            "query": "/query?country=US&indicator=CPI_YOY_A&start=2020&end=2024&frequency=A",
            "batch_query": "POST /batch_query",
            "metadata": "/metadata",
            "source_center": "/source-center",
            "quality_contracts": "/quality-contracts",
            "revision_history": "/revision-history",
            "acceptance_tests": "POST /acceptance-tests",
            "alignment_review": "POST /alignment-reviews",
            "chat": "POST /chat",
            "smart_report": "POST /reports/generate",
            "report_pdf": "/reports/pdf",
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


@app.get("/series-data")
def series_data(
    country: str = Query(...), indicator: str = Query(...),
    start: Optional[str] = Query(None), end: Optional[str] = Query(None),
    frequency: Optional[str] = Query(None), source: Optional[str] = Query(None),
    include_forecast: bool = Query(False),
) -> dict[str, Any]:
    sql = """SELECT date, value, unit, frequency, source_organization, source_dataset,
                    observation_type, status
             FROM macro_observations WHERE country_code = ? AND indicator_code = ?
                    AND value IS NOT NULL"""
    params: list[Any] = [country.upper(), indicator]
    if not include_forecast:
        sql += " AND observation_type != 'forecast'"
    if start:
        sql += " AND date >= ?"
        params.append(start)
    if end:
        sql += " AND date <= ?"
        params.append(end)
    if frequency:
        sql += " AND frequency = ?"
        params.append(frequency)
    if source:
        sql += " AND source_organization = ?"
        params.append(source)
    sql += " ORDER BY date, source_organization LIMIT 5000"
    frame = read_sql(sql, params)
    return {
        "country": country.upper(), "indicator": indicator, "start": start, "end": end,
        "frequency": frequency, "source": source, "include_forecast": include_forecast,
        "rows": _records(frame), "count": len(frame),
    }


@app.get("/lineage")
def lineage() -> dict[str, Any]:
    path = Path(DB_PATH).parent.parent / "metadata" / "source_mapping.csv"
    frame = pd.read_csv(path) if path.exists() else pd.DataFrame()
    return {"mappings": _records(frame), "count": len(frame)}


@app.get("/alignment-candidates")
def alignment_candidates() -> dict[str, Any]:
    path = Path(DB_PATH).parent.parent / "metadata" / "alignment_candidates.csv"
    frame = pd.read_csv(path) if path.exists() else pd.DataFrame()
    review_path = Path(DB_PATH).parent.parent / "metadata" / "mapping_reviews.csv"
    reviews = pd.read_csv(review_path, encoding="utf-8-sig") if review_path.exists() else pd.DataFrame()
    if not frame.empty and not reviews.empty and "candidate_id" in frame and "candidate_id" in reviews:
        latest = reviews.sort_values("reviewed_at").drop_duplicates("candidate_id", keep="last")
        frame = frame.merge(latest[["candidate_id", "decision", "reviewer", "note", "reviewed_at"]], on="candidate_id", how="left")
        labels = {"approved": "人工已批准", "rejected": "人工已驳回", "needs_review": "待人工复核"}
        frame["review_status"] = frame["decision"].map(labels).fillna(frame["review_status"])
    distribution = frame.groupby("confidence_level", dropna=False).size().reset_index(name="count") if not frame.empty else pd.DataFrame()
    status_distribution = frame.groupby("review_status", dropna=False).size().reset_index(name="count") if not frame.empty else pd.DataFrame()
    return {"candidates": _records(frame), "distribution": _records(distribution), "status_distribution": _records(status_distribution), "count": len(frame)}


@app.post("/alignment-reviews")
def alignment_review(payload: AlignmentReviewRequest) -> dict[str, Any]:
    root = Path(DB_PATH).parent.parent
    candidate_path = root / "metadata" / "alignment_candidates.csv"
    candidates = pd.read_csv(candidate_path, encoding="utf-8-sig") if candidate_path.exists() else pd.DataFrame()
    if candidates.empty or "candidate_id" not in candidates or payload.candidate_id not in set(candidates["candidate_id"].astype(str)):
        return {"error": "Candidate not found", "candidate_id": payload.candidate_id}
    selected = candidates[candidates["candidate_id"].astype(str).eq(payload.candidate_id)].iloc[0]
    review_path = root / "metadata" / "mapping_reviews.csv"
    columns = ["candidate_id", "source", "source_dataset", "source_indicator_code", "candidate_indicator_code", "decision", "reviewer", "note", "reviewed_at", "application_status"]
    reviews = pd.read_csv(review_path, encoding="utf-8-sig") if review_path.exists() else pd.DataFrame(columns=columns)
    row = {
        "candidate_id": payload.candidate_id, "source": selected.get("source"),
        "source_dataset": selected.get("source_dataset"), "source_indicator_code": selected.get("source_indicator_code"),
        "candidate_indicator_code": selected.get("candidate_indicator_code"), "decision": payload.decision,
        "reviewer": payload.reviewer, "note": payload.note, "reviewed_at": datetime.now().isoformat(timespec="seconds"),
        "application_status": "pending_next_publication" if payload.decision == "approved" else "recorded",
    }
    reviews = pd.concat([reviews, pd.DataFrame([row])], ignore_index=True)
    reviews.to_csv(review_path, index=False, encoding="utf-8-sig")
    return {
        "saved": True,
        "review": row,
        "message": "审核决定已记录；批准项仍需合并进正式映射并通过下一次质量门禁后才会生效，当前标准库不会被直接修改。",
    }


@app.get("/source-center")
def source_center() -> dict[str, Any]:
    frame = read_sql(
        """SELECT source_organization AS source, COUNT(*) AS rows,
                  COUNT(DISTINCT source_dataset) AS datasets,
                  COUNT(DISTINCT source_indicator_code) AS source_series,
                  COUNT(DISTINCT indicator_code) AS standard_indicators,
                  MIN(date) AS earliest_date, MAX(date) AS latest_date,
                  MAX(last_updated) AS last_updated,
                  SUM(CASE WHEN observation_type = 'forecast' THEN 1 ELSE 0 END) AS forecast_rows
           FROM macro_observations GROUP BY source_organization ORDER BY rows DESC"""
    )
    mapping_path = Path(DB_PATH).parent.parent / "metadata" / "source_mapping.csv"
    mapping = pd.read_csv(mapping_path, encoding="utf-8-sig") if mapping_path.exists() else pd.DataFrame()
    mapping_counts = mapping.groupby("source").size().to_dict() if not mapping.empty else {}
    rows = _records(frame)
    for row in rows:
        row["registered_mappings"] = int(mapping_counts.get(row["source"], 0))
        row["connection_status"] = "available"
    return {"sources": rows, "count": len(rows), "as_of_date": date.today().isoformat(), "update_mode": "GitHub Actions scheduled pipeline + local cache fallback"}


@app.get("/revision-history")
def revision_history(limit: int = Query(200, ge=1, le=1000)) -> dict[str, Any]:
    # FastAPI replaces Query with an int for HTTP calls; accepting a direct
    # function call as well keeps tests and offline report tooling reliable.
    limit_value = limit if isinstance(limit, int) else 200
    root = Path(DB_PATH).parent.parent
    path = root / "metadata" / "revision_events.csv"
    events = pd.read_csv(path, encoding="utf-8-sig") if path.exists() else pd.DataFrame()
    if not events.empty and "detected_at" in events:
        events = events.sort_values("detected_at", ascending=False).head(limit_value)
    status = read_sql("SELECT release_status, COUNT(*) AS rows FROM macro_observations GROUP BY release_status ORDER BY rows DESC")
    versions = read_sql("SELECT data_version, COUNT(*) AS rows FROM macro_observations GROUP BY data_version ORDER BY rows DESC LIMIT 30")
    return {"events": _records(events), "event_count": len(events), "release_status": _records(status), "data_versions": _records(versions), "method": "对比相邻发布快照的业务主键与数值，仅记录真实变化"}


@app.get("/quality-contracts")
def quality_contracts() -> dict[str, Any]:
    path = Path(DB_PATH).parent / "quality_gate.json"
    if not path.exists():
        return {"status": "not_run", "checks": {}}
    return json.loads(path.read_text(encoding="utf-8-sig"))


@app.post("/acceptance-tests")
def acceptance_tests() -> dict[str, Any]:
    started = time.perf_counter()
    samples = read_sql(
        """SELECT country_code AS country, indicator_code AS indicator, frequency, source_organization AS source,
                  COUNT(*) AS rows, MAX(date) AS latest_date
           FROM macro_observations WHERE observation_type != 'forecast'
           GROUP BY country_code, indicator_code, frequency, source_organization
           ORDER BY rows DESC, country_code, indicator_code LIMIT 23"""
    )
    queries = [{"country": row.country, "indicator": row.indicator, "frequency": row.frequency, "source": row.source, "include_forecast": False} for row in samples.itertuples(index=False)]
    result = build_batch_response(queries)
    details = []
    for query_item, response in zip(queries, result["results"]):
        series = response.get("series")
        series_list = series if isinstance(series, list) else [series] if series else []
        observations = [observation for item in series_list for observation in item.get("observations", [])]
        passed = response.get("error") is None and bool(observations) and all(item.get("observation_type") != "forecast" for item in observations)
        details.append({**query_item, "passed": passed, "observation_count": len(observations), "error": response.get("error")})
    passed_count = sum(1 for item in details if item["passed"])
    return {"status": "passed" if passed_count == len(details) and details else "failed", "test_count": len(details), "passed_count": passed_count, "failed_count": len(details) - passed_count, "elapsed_ms": round((time.perf_counter() - started) * 1000, 2), "details": details}


@app.get("/asset-ratings")
def asset_ratings() -> dict[str, Any]:
    frame = read_sql(
        """SELECT indicator_code, COALESCE(MAX(indicator_name_zh), indicator_code) AS indicator_name_zh,
                  COALESCE(MAX(frequency), '') AS frequency,
                  COUNT(DISTINCT country_code) AS country_count,
                  COUNT(DISTINCT source_organization) AS source_count,
                  COUNT(*) AS total_rows,
                  SUM(CASE WHEN value IS NOT NULL THEN 1 ELSE 0 END) AS valid_rows,
                  MIN(CAST(SUBSTR(date, 1, 4) AS INTEGER)) AS start_year,
                  MAX(CAST(SUBSTR(date, 1, 4) AS INTEGER)) AS end_year
           FROM macro_observations WHERE observation_type != 'forecast'
           GROUP BY indicator_code"""
    )
    if frame.empty:
        return {"assets": [], "distribution": [], "count": 0}
    frame["completeness"] = (frame["valid_rows"] / frame["total_rows"].replace(0, pd.NA) * 100).fillna(0)
    for source, target in [("country_count", "coverage_score"), ("source_count", "source_score"), ("valid_rows", "scale_score")]:
        frame[target] = frame[source] / max(float(frame[source].max()), 1) * 100
    frame["freshness_score"] = frame["end_year"].apply(lambda year: 100 if pd.notna(year) and year >= date.today().year - 1 else 70)
    frame["asset_score"] = (frame["completeness"] * .30 + frame["coverage_score"] * .25 + frame["source_score"] * .20 + frame["scale_score"] * .15 + frame["freshness_score"] * .10).round(1)
    frame["asset_level"] = frame["asset_score"].apply(lambda score: "S" if score >= 90 else "A" if score >= 80 else "B" if score >= 70 else "C" if score >= 60 else "D")
    frame = frame.sort_values(["asset_score", "valid_rows"], ascending=False)
    distribution = frame.groupby("asset_level").size().reset_index(name="count")
    return {"assets": _records(frame), "distribution": _records(distribution), "count": len(frame), "method": "完整性30% + 覆盖度25% + 多源20% + 规模15% + 新鲜度10%"}


@app.get("/system-status")
def system_status() -> dict[str, Any]:
    root = Path(DB_PATH).parent.parent
    update_path = root / "metadata" / "update_status.json"
    try:
        update = json.loads(update_path.read_text(encoding="utf-8-sig")) if update_path.exists() else {}
    except Exception:
        update = {}
    return {
        "service": "ok", "database": "ok" if DB_PATH.exists() else "missing",
        "database_bytes": DB_PATH.stat().st_size if DB_PATH.exists() else 0,
        "database_modified_at": date.fromtimestamp(DB_PATH.stat().st_mtime).isoformat() if DB_PATH.exists() else None,
        "deepseek": "configured" if os.environ.get("DEEPSEEK_API_KEY", "").strip() else "not_configured",
        "deployment": "FastAPI + Uvicorn on Render", "scheduled_update": update,
    }


@app.get("/quality-status")
def quality_status() -> dict[str, Any]:
    base = Path(DB_PATH).parent
    files = {
        "checks": base / "quality_report.csv",
        "consistency": base / "quality_consistency_report.csv",
        "coverage": base / "quality_coverage_report.csv",
        "outliers": base / "quality_outlier_report.csv",
    }
    current_year = date.today().year
    current_rows = int(read_sql(
        "SELECT COUNT(*) AS rows FROM macro_observations WHERE observation_type != 'forecast'"
    ).iloc[0]["rows"])
    forecast_rows = int(read_sql(
        "SELECT COUNT(*) AS rows FROM macro_observations WHERE observation_type = 'forecast'"
    ).iloc[0]["rows"])
    result: dict[str, Any] = {
        "scope": "released_data",
        "as_of_date": date.today().isoformat(),
        "forecast_rows_excluded": forecast_rows,
    }
    for key, path in files.items():
        frame = pd.read_csv(path) if path.exists() else pd.DataFrame()
        if key in {"consistency", "outliers"} and not frame.empty and "date" in frame:
            years = pd.to_numeric(frame["date"].astype(str).str.extract(r"^(\d{4})", expand=False), errors="coerce")
            frame = frame[years.le(current_year) | years.isna()].copy()
        if key == "checks" and not frame.empty:
            frame.loc[frame["check_item"] == "row_count", "value"] = current_rows
            if "outlier_count" in frame["check_item"].astype(str).values:
                outlier_path = files["outliers"]
                outlier_frame = pd.read_csv(outlier_path) if outlier_path.exists() else pd.DataFrame()
                if not outlier_frame.empty and "date" in outlier_frame:
                    years = pd.to_numeric(outlier_frame["date"].astype(str).str.extract(r"^(\d{4})", expand=False), errors="coerce")
                    outlier_frame = outlier_frame[years.le(current_year) | years.isna()]
                frame.loc[frame["check_item"] == "outlier_count", "value"] = len(outlier_frame)
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


def _report_payload(payload: ReportRequest, use_deepseek: bool = True) -> dict[str, Any]:
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
    source_rank = (
        data.groupby("source_organization", dropna=False)
        .agg(rows=("value", "size"), latest=("date", "max"))
        .sort_values(["latest", "rows"], ascending=False)
    )
    primary_source = source_rank.index[0]
    primary = data[data["source_organization"].fillna("") == ("" if pd.isna(primary_source) else primary_source)].copy()
    recent = primary.tail(24).copy()
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
    ai_analysis = summary
    analysis_mode = "statistical_fallback"
    if use_deepseek and os.environ.get("DEEPSEEK_API_KEY", "").strip():
        evidence_lines = "\n".join(
            f"[D{i + 1}] {row.date}: {row.value:g}{unit}，来源={row.source_organization}"
            for i, row in enumerate(recent.itertuples(index=False))
        )
        messages = [
            {
                "role": "system",
                "content": (
                    "你是 EconAtlas 智能报告分析器。只能依据编号数据证据写中文分析，不得补写数据或预测未来。"
                    "请用‘趋势判断、关键变化、数据局限’三个短段落，每个关键数值标注 [D编号]。"
                ),
            },
            {
                "role": "user",
                "content": f"对象：{country_name}；指标：{indicator_name}；单位：{unit}\n{evidence_lines}",
            },
        ]
        try:
            ai_result = ask_deepseek(messages)
            ai_analysis = ai_result.text
            analysis_mode = f"deepseek:{ai_result.model}"
        except Exception:
            pass
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

## 智能分析

{ai_analysis}

## 数据治理说明

报告基于 EconAtlas 标准库生成，已排除 observation_type=forecast 的预测记录，并保留来源与口径字段。
"""
    return {
        "country": payload.country.upper(), "country_name": country_name,
        "indicator": payload.indicator, "indicator_name": indicator_name,
        "summary": summary, "ai_analysis": ai_analysis, "analysis_mode": analysis_mode, "markdown": markdown,
        "stats": {"count": len(recent), "latest": latest, "mean": float(recent["value"].mean()), "min": float(recent["value"].min()), "max": float(recent["value"].max()), "unit": unit, "start": str(recent.iloc[0]["date"]), "end": str(recent.iloc[-1]["date"])},
        "sources": sources, "primary_source": None if pd.isna(primary_source) else str(primary_source),
        "series": _records(recent), "forecast_excluded": True,
    }


@app.post("/reports/generate")
def generate_report(payload: ReportRequest) -> dict[str, Any]:
    report = _report_payload(payload)
    if not report.get("error"):
        REPORT_CACHE[(payload.country.upper(), payload.indicator)] = (time.time(), report)
        if len(REPORT_CACHE) > 64:
            oldest_key = min(REPORT_CACHE, key=lambda key: REPORT_CACHE[key][0])
            REPORT_CACHE.pop(oldest_key, None)
    return report


def _build_pdf(report: dict[str, Any]) -> bytes:
    if not REPORTLAB_AVAILABLE:
        raise RuntimeError("当前环境未安装 reportlab")
    try:
        pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
        font_name = "STSong-Light"
    except Exception:  # pragma: no cover
        font_name = "Helvetica"
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=1.6 * cm, leftMargin=1.6 * cm, topMargin=1.5 * cm, bottomMargin=1.5 * cm)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("TitleCN", parent=styles["Title"], fontName=font_name, fontSize=18, leading=25, textColor=colors.HexColor("#17356b"))
    heading = ParagraphStyle("HeadingCN", parent=styles["Heading2"], fontName=font_name, fontSize=13, leading=20, textColor=colors.HexColor("#315ee9"), spaceBefore=12, spaceAfter=7)
    body = ParagraphStyle("BodyCN", parent=styles["BodyText"], fontName=font_name, fontSize=10.5, leading=18, textColor=colors.HexColor("#172033"))
    stats = report["stats"]
    story: list[Any] = [
        Paragraph(html_escape(f"{report['country_name']} · {report['indicator_name']}分析报告"), title_style),
        Paragraph("EconAtlas 全球宏观经济数据要素平台", body), Spacer(1, 8),
        Paragraph("一、报告摘要", heading), Paragraph(html_escape(report["summary"]), body),
        Paragraph("二、核心统计", heading),
    ]
    rows = [
        ["项目", "内容"], ["指标代码", report["indicator"]], ["时间范围", f"{stats['start']}—{stats['end']}"],
        ["有效观测", str(stats["count"])], ["最新值", f"{stats['latest']:g}{stats['unit']}"],
        ["均值", f"{stats['mean']:g}{stats['unit']}"], ["数据来源", "、".join(report["sources"])], ["预测记录", "0（已排除）"],
    ]
    table = Table(rows, colWidths=[4 * cm, 11.2 * cm])
    table.setStyle(TableStyle([("FONTNAME", (0, 0), (-1, -1), font_name), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#315ee9")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("GRID", (0, 0), (-1, -1), .4, colors.HexColor("#d8dfec")), ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f8faff")), ("PADDING", (0, 0), (-1, -1), 7)]))
    story.append(table)
    values = [float(row["value"]) for row in report["series"]]
    if len(values) >= 2:
        drawing = Drawing(440, 150)
        low, high = min(values), max(values)
        spread = high - low or 1
        points = [(18 + i * 400 / (len(values) - 1), 24 + (value - low) * 102 / spread) for i, value in enumerate(values)]
        drawing.add(PolyLine(points, strokeColor=colors.HexColor("#5868ef"), strokeWidth=2))
        drawing.add(String(18, 132, f"{high:g}", fontName=font_name, fontSize=8, fillColor=colors.HexColor("#718096")))
        drawing.add(String(18, 8, f"{low:g}", fontName=font_name, fontSize=8, fillColor=colors.HexColor("#718096")))
        drawing.add(String(72, 8, str(report["series"][0]["date"]), fontName=font_name, fontSize=8, fillColor=colors.HexColor("#718096")))
        drawing.add(String(350, 8, str(report["series"][-1]["date"]), fontName=font_name, fontSize=8, fillColor=colors.HexColor("#718096")))
        story.extend([Paragraph("三、趋势图", heading), drawing])
    story.extend([
        Paragraph("四、智能分析", heading), Paragraph(html_escape(report["ai_analysis"]).replace("\n", "<br/>"), body),
        Paragraph("五、数据治理说明", heading),
        Paragraph("本报告仅使用 EconAtlas 标准库中的历史值和截至当前日期已发布数据，预测情景已严格排除；来源、频率、单位和观测类型均保留可追溯字段。", body),
    ])
    doc.build(story)
    return buffer.getvalue()


@app.get("/reports/pdf")
def report_pdf(country: str = Query(...), indicator: str = Query(...)) -> Response:
    cache_key = (country.upper(), indicator)
    cached = REPORT_CACHE.get(cache_key)
    report = cached[1] if cached and time.time() - cached[0] <= 600 else _report_payload(
        ReportRequest(country=country, indicator=indicator)
    )
    if report.get("error"):
        return Response(report["error"], status_code=404, media_type="text/plain; charset=utf-8")
    pdf = _build_pdf(report)
    filename = f"EconAtlas-{country.upper()}-{indicator}.pdf"
    return Response(pdf, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{filename}"'})


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
        # Conversational data answers use the same released-data boundary as
        # the query, quality and report modules. Forecast scenarios remain in
        # the database but are never presented as current facts.
        observations = read_sql(
            "SELECT * FROM macro_observations WHERE observation_type != 'forecast'"
        )
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
    include_forecast: bool = Query(False, description="是否显式包含预测情景；默认不包含"),
) -> dict[str, Any]:
    try:
        return build_query_response(country, indicator, start, end, frequency, source, include_forecast)
    except Exception as exc:
        return {
            "request": {
                "country": country,
                "indicator_code": indicator,
                "start_date": start,
                "end_date": end,
                "frequency": frequency,
                "source": source,
                "include_forecast": include_forecast,
            },
            "series": None,
            "error": {"message": str(exc)},
        }


@app.post("/batch_query")
def batch_query(payload: BatchQueryRequest) -> dict[str, Any]:
    return build_batch_response([item.dict() for item in payload.queries])
