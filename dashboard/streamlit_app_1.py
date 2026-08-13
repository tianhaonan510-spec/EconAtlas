# -*- coding: utf-8 -*-
"""
MacroHub 全球宏观经济指标数据要素服务平台
dashboard/streamlit_app_1.py

功能模块：
1. 指标查询
2. 指标字典
3. 数据质量
4. JSON输出
5. 一致性分析
6. 治理驾驶舱
7. 指标血缘
8. 治理规则
9. API服务中心
10. 数据资产目录
11. 风险预警
12. 智能分析
13. 智能报告
"""

import sys
import json
import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib import colors
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    REPORTLAB_AVAILABLE = True
except Exception:
    REPORTLAB_AVAILABLE = False


# =========================
# 路径与配置
# =========================
BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(BASE_DIR))

try:
    from config import DATA_CLEAN
    DB_PATH = DATA_CLEAN / "macrohub.db"
except Exception:
    DATA_CLEAN = BASE_DIR / "data_clean"
    DB_PATH = DATA_CLEAN / "macrohub.db"


# =========================
# 页面配置
# =========================
st.set_page_config(
    page_title="MacroHub 全球宏观经济指标数据要素服务平台",
    layout="wide"
)

st.warning("旧版备份页面：请优先运行 dashboard/streamlit_app.py 或 dashboard/bigscreen_app.py；本文件仅用于历史回溯，避免作为当前平台入口。")


