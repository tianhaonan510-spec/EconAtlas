"""Grounded DeepSeek Q&A for EconAtlas observations."""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass

import pandas as pd


DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-v4-flash"

COUNTRY_ALIASES = {
    "中国": "CN", "我国": "CN", "美国": "US", "日本": "JP", "德国": "DE",
    "英国": "GB", "印度": "IN", "法国": "FR", "意大利": "IT", "西班牙": "ES",
    "欧元区": "EA", "巴西": "BR", "南非": "ZA", "土耳其": "TR", "越南": "VN",
    "印度尼西亚": "ID", "印尼": "ID", "墨西哥": "MX", "阿根廷": "AR", "沙特": "SA",
}

INDICATOR_ALIASES = {
    "通胀": ["CPI_YOY_M", "CPI_YOY_A"], "物价": ["CPI_YOY_M", "CPI_YOY_A"],
    "cpi": ["CPI_YOY_M", "CPI_YOY_A"], "失业": ["UNEMPLOYMENT_RATE_M", "UNEMPLOYMENT_RATE_A"],
    "gdp增速": ["GDP_REAL_GROWTH_YOY_Q", "GDP_REAL_GROWTH_YOY_A"],
    "经济增长": ["GDP_REAL_GROWTH_YOY_Q", "GDP_REAL_GROWTH_YOY_A"],
    "gdp": ["GDP_NOMINAL_USD_A", "GDP_REAL_GROWTH_YOY_A"],
    "工业生产": ["INDUSTRIAL_PRODUCTION_INDEX_M", "INDUSTRIAL_OUTPUT_YOY_M"],
    "汇率": ["EXCHANGE_RATE_USD_M", "EXCHANGE_RATE_USD_A", "EXCHANGE_RATE_USD_D"],
    "出口": ["EXPORTS_USD_A", "EXPORTS_GROWTH_A"], "进口": ["IMPORTS_USD_A", "IMPORTS_GROWTH_A"],
    "人口": ["POPULATION_TOTAL_A", "POPULATION_GROWTH_A"], "债务": ["GOV_DEBT_GDP_A"],
}


@dataclass(frozen=True)
class AIAnswer:
    text: str
    model: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None


def resolve_query_intent(
    question: str,
    observations: pd.DataFrame,
    previous: dict | None = None,
    current_year: int = 2026,
) -> dict:
    """Resolve common Chinese macro questions to an available country/indicator pair."""
    text = question.strip()
    lowered = text.lower()
    previous = previous or {}
    available_countries = set(observations["country_code"].dropna().astype(str))
    country = next((code for alias, code in COUNTRY_ALIASES.items() if alias in text and code in available_countries), None)
    if not country:
        for code in available_countries:
            if re.search(rf"\b{re.escape(code.lower())}\b", lowered):
                country = code
                break
    country = country or previous.get("country") or ("CN" if "CN" in available_countries else sorted(available_countries)[0])

    country_rows = observations[observations["country_code"] == country]
    available_indicators = set(country_rows["indicator_code"].dropna().astype(str))
    indicator = None
    # Exact indicator names/codes take precedence over broad aliases.
    for row in country_rows[["indicator_code", "indicator_name_zh", "indicator_name_en"]].drop_duplicates().itertuples(index=False):
        names = [str(row.indicator_code), str(row.indicator_name_zh), str(row.indicator_name_en)]
        if any(name and name.lower() in lowered for name in names):
            indicator = str(row.indicator_code)
            break
    if not indicator:
        for alias, candidates in INDICATOR_ALIASES.items():
            if alias in lowered:
                indicator = next((candidate for candidate in candidates if candidate in available_indicators), None)
                if indicator:
                    break
    if not indicator and previous.get("country") == country and previous.get("indicator") in available_indicators:
        indicator = previous["indicator"]
    if not indicator:
        preferred = ["CPI_YOY_M", "CPI_YOY_A", "GDP_REAL_GROWTH_YOY_A"]
        indicator = next((item for item in preferred if item in available_indicators), sorted(available_indicators)[0])

    years = [int(value) for value in re.findall(r"(?<!\d)(19\d{2}|20\d{2}|2100)(?!\d)", text)]
    relative = re.search(r"(?:近|最近|过去)([一二三四五六七八九十\d]+)年", text)
    chinese_numbers = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
    if relative:
        token = relative.group(1)
        count = int(token) if token.isdigit() else chinese_numbers.get(token, 5)
        start_year, end_year = current_year - count + 1, current_year
    elif len(years) >= 2:
        start_year, end_year = min(years), max(years)
    elif len(years) == 1:
        start_year = end_year = years[0]
    else:
        start_year = int(previous.get("start_year", current_year - 5))
        end_year = int(previous.get("end_year", current_year))
    return {"country": country, "indicator": indicator, "start_year": start_year, "end_year": end_year}


