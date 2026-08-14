"""Grounded DeepSeek Q&A for EconAtlas observations."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass

import pandas as pd


DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-v4-flash"


@dataclass(frozen=True)
class AIAnswer:
    text: str
    model: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None


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
