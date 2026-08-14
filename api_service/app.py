# -*- coding: utf-8 -*-
from typing import Any, Optional

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from config import DB_PATH
from api_service.workspace import WORKSPACE_HTML
from services.ai_qa_service import ask_deepseek, build_messages, prepare_evidence, resolve_query_intent
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


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=1000)
    context: Optional[dict[str, Any]] = None


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
    return HTMLResponse(WORKSPACE_HTML)


@app.post("/chat")
def chat(payload: ChatRequest) -> dict[str, Any]:
    try:
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
        return {"answer": answer.text, "model": answer.model, "context": intent, "evidence": records}
    except Exception as exc:
        return {"answer": None, "error": str(exc), "context": payload.context or {}, "evidence": []}


@app.get("/health")
def health_check() -> dict[str, Any]:
    return {"status": "ok", "db_exists": DB_PATH.exists()}


@app.get("/metadata")
def metadata() -> dict[str, Any]:
    try:
        df = read_sql("SELECT * FROM macro_observations")
        frequencies = sorted(df["frequency"].dropna().astype(str).unique().tolist())
        return {
            "data_asset": {
                "table": "macro_observations",
                "rows": int(len(df)),
                "countries": int(df["country_code"].nunique()),
                "indicators": int(df["indicator_code"].nunique()),
                "sources": int(df["source_organization"].nunique()),
                "frequencies": frequencies,
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