def prepare_evidence(df: pd.DataFrame, max_rows: int = 36) -> tuple[pd.DataFrame, str]:
    """Select a compact, traceable evidence set for the model and the UI."""
    if df.empty:
        return df.copy(), ""
    evidence = df.dropna(subset=["value"]).copy()
    evidence["date"] = evidence["date"].astype(str)
    evidence["value"] = pd.to_numeric(evidence["value"], errors="coerce")
    evidence = evidence.dropna(subset=["value"])
    evidence = evidence.sort_values(["source_organization", "date"])
    if len(evidence) > max_rows:
        per_source = max(3, max_rows // max(evidence["source_organization"].nunique(), 1))
        evidence = evidence.groupby("source_organization", group_keys=False).tail(per_source).tail(max_rows)

    fields = [
        "date", "value", "unit", "frequency", "observation_type",
        "source_organization", "source_dataset", "source_url",
    ]
    fields = [field for field in fields if field in evidence.columns]
    evidence = evidence[fields].reset_index(drop=True)
    lines = []
    for index, row in evidence.iterrows():
        lines.append(
            f"[E{index + 1}] 日期={row.get('date')}；数值={row.get('value')} {row.get('unit', '')}；"
            f"频率={row.get('frequency', '')}；类型={row.get('observation_type', '')}；"
            f"来源={row.get('source_organization', '')} / {row.get('source_dataset', '')}"
        )
    return evidence, "\n".join(lines)


def build_messages(question: str, country_label: str, indicator_label: str, evidence_text: str) -> list[dict]:
    system = (
        "你是 EconAtlas 数据问答助手。只能依据用户提供的编号证据回答，不得使用模型记忆补写数值。"
        "所有关键数值后必须标注证据编号，如 [E1]。必须区分历史值、预测值和派生值。"
        "证据不足时明确说‘当前数据不足以判断’，不要猜测。回答使用中文，先给结论，再给依据、趋势和局限。"
        "不得声称因果关系，除非证据本身明确支持。"
    )
    user = (
        f"国家/地区：{country_label}\n指标：{indicator_label}\n问题：{question}\n\n"
        f"EconAtlas 检索证据：\n{evidence_text}"
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def ask_deepseek(messages: list[dict]) -> AIAnswer:
    api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("尚未配置 DEEPSEEK_API_KEY")
    base_url = os.environ.get("DEEPSEEK_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
    model = os.environ.get("DEEPSEEK_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
    payload = {
        "model": model,
        "messages": messages,
        "thinking": {"type": "disabled"},
        "temperature": 0.2,
        "max_tokens": 1200,
        "stream": False,
    }
    request = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"DeepSeek API 返回 HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"无法连接 DeepSeek API: {exc.reason}") from exc

    choices = result.get("choices") or []
    if not choices or not choices[0].get("message", {}).get("content"):
        raise RuntimeError("DeepSeek API 未返回有效回答")
    usage = result.get("usage") or {}
    return AIAnswer(
        text=choices[0]["message"]["content"].strip(),
        model=result.get("model", model),
        prompt_tokens=usage.get("prompt_tokens"),
        completion_tokens=usage.get("completion_tokens"),
    )