# =========================
# 科技风 CSS
# =========================
st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg, #0f172a 0%, #111827 45%, #020617 100%);
    color: #e5e7eb;
}
.block-container {
    padding-top: 2rem;
    padding-bottom: 3rem;
}
h1, h2, h3 {
    color: #f8fafc !important;
    font-weight: 800 !important;
}
p, label, span, div {
    color: #e5e7eb;
}
[data-testid="stMetric"] {
    background: linear-gradient(135deg, rgba(30,64,175,0.92), rgba(14,165,233,0.38));
    border: 1px solid rgba(125,211,252,0.45);
    padding: 22px;
    border-radius: 18px;
    box-shadow: 0 0 20px rgba(56,189,248,0.20);
}
[data-testid="stMetricValue"] {
    color: #ffffff !important;
    font-size: 34px !important;
    font-weight: 800 !important;
}
[data-testid="stMetricLabel"] {
    color: #bae6fd !important;
    font-size: 15px !important;
}
button[data-baseweb="tab"] {
    background-color: transparent;
    color: #cbd5e1 !important;
    font-weight: 650;
}
button[data-baseweb="tab"][aria-selected="true"] {
    color: #38bdf8 !important;
    border-bottom: 3px solid #38bdf8 !important;
}
div[data-baseweb="select"] > div {
    background-color: #0f172a !important;
    border: 1px solid #38bdf8 !important;
    color: #ffffff !important;
    border-radius: 10px !important;
}
div[data-baseweb="select"] span {
    color: #ffffff !important;
    font-size: 16px !important;
    font-weight: 600 !important;
}
div[data-baseweb="select"] input {
    color: #ffffff !important;
}
div[role="listbox"] {
    background-color: #0f172a !important;
    border: 1px solid #38bdf8 !important;
}
div[role="option"] {
    background-color: #0f172a !important;
    color: #ffffff !important;
}
div[role="option"]:hover {
    background-color: #1e293b !important;
}
.stSlider label, .stSlider span {
    color: #ffffff !important;
}
[data-testid="stDataFrame"] {
    border-radius: 16px;
    overflow: hidden;
    border: 1px solid rgba(148,163,184,0.25);
}
.stAlert {
    border-radius: 16px;
    background-color: rgba(30,64,175,0.35) !important;
    border: 1px solid rgba(56,189,248,0.25);
}
pre {
    background-color: #020617 !important;
    color: #dbeafe !important;
    border-radius: 16px !important;
    border: 1px solid rgba(56,189,248,0.25);
}
hr {
    border: none;
    height: 1px;
    background: linear-gradient(to right, transparent, #38bdf8, transparent);
}
.stDownloadButton button {
    background: linear-gradient(135deg, #2563eb, #06b6d4);
    color: white;
    border: none;
    border-radius: 12px;
    padding: 0.6rem 1.2rem;
    font-weight: 700;
}
.stDownloadButton button:hover {
    background: linear-gradient(135deg, #1d4ed8, #0891b2);
    color: white;
}
</style>
""", unsafe_allow_html=True)


# =========================
# 数据读取
# =========================
@st.cache_data
def load_data() -> pd.DataFrame:
    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql_query("SELECT * FROM macro_observations", conn)
    return df


def safe_col(df: pd.DataFrame, col: str, default=None):
    if col in df.columns:
        return df[col]
    return pd.Series([default] * len(df))


def format_number(x):
    if pd.isna(x):
        return "—"
    try:
        return f"{float(x):,.2f}"
    except Exception:
        return str(x)


def query_data(
    df_all: pd.DataFrame,
    country: str,
    indicator: str,
    frequency: str,
    source: str = "全部",
    start_year=None,
    end_year=None,
) -> pd.DataFrame:
    df = df_all[
        (df_all["country_code"] == country)
        & (df_all["indicator_code"] == indicator)
        & (df_all["frequency"] == frequency)
    ].copy()

    if source != "全部":
        df = df[df["source_organization"] == source].copy()

    df["date_int"] = pd.to_numeric(df["date"], errors="coerce")

    if start_year is not None:
        df = df[df["date_int"] >= int(start_year)]
    if end_year is not None:
        df = df[df["date_int"] <= int(end_year)]

    return df.sort_values(["source_organization", "date_int", "date"])


def get_valid_stats(df_query: pd.DataFrame):
    valid_df = df_query.dropna(subset=["value"]).copy()
    if valid_df.empty:
        return None

    valid_df["date_int"] = pd.to_numeric(valid_df["date"], errors="coerce")
    valid_df = valid_df.sort_values("date_int")

    latest_row = valid_df.iloc[-1]
    latest_value = latest_row["value"]
    latest_date = latest_row["date"]

    delta = None
    if len(valid_df) >= 2:
        prev_value = valid_df.iloc[-2]["value"]
        if pd.notna(prev_value):
            delta = latest_value - prev_value

    return {
        "latest_value": latest_value,
        "latest_date": latest_date,
        "delta": delta,
        "max_value": valid_df["value"].max(),
        "min_value": valid_df["value"].min(),
        "mean_value": valid_df["value"].mean(),
        "valid_count": len(valid_df),
        "start_year": int(valid_df["date_int"].min()),
        "end_year": int(valid_df["date_int"].max()),
    }


def build_json_output(df: pd.DataFrame, country, indicator, frequency, source):
    if df.empty:
        return {
            "request": {
                "country": country,
                "indicator_code": indicator,
                "frequency": frequency,
                "source": source,
            },
            "series": None,
            "error": {"message": "No data found."},
        }

    first = df.iloc[0].to_dict()

    observations = []
    for _, row in df.iterrows():
        val = row.get("value")
        observations.append({
            "date": str(row.get("date")),
            "value": None if pd.isna(val) else float(val),
            "status": row.get("status", "final"),
            "source_organization": row.get("source_organization", ""),
        })

    return {
        "request": {
            "country": country,
            "indicator_code": indicator,
            "frequency": frequency,
            "source": source,
        },
        "series": {
            "series_id": first.get("series_id", f"{country}.{indicator}"),
            "indicator_code": first.get("indicator_code", indicator),
            "indicator_name_zh": first.get("indicator_name_zh", ""),
            "indicator_name_en": first.get("indicator_name_en", ""),
            "country_name_zh": first.get("country_name_zh", ""),
            "country_name_en": first.get("country_name_en", ""),
            "country_code": first.get("country_code", country),
            "frequency": first.get("frequency", frequency),
            "unit": first.get("unit", ""),
            "seasonal_adjustment": first.get("seasonal_adjustment", ""),
            "calculation": first.get("calculation", ""),
            "source": {
                "organization": first.get("source_organization", ""),
                "dataset": first.get("source_dataset", ""),
                "source_series_code": first.get("source_indicator_code", ""),
                "source_url": first.get("source_url", ""),
            },
            "last_updated": first.get("last_updated", ""),
            "observations": observations,
        },
        "error": None,
    }


def build_lineage_sankey(df_lineage: pd.DataFrame):
    source_nodes = df_lineage["source_organization"].astype(str).unique().tolist()
    raw_nodes = (
        df_lineage["source_organization"].astype(str)
        + "："
        + df_lineage["source_indicator_code"].astype(str)
    ).unique().tolist()
    standard_nodes = df_lineage["indicator_code"].astype(str).unique().tolist()

    labels = source_nodes + raw_nodes + standard_nodes
    label_to_idx = {label: i for i, label in enumerate(labels)}

    source = []
    target = []
    value = []

    for _, row in df_lineage.iterrows():
        org = str(row["source_organization"])
        raw = f"{row['source_organization']}：{row['source_indicator_code']}"
        std = str(row["indicator_code"])

        if org in label_to_idx and raw in label_to_idx:
            source.append(label_to_idx[org])
            target.append(label_to_idx[raw])
            value.append(1)

        if raw in label_to_idx and std in label_to_idx:
            source.append(label_to_idx[raw])
            target.append(label_to_idx[std])
            value.append(1)

    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=25,
            thickness=18,
            line=dict(color="rgba(148,163,184,0.5)", width=0.5),
            label=labels,
            color=["#38bdf8"] * len(labels),
        ),
        link=dict(
            source=source,
            target=target,
            value=value,
            color="rgba(56,189,248,0.25)",
        ),
    )])

    fig.update_layout(
        title_text="指标血缘关系图：来源机构 → 原始指标 → 标准指标",
        font=dict(size=14, color="#e5e7eb"),
        paper_bgcolor="#0f172a",
        plot_bgcolor="#0f172a",
    )
    return fig


def infer_trend(valid_df: pd.DataFrame) -> str:
    if len(valid_df) < 3:
        return "样本较少，趋势不明显"

    valid_df = valid_df.sort_values("date_int")
    recent = valid_df.tail(min(5, len(valid_df)))
    start = recent.iloc[0]["value"]
    end = recent.iloc[-1]["value"]

    if pd.isna(start) or pd.isna(end):
        return "趋势不明显"

    diff = end - start
    std = valid_df["value"].std()
    threshold = 0.15 * std if pd.notna(std) and std > 0 else 0.01

    if diff > threshold:
        return "上升趋势"
    if diff < -threshold:
        return "下降趋势"
    return "相对稳定"


def infer_risk(indicator: str, latest_value: float, mean_value: float) -> str:
    if pd.isna(latest_value):
        return "未知"

    ind = indicator.upper()

    if "CPI" in ind:
        if latest_value >= 50:
            return "极高风险"
        if latest_value >= 10:
            return "高风险"
        if latest_value >= 5:
            return "中风险"
        return "低风险"

    if "UNEMPLOYMENT" in ind or "UEM" in ind:
        if latest_value >= 15:
            return "高风险"
        if latest_value >= 8:
            return "中风险"
        return "低风险"

    if "GDP" in ind and "GROWTH" in ind:
        if latest_value < -2:
            return "高风险"
        if latest_value < 0:
            return "中风险"
        return "低风险"

    if pd.notna(mean_value) and abs(mean_value) > 1e-9:
        ratio = abs(latest_value - mean_value) / abs(mean_value)
        if ratio > 1:
            return "高风险"
        if ratio > 0.4:
            return "中风险"
    return "低风险"


def generate_ai_text(df_query: pd.DataFrame, country: str, indicator: str):
    valid_df = df_query.dropna(subset=["value"]).copy()
    valid_df["date_int"] = pd.to_numeric(valid_df["date"], errors="coerce")
    valid_df = valid_df.dropna(subset=["date_int"]).sort_values("date_int")

    if valid_df.empty:
        return {
            "trend": "无有效数据",
            "risk": "未知",
            "summary": "当前查询条件下暂无有效观测值，无法生成智能解读。",
            "advice": "建议更换国家、指标或时间范围后重新查询。",
        }

    stats = get_valid_stats(valid_df)
    trend = infer_trend(valid_df)
    risk = infer_risk(indicator, stats["latest_value"], stats["mean_value"])

    country_name = valid_df.iloc[0].get("country_name_zh") or country
    indicator_name = valid_df.iloc[0].get("indicator_name_zh") or indicator
    unit = valid_df.iloc[0].get("unit") or ""
    sources = "、".join(sorted(valid_df["source_organization"].dropna().astype(str).unique().tolist()))

    summary = (
        f"{country_name}（{country}）的{indicator_name}（{indicator}）在 "
        f"{stats['start_year']}—{stats['end_year']} 期间共有 {stats['valid_count']} 条有效观测记录，"
        f"数据来源包括 {sources}。从最新数据看，该指标在 {stats['latest_date']} 年的数值为 "
        f"{format_number(stats['latest_value'])}{unit}，历史平均值为 {format_number(stats['mean_value'])}{unit}，"
        f"历史区间为 {format_number(stats['min_value'])}{unit}—{format_number(stats['max_value'])}{unit}。"
        f"趋势识别结果显示，该指标近期整体呈现{trend}。风险判断结果为{risk}。"
    )

    if risk in ["高风险", "极高风险"]:
        advice = "建议重点关注该指标的持续变化，并结合 GDP 增速、失业率、国际收支和政府债务等指标进行交叉验证。"
    elif risk == "中风险":
        advice = "建议持续监测指标边际变化，关注是否出现趋势反转或异常波动。"
    elif risk == "低风险":
        advice = "当前风险水平相对可控，可作为宏观经济状态跟踪的常规监测指标。"
    else:
        advice = "建议补充更多观测数据后再进行风险判断。"

    return {
        "trend": trend,
        "risk": risk,
        "summary": summary,
        "advice": advice,
    }


def build_asset_catalog(df_all: pd.DataFrame) -> pd.DataFrame:
    group_cols = ["indicator_code"]
    agg_dict = {
        "country_code": "nunique",
        "source_organization": "nunique",
        "value": "count",
        "date": ["min", "max", "count"],
    }

    asset = df_all.groupby(group_cols).agg(agg_dict)
    asset.columns = [
        "country_count",
        "source_count",
        "observation_count",
        "start_year",
        "end_year",
        "total_rows",
    ]
    asset = asset.reset_index()

    meta_cols = [
        "indicator_code",
        "indicator_name_zh",
        "indicator_name_en",
        "unit",
        "frequency",
    ]
    meta_cols = [c for c in meta_cols if c in df_all.columns]
    meta = df_all[meta_cols].drop_duplicates("indicator_code")

    asset = asset.merge(meta, on="indicator_code", how="left")
    asset["api_available"] = "是"
    asset["quality_score"] = ((asset["observation_count"] / asset["total_rows"].replace(0, pd.NA)) * 100).fillna(0).round(1)
    asset["quality_level"] = asset["quality_score"].apply(lambda x: "高" if x >= 85 else ("中" if x >= 60 else "低"))

    ordered = [
        "indicator_code", "indicator_name_zh", "indicator_name_en", "unit", "frequency",
        "country_count", "source_count", "observation_count", "total_rows",
        "start_year", "end_year", "quality_score", "quality_level", "api_available"
    ]
    return asset[[c for c in ordered if c in asset.columns]].sort_values(
        ["source_count", "country_count", "observation_count"], ascending=False
    )


def build_alerts(df_all: pd.DataFrame) -> pd.DataFrame:
    alerts = []

    # 缺失值预警
    miss = df_all.groupby("indicator_code")["value"].apply(lambda x: x.isna().mean()).reset_index(name="missing_rate")
    for _, row in miss.iterrows():
        if row["missing_rate"] >= 0.25:
            level = "高"
        elif row["missing_rate"] >= 0.10:
            level = "中"
        else:
            level = None
        if level:
            alerts.append({
                "预警类型": "缺失值预警",
                "预警对象": row["indicator_code"],
                "预警等级": level,
                "预警说明": f"该指标缺失率为 {row['missing_rate']:.1%}。",
                "处置建议": "建议检查来源数据完整性，必要时补充其他来源。"
            })

    # 多源覆盖不足
    src_count = df_all.groupby("indicator_code")["source_organization"].nunique().reset_index(name="source_count")
    for _, row in src_count.iterrows():
        if row["source_count"] < 2:
            alerts.append({
                "预警类型": "多源覆盖不足",
                "预警对象": row["indicator_code"],
                "预警等级": "中",
                "预警说明": "该指标当前仅有单一来源，难以进行多源交叉验证。",
                "处置建议": "建议引入 OECD、FRED 或其他官方来源。"
            })

    # 更新时间缺失
    if "last_updated" in df_all.columns:
        upd = df_all.groupby("source_organization")["last_updated"].apply(lambda x: x.isna().mean()).reset_index(name="missing_update_rate")
        for _, row in upd.iterrows():
            if row["missing_update_rate"] >= 0.5:
                alerts.append({
                    "预警类型": "更新时间缺失",
                    "预警对象": row["source_organization"],
                    "预警等级": "低",
                    "预警说明": f"该来源更新时间字段缺失率为 {row['missing_update_rate']:.1%}。",
                    "处置建议": "建议完善元数据更新时间字段。"
                })

    # 多源偏差预警
    multi_inds = src_count[src_count["source_count"] >= 2]["indicator_code"].tolist()
    for ind in multi_inds:
        tmp = df_all[df_all["indicator_code"] == ind].dropna(subset=["value"]).copy()
        pivot = tmp.pivot_table(index=["country_code", "date"], columns="source_organization", values="value")
        if pivot.shape[1] >= 2:
            common = pivot.dropna()
            if not common.empty:
                cols = common.columns.tolist()
                s1, s2 = cols[0], cols[1]
                denominator = common[[s1, s2]].mean(axis=1).abs().replace(0, pd.NA)
                pct_diff = ((common[s1] - common[s2]).abs() / denominator * 100).dropna()
                if not pct_diff.empty and pct_diff.mean() >= 15:
                    alerts.append({
                        "预警类型": "多源偏差预警",
                        "预警对象": ind,
                        "预警等级": "高",
                        "预警说明": f"多源共同观测期平均偏差率为 {pct_diff.mean():.2f}%。",
                        "处置建议": "建议检查指标口径、发布时间差异或预测值与历史值差异。"
                    })

    return pd.DataFrame(alerts)



def get_chinese_pdf_font() -> str:
    """Register a Chinese font for ReportLab when available."""
    if not REPORTLAB_AVAILABLE:
        return "Helvetica"

    font_candidates = [
        r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\simhei.ttf",
        r"C:\Windows\Fonts\simsun.ttc",
        r"C:\Windows\Fonts\msyh.ttf",
    ]

    for font_path in font_candidates:
        p = Path(font_path)
        if p.exists():
            try:
                pdfmetrics.registerFont(TTFont("ChineseFont", str(p)))
                return "ChineseFont"
            except Exception:
                continue

    return "Helvetica"


def build_pdf_report(
    title: str,
    summary: str,
    stats_rows: list,
    ai_summary: str,
    risk_level: str,
    trend: str,
    advice: str,
    governance_note: str,
) -> bytes:
    """Generate a PDF report as bytes."""
    if not REPORTLAB_AVAILABLE:
        raise RuntimeError("当前环境未安装 reportlab，请先运行：pip install reportlab")

    buffer = BytesIO()
    font_name = get_chinese_pdf_font()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.6 * cm,
        leftMargin=1.6 * cm,
        topMargin=1.6 * cm,
        bottomMargin=1.6 * cm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "MacroHubTitle",
        parent=styles["Title"],
        fontName=font_name,
        fontSize=20,
        leading=28,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=16,
    )
    h_style = ParagraphStyle(
        "MacroHubHeading",
        parent=styles["Heading2"],
        fontName=font_name,
        fontSize=14,
        leading=20,
        textColor=colors.HexColor("#1d4ed8"),
        spaceBefore=12,
        spaceAfter=8,
    )
    body_style = ParagraphStyle(
        "MacroHubBody",
        parent=styles["BodyText"],
        fontName=font_name,
        fontSize=10.5,
        leading=18,
        textColor=colors.HexColor("#111827"),
        spaceAfter=8,
    )

    story = []
    story.append(Paragraph(title, title_style))
    story.append(Paragraph("报告由 MacroHub 全球宏观经济指标数据要素服务平台自动生成", body_style))
    story.append(Spacer(1, 8))

    story.append(Paragraph("一、报告摘要", h_style))
    story.append(Paragraph(summary.replace("\n", "<br/>"), body_style))

    story.append(Paragraph("二、核心统计", h_style))
    table_data = [["项目", "内容"]] + stats_rows
    table = Table(table_data, colWidths=[5 * cm, 10 * cm])
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1d4ed8")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f8fafc")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(table)

    story.append(Paragraph("三、AI 自动解读", h_style))
    story.append(Paragraph(ai_summary.replace("\n", "<br/>"), body_style))

    story.append(Paragraph("四、风险等级", h_style))
    story.append(Paragraph(f"当前风险等级判断为：{risk_level}", body_style))

    story.append(Paragraph("五、趋势判断", h_style))
    story.append(Paragraph(f"系统识别该指标近期整体呈现：{trend}", body_style))

    story.append(Paragraph("六、风险处置建议", h_style))
    story.append(Paragraph(advice.replace("\n", "<br/>"), body_style))

    story.append(Paragraph("七、数据治理说明", h_style))
    story.append(Paragraph(governance_note.replace("\n", "<br/>"), body_style))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


# =========================
# 主程序
# =========================
try:
    df_all = load_data()
except Exception as e:
    st.error(f"数据库读取失败：{e}")
    st.stop()

# 基础类型处理
if "value" in df_all.columns:
    df_all["value"] = pd.to_numeric(df_all["value"], errors="coerce")
df_all["date"] = df_all["date"].astype(str)

st.title("MacroHub 全球宏观经济指标数据要素服务平台")
st.caption("多源采集 · 指标标准化 · 元数据治理 · JSON 结构化输出")

k1, k2, k3, k4 = st.columns(4)
k1.metric("数据源数量", df_all["source_organization"].nunique())
k2.metric("标准指标数", df_all["indicator_code"].nunique())
k3.metric("国家覆盖数", df_all["country_code"].nunique())
k4.metric("总观测值", f"{len(df_all):,}")

st.markdown("---")

countries = sorted(df_all["country_code"].dropna().unique().tolist())
indicators = sorted(df_all["indicator_code"].dropna().unique().tolist())
frequencies = sorted(df_all["frequency"].dropna().unique().tolist())
sources = ["全部"] + sorted(df_all["source_organization"].dropna().unique().tolist())

tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10, tab11, tab12, tab13 = st.tabs([
    "指标查询",
    "指标字典",
    "数据质量",
    "JSON输出",
    "一致性分析",
    "治理驾驶舱",
    "指标血缘",
    "治理规则",
    "API服务中心",
    "数据资产目录",
    "风险预警",
    "智能分析",
    "智能报告",
])


# =========================
# TAB1 指标查询
# =========================
with tab1:
    st.subheader("指标查询与趋势分析")

    c1, c2, c3, c4 = st.columns(4)
    country = c1.selectbox("国家/地区", countries)
    indicator = c2.selectbox("标准指标", indicators)
    frequency = c3.selectbox("频率", frequencies)
    source_selected = c4.selectbox("数据来源", sources)

    date_num = pd.to_numeric(df_all["date"], errors="coerce").dropna()
    min_year = int(date_num.min()) if not date_num.empty else 1980
    max_year = int(date_num.max()) if not date_num.empty else 2031

    start_year, end_year = st.slider(
        "时间范围",
        min_value=min_year,
        max_value=max_year,
        value=(min_year, max_year),
    )

    df_query = query_data(df_all, country, indicator, frequency, source_selected, start_year, end_year)

    st.markdown("## 查询结果")
    if df_query.empty:
        st.warning("当前查询条件下没有数据。")
    else:
        stats = get_valid_stats(df_query)

        if stats:
            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric(f"最新有效值（{stats['latest_date']}）", format_number(stats["latest_value"]), delta=None if stats["delta"] is None else format_number(stats["delta"]))
            m2.metric("历史最大值", format_number(stats["max_value"]))
            m3.metric("历史最小值", format_number(stats["min_value"]))
            m4.metric("历史平均值", format_number(stats["mean_value"]))
            m5.metric("有效观测值数量", stats["valid_count"])

        chart_df = df_query.dropna(subset=["value"]).copy()
        if chart_df.empty:
            st.warning("当前查询结果没有可绘制的有效数值。")
        else:
            fig = px.line(
                chart_df,
                x="date",
                y="value",
                color="source_organization",
                markers=True,
                title=f"{country} - {indicator} 趋势分析",
            )
            fig.update_layout(plot_bgcolor="#0f172a", paper_bgcolor="#0f172a", font_color="#e5e7eb")
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("### 数据来源与元数据")
        meta_cols = [
            "source_organization", "source_dataset", "source_indicator_code",
            "unit", "frequency", "seasonal_adjustment", "calculation", "last_updated"
        ]
        meta_cols = [c for c in meta_cols if c in df_query.columns]
        st.dataframe(df_query[meta_cols].drop_duplicates(), use_container_width=True)

        st.markdown("### 标准化观测数据")
        st.dataframe(df_query.drop(columns=["date_int"], errors="ignore"), use_container_width=True)

        csv_data = df_query.drop(columns=["date_int"], errors="ignore").to_csv(index=False, encoding="utf-8-sig")
        st.download_button(
            "下载查询结果 CSV",
            data=csv_data,
            file_name=f"{country}_{indicator}_{frequency}_{source_selected}.csv",
            mime="text/csv",
        )


# =========================
# TAB2 指标字典
# =========================
with tab2:
    st.subheader("指标字典")
    dict_cols = [
        "indicator_code", "indicator_name_zh", "indicator_name_en",
        "unit", "frequency", "seasonal_adjustment", "calculation",
        "source_organization", "source_dataset", "source_indicator_code", "source_url"
    ]
    existing_cols = [c for c in dict_cols if c in df_all.columns]
    st.dataframe(df_all[existing_cols].drop_duplicates().sort_values(existing_cols[:1]), use_container_width=True)


# =========================
# TAB3 数据质量
# =========================
with tab3:
    st.subheader("数据质量概览")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("总观测值数量", len(df_all))
    c2.metric("国家/地区数量", df_all["country_code"].nunique())
    c3.metric("标准指标数量", df_all["indicator_code"].nunique())
    c4.metric("来源机构数量", df_all["source_organization"].nunique())

    st.markdown("### 缺失值统计")
    missing = df_all.isna().sum().reset_index()
    missing.columns = ["字段", "缺失数量"]
    st.dataframe(missing, use_container_width=True)

    st.markdown("### 数据来源覆盖")
    source_coverage = (
        df_all.groupby(["source_organization", "source_dataset"])
        .agg(rows=("value", "count"), countries=("country_code", "nunique"), indicators=("indicator_code", "nunique"))
        .reset_index()
    )
    st.dataframe(source_coverage, use_container_width=True)


# =========================
# TAB4 JSON输出
# =========================
with tab4:
    st.subheader("标准化 JSON 输出")
    c1, c2, c3, c4 = st.columns(4)
    json_country = c1.selectbox("国家", countries, key="json_country")
    json_indicator = c2.selectbox("指标", indicators, key="json_indicator")
    json_frequency = c3.selectbox("频率", frequencies, key="json_frequency")
    json_source = c4.selectbox("数据来源", sources, key="json_source")

    df_json = query_data(df_all, json_country, json_indicator, json_frequency, json_source)
    json_output = build_json_output(df_json, json_country, json_indicator, json_frequency, json_source)
    st.json(json_output)

    json_str = json.dumps(json_output, ensure_ascii=False, indent=2)
    st.download_button(
        "下载 JSON",
        data=json_str,
        file_name=f"{json_country}_{json_indicator}_{json_frequency}_{json_source}.json",
        mime="application/json",
    )


# =========================
# TAB5 一致性分析
# =========================
with tab5:
    st.subheader("多源指标一致性分析")

    multi_source_indicators = (
        df_all.groupby("indicator_code")["source_organization"].nunique()
    )
    multi_source_indicators = multi_source_indicators[multi_source_indicators >= 2].index.tolist()

    if not multi_source_indicators:
        st.warning("当前没有可进行多源一致性分析的指标。")
    else:
        c1, c2 = st.columns(2)
        compare_country = c1.selectbox("国家", countries, key="compare_country")
        compare_indicator = c2.selectbox("标准指标", multi_source_indicators, key="compare_indicator")

        df_compare = df_all[
            (df_all["country_code"] == compare_country)
            & (df_all["indicator_code"] == compare_indicator)
        ].dropna(subset=["value"]).copy()

        if df_compare.empty:
            st.warning("没有找到可对比数据。")
        else:
            fig = px.line(
                df_compare,
                x="date",
                y="value",
                color="source_organization",
                markers=True,
                title=f"{compare_country} - {compare_indicator} 多来源对比",
            )
            fig.update_layout(plot_bgcolor="#0f172a", paper_bgcolor="#0f172a", font_color="#e5e7eb")
            st.plotly_chart(fig, use_container_width=True)

            pivot_df = df_compare.pivot_table(index="date", columns="source_organization", values="value")
            if pivot_df.shape[1] >= 2:
                common_df = pivot_df.dropna().copy()
                cols = common_df.columns.tolist()

                if len(cols) >= 2 and not common_df.empty:
                    s1, s2 = cols[0], cols[1]
                    common_df["abs_diff"] = (common_df[s1] - common_df[s2]).abs()
                    denominator = common_df[[s1, s2]].mean(axis=1).abs().replace(0, pd.NA)
                    common_df["pct_diff"] = common_df["abs_diff"] / denominator * 100

                    avg_diff = common_df["pct_diff"].mean()
                    corr = common_df[[s1, s2]].corr().iloc[0, 1]

                    d1, d2, d3 = st.columns(3)
                    d1.metric("共同观测期数量", len(common_df))
                    d2.metric("平均偏差率 (%)", f"{avg_diff:.2f}")
                    d3.metric("相关系数", f"{corr:.4f}")

                    st.dataframe(common_df.reset_index(), use_container_width=True)


# =========================
# TAB6 治理驾驶舱
# =========================
with tab6:
    st.subheader("数据治理驾驶舱")

    missing_rate = df_all["value"].isna().mean()
    duplicate_rate = df_all.duplicated(
        subset=["country_code", "indicator_code", "date", "source_organization"]
    ).mean()
    source_coverage_mean = df_all.groupby("indicator_code")["source_organization"].nunique().mean()

    completeness_score = round((1 - missing_rate) * 100, 1)
    consistency_score = round(min(source_coverage_mean / 2, 1) * 100, 1)
    uniqueness_score = round((1 - duplicate_rate) * 100, 1)
    total_score = round(completeness_score * 0.4 + consistency_score * 0.3 + uniqueness_score * 0.3, 1)

    q1, q2, q3, q4 = st.columns(4)
    q1.metric("完整性评分", completeness_score)
    q2.metric("一致性评分", consistency_score)
    q3.metric("唯一性评分", uniqueness_score)
    q4.metric("综合评分", f"{total_score}/100")

    st.markdown("### 缺失值统计")
    missing_df = df_all.groupby("indicator_code")["value"].apply(lambda x: x.isna().sum()).reset_index()
    missing_df.columns = ["indicator_code", "missing_count"]
    fig_missing = px.bar(missing_df, x="indicator_code", y="missing_count", title="指标缺失值统计")
    fig_missing.update_layout(plot_bgcolor="#0f172a", paper_bgcolor="#0f172a", font_color="#e5e7eb")
    st.plotly_chart(fig_missing, use_container_width=True)

    st.markdown("### 多源覆盖统计")
    coverage_df = df_all.groupby("indicator_code")["source_organization"].nunique().reset_index()
    coverage_df.columns = ["indicator_code", "source_count"]
    fig_cov = px.bar(coverage_df, x="indicator_code", y="source_count", title="标准指标多源覆盖情况")
    fig_cov.update_layout(plot_bgcolor="#0f172a", paper_bgcolor="#0f172a", font_color="#e5e7eb")
    st.plotly_chart(fig_cov, use_container_width=True)

    st.info("MacroHub 已实现多源宏观经济数据采集、标准指标统一治理、数据缺失检测、多源一致性分析、数据质量评分、元数据管理、JSON 结构化服务输出和可视化分析。")


# =========================
# TAB7 指标血缘
# =========================
with tab7:
    st.subheader("指标血缘关系图")

    lineage_cols = [
        "source_organization", "source_dataset", "source_indicator_code",
        "source_indicator_name", "indicator_code", "indicator_name_zh",
        "indicator_name_en", "unit", "frequency", "calculation"
    ]
    existing_lineage_cols = [c for c in lineage_cols if c in df_all.columns]

    lineage_df = df_all[existing_lineage_cols].drop_duplicates().copy()
    lineage_indicators = sorted(lineage_df["indicator_code"].dropna().unique().tolist())

    selected_lineage_indicator = st.selectbox("选择标准指标", lineage_indicators, key="lineage_indicator")
    selected_lineage_df = lineage_df[lineage_df["indicator_code"] == selected_lineage_indicator].copy()

    if selected_lineage_df.empty:
        st.warning("当前指标暂无血缘信息。")
    else:
        fig_lineage = build_lineage_sankey(selected_lineage_df)
        st.plotly_chart(fig_lineage, use_container_width=True)

        st.markdown("### 血缘明细表")
        st.dataframe(selected_lineage_df, use_container_width=True)

        st.info("该图展示了标准指标的来源链路：来源机构 → 原始指标代码 → 平台标准指标编码。")


# =========================
# TAB8 治理规则
# =========================
with tab8:
    st.subheader("治理规则中心")

    st.info("治理规则中心用于展示平台如何将 IMF、World Bank 等不同来源的异构指标统一治理为平台标准指标体系。")

    rule_data = [
        {"规则类型": "指标映射", "来源": "IMF", "原始字段/指标": "PCPIPCH", "标准字段/指标": "CPI_YOY_A", "治理说明": "IMF 居民消费价格指数同比统一映射为平台 CPI 同比指标。"},
        {"规则类型": "指标映射", "来源": "World Bank", "原始字段/指标": "FP.CPI.TOTL.ZG", "标准字段/指标": "CPI_YOY_A", "治理说明": "World Bank CPI inflation 指标统一映射为平台 CPI 同比指标。"},
        {"规则类型": "指标映射", "来源": "IMF", "原始字段/指标": "NGDP_RPCH", "标准字段/指标": "GDP_REAL_GROWTH_YOY_A", "治理说明": "IMF 实际 GDP 增速统一映射为平台实际 GDP 同比增速指标。"},
        {"规则类型": "指标映射", "来源": "IMF", "原始字段/指标": "LUR", "标准字段/指标": "UNEMPLOYMENT_RATE_A", "治理说明": "IMF 失业率指标统一映射为平台失业率指标。"},
        {"规则类型": "频率统一", "来源": "All Sources", "原始字段/指标": "Annual / Yearly", "标准字段/指标": "A", "治理说明": "年度数据统一编码为 A。"},
        {"规则类型": "单位统一", "来源": "All Sources", "原始字段/指标": "Percent / % / Percentage", "标准字段/指标": "%", "治理说明": "百分比类指标统一采用 % 作为单位。"},
        {"规则类型": "缺失值处理", "来源": "All Sources", "原始字段/指标": "空值 / n/a / --", "标准字段/指标": "None / NaN", "治理说明": "缺失值统一转换为空值，并在统计分析和趋势图中自动忽略。"},
        {"规则类型": "多源冲突处理", "来源": "IMF / World Bank", "原始字段/指标": "同一指标多来源数值差异", "标准字段/指标": "一致性分析", "治理说明": "通过共同观测期、平均偏差率和相关系数评估多源数据一致性。"},
        {"规则类型": "数据血缘", "来源": "All Sources", "原始字段/指标": "source_organization + source_indicator_code", "标准字段/指标": "indicator_code", "治理说明": "保留来源机构、原始指标代码和标准指标代码，形成可追溯血缘链路。"},
    ]
    rule_df = pd.DataFrame(rule_data)

    st.markdown("### 治理规则明细")
    st.dataframe(rule_df, use_container_width=True)

    st.markdown("### 治理规则分类统计")
    rule_count = rule_df["规则类型"].value_counts().reset_index()
    rule_count.columns = ["规则类型", "规则数量"]
    fig_rule = px.bar(rule_count, x="规则类型", y="规则数量", title="治理规则类型分布")
    fig_rule.update_layout(plot_bgcolor="#0f172a", paper_bgcolor="#0f172a", font_color="#e5e7eb")
    st.plotly_chart(fig_rule, use_container_width=True)

    st.markdown("### 数据治理流程")
    st.code("""
原始数据接入
    ↓
字段结构识别
    ↓
来源指标解析
    ↓
标准指标映射
    ↓
单位与频率统一
    ↓
缺失值与异常值处理
    ↓
元数据补全
    ↓
标准化入库
    ↓
JSON/API 服务输出
""")

    st.success("通过治理规则中心，平台能够清晰展示异构数据如何被统一治理为标准数据资产。")


# =========================
# TAB9 API服务中心
# =========================
with tab9:
    st.subheader("API服务中心")

    st.info("API 服务中心用于展示平台对外提供标准化数据服务的能力。用户可以通过统一接口查询国家、指标、频率、来源和时间范围，并获得标准化 JSON 输出。")

    st.markdown("### 接口地址")
    st.code("GET http://127.0.0.1:8000/query")

    st.markdown("### 请求参数")
    api_params = pd.DataFrame([
        {"参数名": "country", "是否必填": "是", "说明": "国家或地区代码，如 CN、US、AR"},
        {"参数名": "indicator", "是否必填": "是", "说明": "平台标准指标代码，如 CPI_YOY_A"},
        {"参数名": "frequency", "是否必填": "否", "说明": "频率代码，如 A、Q、M"},
        {"参数名": "source", "是否必填": "否", "说明": "数据来源，如 IMF、World Bank"},
        {"参数名": "start", "是否必填": "否", "说明": "开始年份，如 2015"},
        {"参数名": "end", "是否必填": "否", "说明": "结束年份，如 2024"},
    ])
    st.dataframe(api_params, use_container_width=True)

    st.markdown("### 示例请求")
    st.code("http://127.0.0.1:8000/query?country=AR&indicator=CPI_YOY_A&frequency=A")

    st.markdown("### 示例返回 JSON")
    sample_json = {
        "request": {"country": "AR", "indicator_code": "CPI_YOY_A", "frequency": "A"},
        "series": {
            "indicator_name_zh": "居民消费价格指数同比",
            "country_code": "AR",
            "unit": "%",
            "source": {"organization": "IMF / World Bank"},
            "observations": [
                {"date": "2022", "value": 72.4},
                {"date": "2023", "value": 133.5},
                {"date": "2024", "value": 219.9},
            ],
        },
        "error": None,
    }
    st.json(sample_json)

    st.success("通过 API 服务中心，MacroHub 不仅能够实现可视化查询，还能够以标准化 JSON 格式对外提供数据服务。")


# =========================
# TAB10 数据资产目录
# =========================
with tab10:
    st.subheader("数据资产目录")

    st.info("数据资产目录用于将平台中的标准宏观指标沉淀为可管理、可查询、可调用的数据资产。每一项资产均包含覆盖国家、来源数量、观测规模、质量评分和 API 可调用状态等信息。")

    asset_df = build_asset_catalog(df_all)

    asset_count = len(asset_df)
    api_count = int((asset_df["api_available"] == "是").sum()) if "api_available" in asset_df.columns else asset_count
    multi_source_count = int((asset_df["source_count"] >= 2).sum()) if "source_count" in asset_df.columns else 0
    high_quality_count = int((asset_df["quality_level"] == "高").sum()) if "quality_level" in asset_df.columns else 0

    a1, a2, a3, a4 = st.columns(4)
    a1.metric("数据资产数量", asset_count)
    a2.metric("可 API 调用资产", api_count)
    a3.metric("多源资产数量", multi_source_count)
    a4.metric("高质量资产数量", high_quality_count)

    st.markdown("### 数据资产明细")
    st.dataframe(asset_df, use_container_width=True)

    st.markdown("### 数据资产多源覆盖")
    fig_asset = px.bar(asset_df, x="indicator_code", y="source_count", title="各标准指标来源覆盖数量")
    fig_asset.update_layout(plot_bgcolor="#0f172a", paper_bgcolor="#0f172a", font_color="#e5e7eb")
    st.plotly_chart(fig_asset, use_container_width=True)


# =========================
# TAB11 风险预警
# =========================
with tab11:
    st.subheader("数据质量风险预警中心")

    st.info("风险预警中心用于自动识别宏观数据资产中的潜在治理问题，包括缺失值异常、多源覆盖不足、更新时间缺失以及多源数值偏差过大等情况。")

    alert_df = build_alerts(df_all)

    if alert_df.empty:
        st.success("当前未识别到明显数据质量风险。")
    else:
        total_alerts = len(alert_df)
        high_alerts = int((alert_df["预警等级"] == "高").sum())
        mid_alerts = int((alert_df["预警等级"] == "中").sum())
        low_alerts = int((alert_df["预警等级"] == "低").sum())

        r1, r2, r3, r4 = st.columns(4)
        r1.metric("预警总数", total_alerts)
        r2.metric("高等级预警", high_alerts)
        r3.metric("中等级预警", mid_alerts)
        r4.metric("低等级预警", low_alerts)

        st.markdown("### 预警明细")
        st.dataframe(alert_df, use_container_width=True)

        level_count = alert_df["预警等级"].value_counts().reset_index()
        level_count.columns = ["预警等级", "数量"]
        fig_alert = px.bar(level_count, x="预警等级", y="数量", title="风险预警等级分布")
        fig_alert.update_layout(plot_bgcolor="#0f172a", paper_bgcolor="#0f172a", font_color="#e5e7eb")
        st.plotly_chart(fig_alert, use_container_width=True)


# =========================
# TAB12 智能分析
# =========================
with tab12:
    st.subheader("AI 智能分析")

    c1, c2, c3, c4 = st.columns(4)
    ai_country = c1.selectbox("国家/地区", countries, key="ai_country")
    ai_indicator = c2.selectbox("标准指标", indicators, key="ai_indicator")
    ai_frequency = c3.selectbox("频率", frequencies, key="ai_frequency")
    ai_source = c4.selectbox("数据来源", sources, key="ai_source")

    ai_df = query_data(df_all, ai_country, ai_indicator, ai_frequency, ai_source)
    valid_ai_df = ai_df.dropna(subset=["value"]).copy()

    if valid_ai_df.empty:
        st.warning("当前查询条件下没有可用于智能分析的有效数据。")
    else:
        valid_ai_df["date_int"] = pd.to_numeric(valid_ai_df["date"], errors="coerce")
        valid_ai_df = valid_ai_df.dropna(subset=["date_int"]).sort_values("date_int")

        fig_ai = px.line(valid_ai_df, x="date", y="value", color="source_organization", markers=True, title=f"{ai_country} - {ai_indicator} 智能趋势分析")
        fig_ai.update_layout(plot_bgcolor="#0f172a", paper_bgcolor="#0f172a", font_color="#e5e7eb")
        st.plotly_chart(fig_ai, use_container_width=True)

        ai_result = generate_ai_text(valid_ai_df, ai_country, ai_indicator)

        s1, s2 = st.columns(2)
        s1.metric("趋势识别", ai_result["trend"])
        s2.metric("风险等级", ai_result["risk"])

        st.markdown("### AI 自动解读")
        st.info(ai_result["summary"])

        st.markdown("### 风险处置建议")
        st.success(ai_result["advice"])


# =========================
# TAB13 智能报告
# =========================
with tab13:
    st.subheader("智能报告生成中心")

    st.info("智能报告中心用于将指标查询、趋势分析、风险判断、数据来源和治理信息自动整合为可下载的宏观分析报告。")

    c1, c2, c3, c4 = st.columns(4)
    report_country = c1.selectbox("国家/地区", countries, key="report_country")
    report_indicator = c2.selectbox("标准指标", indicators, key="report_indicator")
    report_frequency = c3.selectbox("频率", frequencies, key="report_frequency")
    report_source = c4.selectbox("数据来源", sources, key="report_source")

    report_df = query_data(df_all, report_country, report_indicator, report_frequency, report_source)
    report_valid = report_df.dropna(subset=["value"]).copy()

    if report_valid.empty:
        st.warning("当前查询条件下暂无有效数据，无法生成报告。")
    else:
        report_valid["date_int"] = pd.to_numeric(report_valid["date"], errors="coerce")
        report_valid = report_valid.dropna(subset=["date_int"]).sort_values("date_int")

        report_stats = get_valid_stats(report_valid)
        ai_result = generate_ai_text(report_valid, report_country, report_indicator)

        country_name = report_valid.iloc[0].get("country_name_zh") or report_country
        indicator_name = report_valid.iloc[0].get("indicator_name_zh") or report_indicator
        unit = report_valid.iloc[0].get("unit") or ""
        source_text = "、".join(sorted(report_valid["source_organization"].dropna().astype(str).unique().tolist()))

        report_md = f"""# {country_name}（{report_country}）{indicator_name}智能分析报告

## 一、报告摘要

本报告基于 MacroHub 全球宏观经济指标数据要素服务平台，对 **{country_name}（{report_country}）** 的 **{indicator_name}（{report_indicator}）** 进行趋势分析、风险识别与数据治理说明。数据来源包括：**{source_text}**。

## 二、核心统计

- 指标代码：{report_indicator}
- 频率：{report_frequency}
- 数据来源：{source_text}
- 有效观测数量：{report_stats['valid_count']}
- 时间范围：{report_stats['start_year']}—{report_stats['end_year']}
- 最新值：{format_number(report_stats['latest_value'])}{unit}
- 历史均值：{format_number(report_stats['mean_value'])}{unit}
- 历史最大值：{format_number(report_stats['max_value'])}{unit}
- 历史最小值：{format_number(report_stats['min_value'])}{unit}

## 三、AI 自动解读

{ai_result['summary']}

## 四、风险等级

当前风险等级判断为：**{ai_result['risk']}**。

## 五、趋势判断

系统识别该指标近期整体呈现：**{ai_result['trend']}**。

## 六、风险处置建议

{ai_result['advice']}

## 七、数据治理说明

平台已对 IMF、World Bank 等来源数据进行标准化治理，包括指标编码统一、频率统一、单位统一、元数据保留、多源一致性分析和 JSON/API 结构化输出。

---
报告由 MacroHub 自动生成。
"""

        st.markdown("### 报告预览")
        st.markdown(report_md)

        st.download_button(
            "下载 Markdown 报告",
            data=report_md,
            file_name=f"{report_country}_{report_indicator}_report.md",
            mime="text/markdown",
        )

        # PDF 报告下载
        if REPORTLAB_AVAILABLE:
            governance_note = (
                "平台已对 IMF、World Bank 等来源数据进行标准化治理，包括指标编码统一、"
                "频率统一、单位统一、元数据保留、多源一致性分析和 JSON/API 结构化输出。"
            )

            stats_rows = [
                ["指标代码", str(report_indicator)],
                ["频率", str(report_frequency)],
                ["数据来源", str(source_text)],
                ["有效观测数量", str(report_stats["valid_count"])],
                ["时间范围", f"{report_stats['start_year']}—{report_stats['end_year']}"],
                ["最新值", f"{format_number(report_stats['latest_value'])}{unit}"],
                ["历史均值", f"{format_number(report_stats['mean_value'])}{unit}"],
                ["历史最大值", f"{format_number(report_stats['max_value'])}{unit}"],
                ["历史最小值", f"{format_number(report_stats['min_value'])}{unit}"],
            ]

            pdf_title = f"{country_name}（{report_country}）{indicator_name}智能分析报告"

            pdf_bytes = build_pdf_report(
                title=pdf_title,
                summary=(
                    f"本报告基于 MacroHub 全球宏观经济指标数据要素服务平台，对 "
                    f"{country_name}（{report_country}）的 {indicator_name}（{report_indicator}）"
                    f"进行趋势分析、风险识别与数据治理说明。数据来源包括：{source_text}。"
                ),
                stats_rows=stats_rows,
                ai_summary=ai_result["summary"],
                risk_level=ai_result["risk"],
                trend=ai_result["trend"],
                advice=ai_result["advice"],
                governance_note=governance_note,
            )

            st.download_button(
                "下载 PDF 报告",
                data=pdf_bytes,
                file_name=f"{report_country}_{report_indicator}_report.pdf",
                mime="application/pdf",
            )
        else:
            st.warning("当前环境未安装 reportlab，暂无法生成 PDF。请在终端运行：pip install reportlab")

        report_json = {
            "country": report_country,
            "indicator": report_indicator,
            "frequency": report_frequency,
            "source": report_source,
            "stats": report_stats,
            "ai_analysis": ai_result,
        }
        st.download_button(
            "下载 JSON 报告",
            data=json.dumps(report_json, ensure_ascii=False, indent=2),
            file_name=f"{report_country}_{report_indicator}_report.json",
            mime="application/json",
        )

        report_csv = report_valid.drop(columns=["date_int"], errors="ignore").to_csv(index=False, encoding="utf-8-sig")
        st.download_button(
            "下载报告数据 CSV",
            data=report_csv,
            file_name=f"{report_country}_{report_indicator}_report_data.csv",
            mime="text/csv",
        )
