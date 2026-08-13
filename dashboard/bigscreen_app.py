# -*- coding: utf-8 -*-
"""
EconAtlas big-screen command dashboard.

Run:
    streamlit run dashboard/bigscreen_app.py
"""

from __future__ import annotations

import json
import math
import sqlite3
from datetime import datetime
from io import BytesIO
from pathlib import Path
from urllib.parse import quote
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    REPORTLAB_AVAILABLE = True
except Exception:
    REPORTLAB_AVAILABLE = False


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_CLEAN = BASE_DIR / "data_clean"
METADATA_DIR = BASE_DIR / "metadata"
DB_PATH = DATA_CLEAN / "macrohub.db"

COUNTRY_COORDS = {
    "US": (37.0902, -95.7129),
    "CN": (35.8617, 104.1954),
    "JP": (36.2048, 138.2529),
    "DE": (51.1657, 10.4515),
    "GB": (55.3781, -3.4360),
    "IN": (20.5937, 78.9629),
    "VN": (14.0583, 108.2772),
    "ID": (-0.7893, 113.9213),
    "MX": (23.6345, -102.5528),
    "BR": (-14.2350, -51.9253),
    "ZA": (-30.5595, 22.9375),
    "TR": (38.9637, 35.2433),
    "AR": (-38.4161, -63.6167),
    "SA": (23.8859, 45.0792),
    "FR": (46.2276, 2.2137),
    "IT": (41.8719, 12.5674),
    "ES": (40.4637, -3.7492),
    "EA": (50.1109, 8.6821),
}

MODULES = [
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
    "资产评级",
    "指标对齐审核",
]


st.set_page_config(
    page_title="EconAtlas 数据要素大屏",
    page_icon="EA",
    layout="wide",
    initial_sidebar_state="collapsed",
)


@st.cache_data
def load_observations() -> pd.DataFrame:
    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql_query("SELECT * FROM macro_observations", conn)
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df["date"] = df["date"].astype(str)
    df["date_year"] = pd.to_numeric(df["date"].str.extract(r"^(\d{4})", expand=False), errors="coerce")
    return df


@st.cache_data
def load_csv(name: str) -> pd.DataFrame:
    path = METADATA_DIR / name
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, encoding="utf-8-sig", low_memory=False)


@st.cache_data
def load_quality_report() -> pd.DataFrame:
    path = DATA_CLEAN / "quality_report.csv"
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, encoding="utf-8-sig", low_memory=False)


@st.cache_data
def load_clean_csv(name: str) -> pd.DataFrame:
    path = DATA_CLEAN / name
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, encoding="utf-8-sig", low_memory=False)


@st.cache_data
def load_update_status() -> dict:
    path = METADATA_DIR / "update_status.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def fmt_int(value) -> str:
    try:
        return f"{int(value):,}"
    except Exception:
        return "-"


def fmt_float(value, digits: int = 2) -> str:
    try:
        return f"{float(value):,.{digits}f}"
    except Exception:
        return "-"


def compact_number(value) -> str:
    try:
        value = float(value)
    except Exception:
        return "-"
    abs_value = abs(value)
    if abs_value >= 1e12:
        return f"{value / 1e12:.2f}万亿"
    if abs_value >= 1e8:
        return f"{value / 1e8:.2f}亿"
    if abs_value >= 1e4:
        return f"{value / 1e4:.2f}万"
    return f"{value:.2f}"


def short_text(value, max_len: int = 18) -> str:
    text = "" if pd.isna(value) else str(value)
    return text if len(text) <= max_len else text[:max_len] + "..."


def csv_download_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8-sig")


def get_chinese_pdf_font() -> str:
    if not REPORTLAB_AVAILABLE:
        return "Helvetica"

    font_candidates = [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
        "/System/Library/Fonts/Supplemental/Songti.ttc",
        r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\simsun.ttc",
    ]
    for font_path in font_candidates:
        path = Path(font_path)
        if path.exists():
            try:
                pdfmetrics.registerFont(TTFont("EconAtlasCN", str(path)))
                return "EconAtlasCN"
            except Exception:
                continue

    try:
        pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
        return "STSong-Light"
    except Exception:
        return "Helvetica"


def build_pdf_report(title: str, summary: str, stats_rows: list[list[str]], governance_note: str) -> bytes:
    if not REPORTLAB_AVAILABLE:
        raise RuntimeError("当前环境未安装 reportlab，暂无法生成 PDF。")

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
        "EconAtlasTitle",
        parent=styles["Title"],
        fontName=font_name,
        fontSize=19,
        leading=27,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=14,
    )
    h_style = ParagraphStyle(
        "EconAtlasHeading",
        parent=styles["Heading2"],
        fontName=font_name,
        fontSize=13,
        leading=20,
        textColor=colors.HexColor("#1d4ed8"),
        spaceBefore=12,
        spaceAfter=8,
    )
    body_style = ParagraphStyle(
        "EconAtlasBody",
        parent=styles["BodyText"],
        fontName=font_name,
        fontSize=10.5,
        leading=18,
        textColor=colors.HexColor("#111827"),
        spaceAfter=8,
    )

    story = [
        Paragraph(title, title_style),
        Paragraph("报告由 EconAtlas 全球宏观经济指标数据要素服务平台自动生成", body_style),
        Spacer(1, 8),
        Paragraph("一、报告摘要", h_style),
        Paragraph(summary, body_style),
        Paragraph("二、核心统计", h_style),
    ]
    table = Table([["项目", "内容"]] + stats_rows, colWidths=[4.2 * cm, 11 * cm])
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
    story.extend([
        table,
        Paragraph("三、数据治理说明", h_style),
        Paragraph(governance_note, body_style),
    ])
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


def build_asset_rating(df: pd.DataFrame) -> pd.DataFrame:
    base = df.copy()
    grouped = base.groupby("indicator_code", dropna=False)
    rating = grouped.agg(
        indicator_name_zh=("indicator_name_zh", "first"),
        frequency=("frequency", "first"),
        country_count=("country_code", "nunique"),
        source_count=("source_organization", "nunique"),
        total_rows=("value", "size"),
        valid_rows=("value", "count"),
        start_year=("date_year", "min"),
        end_year=("date_year", "max"),
    ).reset_index()
    rating["completeness"] = (rating["valid_rows"] / rating["total_rows"].replace(0, pd.NA) * 100).fillna(0)
    rating["coverage_score"] = rating["country_count"] / max(rating["country_count"].max(), 1) * 100
    rating["source_score"] = rating["source_count"] / max(rating["source_count"].max(), 1) * 100
    rating["scale_score"] = rating["valid_rows"] / max(rating["valid_rows"].max(), 1) * 100
    latest = rating["end_year"].max()
    rating["freshness_score"] = rating["end_year"].apply(lambda y: 100 if pd.notna(y) and y >= latest - 1 else 70)
    rating["asset_score"] = (
        rating["completeness"] * 0.30
        + rating["coverage_score"] * 0.25
        + rating["source_score"] * 0.20
        + rating["scale_score"] * 0.15
        + rating["freshness_score"] * 0.10
    ).round(1)
    rating["asset_level"] = rating["asset_score"].apply(
        lambda x: "S" if x >= 90 else ("A" if x >= 80 else ("B" if x >= 70 else ("C" if x >= 60 else "D")))
    )
    return rating.sort_values(["asset_score", "valid_rows"], ascending=False)


def build_country_panel(df: pd.DataFrame) -> pd.DataFrame:
    panel = df.groupby("country_code").agg(
        rows=("value", "size"),
        valid_rows=("value", "count"),
        indicators=("indicator_code", "nunique"),
        sources=("source_organization", "nunique"),
        country_name=("country_name_zh", "first"),
    ).reset_index()
    panel["quality"] = (panel["valid_rows"] / panel["rows"].replace(0, pd.NA) * 100).fillna(0).round(1)
    panel["lat"] = panel["country_code"].map(lambda x: COUNTRY_COORDS.get(x, (None, None))[0])
    panel["lon"] = panel["country_code"].map(lambda x: COUNTRY_COORDS.get(x, (None, None))[1])
    panel = panel.dropna(subset=["lat", "lon"])
    return panel


def kpi_card(label: str, value: str, sub: str = "", accent: str = "cyan") -> None:
    st.markdown(
        f"""
        <div class="kpi-card {accent} live-kpi">
          <div class="kpi-label">{label}</div>
          <div class="kpi-value">{value}</div>
          <div class="kpi-sub">{sub}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_title(title: str, sub: str = "") -> None:
    st.markdown(
        f"""
        <div class="section-title">
          <span></span>
          <strong>{title}</strong>
          <em>{sub}</em>
        </div>
        """,
        unsafe_allow_html=True,
    )


def style_plotly(fig: go.Figure, height: int = 260) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=8, r=8, t=28, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#dbeafe", family="Arial"),
        legend=dict(orientation="h", y=-0.12, x=0, font=dict(size=10)),
    )
    fig.update_xaxes(showgrid=True, gridcolor="rgba(96,165,250,.12)", zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor="rgba(96,165,250,.12)", zeroline=False)
    return fig


def curved_route(lon1: float, lat1: float, lon2: float, lat2: float, steps: int = 34) -> tuple[list[float], list[float]]:
    lons = []
    lats = []
    distance = abs(lon2 - lon1) + abs(lat2 - lat1)
    lift = min(18, max(5, distance * 0.08))
    for index in range(steps):
        t = index / (steps - 1)
        ease = 0.5 - 0.5 * math.cos(math.pi * t)
        lon = lon1 + (lon2 - lon1) * ease
        lat = lat1 + (lat2 - lat1) * ease + math.sin(math.pi * t) * lift
        lons.append(lon)
        lats.append(lat)
    return lons, lats


def cloud_band(base_lat: float, phase: float, amplitude: float = 4.5) -> tuple[list[float], list[float]]:
    lons = list(range(-180, 181, 4))
    lats = [
        base_lat
        + math.sin(math.radians(lon * 1.45 + phase)) * amplitude
        + math.sin(math.radians(lon * 3.1 - phase)) * 1.4
        for lon in lons
    ]
    return lons, lats


def draw_world_map(country_panel: pd.DataFrame) -> go.Figure:
    focus = country_panel[country_panel["country_code"] == "CN"]
    if focus.empty:
        focus_lat, focus_lon = 35.8617, 104.1954
    else:
        focus_lat = float(focus.iloc[0]["lat"])
        focus_lon = float(focus.iloc[0]["lon"])

    fig = go.Figure()
    for base_lat, phase, width, opacity in [(-42, 20, 7, .20), (-15, 130, 8, .22), (18, 250, 7, .24), (47, 45, 8, .18)]:
        cloud_lons, cloud_lats = cloud_band(base_lat, phase)
        fig.add_trace(
            go.Scattergeo(
                lon=cloud_lons,
                lat=cloud_lats,
                mode="lines",
                line=dict(color=f"rgba(226, 232, 240, {opacity})", width=width),
                hoverinfo="skip",
                showlegend=False,
            )
        )

    china_outline_lon = [74, 83, 96, 110, 123, 133, 125, 112, 96, 82, 74]
    china_outline_lat = [20, 31, 24, 22, 27, 42, 51, 54, 49, 40, 31]
    fig.add_trace(
        go.Scattergeo(
            lon=china_outline_lon,
            lat=china_outline_lat,
            mode="lines",
            fill="toself",
            fillcolor="rgba(34, 211, 238, .20)",
            line=dict(color="rgba(125, 211, 252, .88)", width=2.0),
            hoverinfo="skip",
            name="中国数据服务核心区",
        )
    )

    route_targets = country_panel[country_panel["country_code"] != "CN"].sort_values("valid_rows", ascending=False).head(9)
    for row in route_targets.itertuples(index=False):
        route_lons, route_lats = curved_route(focus_lon, focus_lat, float(row.lon), float(row.lat))
        fig.add_trace(
            go.Scattergeo(
                lon=route_lons,
                lat=route_lats,
                mode="lines",
                line=dict(color="rgba(167, 243, 208, .46)", width=5.5),
                opacity=.35,
                hoverinfo="skip",
                showlegend=False,
            )
        )
        fig.add_trace(
            go.Scattergeo(
                lon=route_lons,
                lat=route_lats,
                mode="lines",
                line=dict(color="rgba(125, 211, 252, .92)", width=1.7),
                opacity=.88,
                hoverinfo="skip",
                showlegend=False,
            )
        )

    top_lights = country_panel.sort_values("valid_rows", ascending=False).head(12)
    fig.add_trace(
        go.Scattergeo(
            lon=top_lights["lon"],
            lat=top_lights["lat"],
            mode="markers",
            marker=dict(
                size=26,
                color="rgba(255, 255, 180, .18)",
                line=dict(width=0),
            ),
            hoverinfo="skip",
            showlegend=False,
        )
    )

    fig.add_trace(
        go.Scattergeo(
            lon=country_panel["lon"],
            lat=country_panel["lat"],
            mode="markers+text",
            text=country_panel["country_code"],
            textposition="top center",
            marker=dict(
                size=(country_panel["valid_rows"] / country_panel["valid_rows"].max() * 24 + 7),
                color=country_panel["quality"],
                colorscale=[[0, "#38bdf8"], [.55, "#67e8f9"], [1, "#fef3c7"]],
                line=dict(width=1.4, color="#e0f2fe"),
                opacity=.95,
            ),
            customdata=country_panel[["country_name", "indicators", "sources", "valid_rows"]],
            hovertemplate="%{customdata[0]}<br>指标 %{customdata[1]} 个<br>来源 %{customdata[2]} 类<br>有效观测 %{customdata[3]:,} 条<extra></extra>",
            name="数据节点",
        )
    )

    fig.update_geos(
        bgcolor="rgba(0,0,0,0)",
        showland=True,
        landcolor="rgba(132, 139, 112, .95)",
        showocean=True,
        oceancolor="rgba(4, 22, 50, .94)",
        showcoastlines=True,
        coastlinecolor="rgba(226, 232, 240, .72)",
        showcountries=True,
        countrycolor="rgba(148, 163, 184, .24)",
        showlakes=True,
        lakecolor="rgba(14, 165, 233, .34)",
        lataxis_showgrid=True,
        lonaxis_showgrid=True,
        lataxis_gridcolor="rgba(125, 211, 252, .10)",
        lonaxis_gridcolor="rgba(125, 211, 252, .10)",
        projection_type="orthographic",
        projection_rotation=dict(lon=88, lat=31, roll=0),
        projection_scale=1.04,
    )
    fig.update_layout(
        width=500,
        height=500,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        geo=dict(domain=dict(x=[0, 1], y=[0, 1])),
        autosize=False,
        showlegend=False,
    )
    return fig


def get_selected_module() -> str:
    try:
        value = st.query_params.get("module", "")
    except Exception:
        try:
            value = st.experimental_get_query_params().get("module", [""])[0]
        except Exception:
            value = ""
    if isinstance(value, list):
        value = value[0] if value else ""
    return value if value in MODULES else ""


def module_dock(selected_module: str = "") -> None:
    module_links = []
    for name in MODULES:
        active = " active" if name == selected_module else ""
        current = ' aria-current="page"' if name == selected_module else ""
        module_links.append(
            f'<a class="{active.strip()}"{current} target="_self" '
            f'href="?page=platform&amp;module={quote(name)}">{name}</a>'
        )
    module_html = "".join(module_links)
    st.markdown(
        f"""
        <div class="module-dock">
          <div class="module-dock-title-wrap">
            <i></i>
            <div>
              <div class="module-dock-title">平台模块入口</div>
              <div class="system-lights">
                <span></span>DB ONLINE
                <span></span>API READY
                <span></span>QUALITY OK
              </div>
            </div>
          </div>
          <nav class="module-dock-links" aria-label="平台模块导航">
            <a class="primary" target="_self" href="?page=platform">返回大屏首页</a>
            {module_html}
          </nav>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_event_ticker(df_all: pd.DataFrame, quality_rate: float, warning_count: int, latest_year: int) -> None:
    sources = sorted(df_all["source_organization"].dropna().astype(str).unique().tolist())
    source_text = " · ".join(sources[:8])
    events = [
        f"标准库在线：{fmt_int(len(df_all))} 条观测记录",
        f"数据质量通过率：{quality_rate:.1f}%",
        f"最新数据年份：{latest_year}",
        f"质量警示项：{warning_count}",
        f"接入来源：{source_text}",
        "指标标准化服务：RUNNING",
        "多源一致性监测：ACTIVE",
        "JSON API 服务能力：READY",
    ]
    html = "".join(f"<span>{item}</span>" for item in events)
    st.markdown(
        f"""
        <div class="event-ticker">
          <strong>实时事件</strong>
          <div class="event-track">
            <div class="event-content">{html}{html}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def module_title(name: str, desc: str) -> None:
    st.markdown(
        f"""
        <div class="module-hero">
          <div>
            <div class="module-kicker">EconAtlas Module</div>
            <h2>{name}</h2>
            <p>{desc}</p>
          </div>
          <a target="_self" href="?page=platform">返回大屏首页</a>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_status_row(status_text: str, finished_at: str) -> None:
    """Render the status row with the current China Standard Time."""
    now = datetime.now(ZoneInfo("Asia/Shanghai"))
    display_time = now.strftime("%Y-%m-%d %H:%M:%S")
    iso_time = now.isoformat(timespec="seconds")
    st.markdown(
        f"""
        <div class="status-row">
          <div>数据源状态：{status_text} · 最近记录：{finished_at}</div>
          <div>系统当前时间（北京时间）· <time datetime="{iso_time}">{display_time}</time></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_live_status_row(status_text: str, finished_at: str) -> None:
    """Refresh only the display clock when the installed Streamlit supports fragments."""
    fragment = getattr(st, "fragment", None)
    if fragment is None:
        render_status_row(status_text, finished_at)
        return

    @fragment(run_every="1s")
    def live_status() -> None:
        render_status_row(status_text, finished_at)

    live_status()


def latest_series(df: pd.DataFrame, country: str, indicator: str) -> pd.DataFrame:
    out = df[(df["country_code"] == country) & (df["indicator_code"] == indicator)].copy()
    out = out.dropna(subset=["value", "date_year"]).sort_values(["source_organization", "date"])
    return out


def render_module_page(
    module: str,
    df_all: pd.DataFrame,
    asset_rating: pd.DataFrame,
    country_panel: pd.DataFrame,
    quality_report: pd.DataFrame,
    alignment_df: pd.DataFrame,
    source_mapping: pd.DataFrame,
) -> None:
    indicator_master = load_csv("indicator_master.csv")
    country_master = load_csv("country_master.csv")
    consistency_df = load_clean_csv("quality_consistency_report.csv")
    coverage_df = load_clean_csv("quality_coverage_report.csv")
    outlier_df = load_clean_csv("quality_outlier_report.csv")
    country_meta = (
        df_all[["country_code", "country_name_zh", "country_name_en"]]
        .dropna(subset=["country_code"])
        .drop_duplicates("country_code")
        .set_index("country_code")
        .to_dict("index")
    )
    indicator_meta = (
        df_all[["indicator_code", "indicator_name_zh", "indicator_name_en", "unit"]]
        .dropna(subset=["indicator_code"])
        .drop_duplicates("indicator_code")
        .set_index("indicator_code")
        .to_dict("index")
    )

    def country_label(code: str) -> str:
        meta = country_meta.get(code, {})
        zh = meta.get("country_name_zh") or code
        return f"{zh} ({code})"

    def indicator_label(code: str) -> str:
        meta = indicator_meta.get(code, {})
        zh = meta.get("indicator_name_zh") or code
        return f"{short_text(zh, 18)} ({code})"

    def frequency_label(code: str) -> str:
        zh = {"A": "年度", "Q": "季度", "M": "月度", "D": "日度"}.get(code, code)
        return f"{zh} ({code})"

    descriptions = {
        "指标查询": "按国家、指标、频率和来源进行统一查询，输出趋势图与标准化观测表。",
        "指标字典": "展示平台标准指标体系、频率、单位、来源数量和治理口径。",
        "数据质量": "集中查看完整性、缺失、异常、覆盖率和质量检查结果。",
        "JSON输出": "展示平台对外服务的结构化 JSON 数据格式。",
        "一致性分析": "识别多来源共同观测期的口径差异和偏差风险。",
        "治理驾驶舱": "汇总采集、标准化、入库、质量和资产化治理状态。",
        "指标血缘": "追踪来源机构、原始指标代码与标准指标之间的映射关系。",
        "治理规则": "展示指标映射、频率统一、单位统一、缺失处理和冲突识别规则。",
        "API服务中心": "展示统一查询、批量查询、元数据和健康检查接口能力。",
        "数据资产目录": "以资产视角管理指标，展示覆盖、来源、规模和 API 可用性。",
        "风险预警": "对缺失值、多源偏差、覆盖不足和异常值进行预警。",
        "智能分析": "对选定宏观指标进行趋势判断、风险识别和建议生成。",
        "智能报告": "自动整合趋势、来源、风险和治理说明，形成报告草稿。",
        "资产评级": "综合完整性、覆盖度、来源、规模和新鲜度评估资产等级。",
        "指标对齐审核": "展示半自动指标候选对齐、置信等级和人工复核结果。",
    }
    module_title(module, descriptions.get(module, "EconAtlas 大屏风格业务模块。"))

    if module == "指标查询":
        countries = sorted(df_all["country_code"].dropna().unique().tolist())
        indicators = sorted(df_all["indicator_code"].dropna().unique().tolist())
        freqs = sorted(df_all["frequency"].dropna().unique().tolist())
        c1, c2, c3 = st.columns([1, 1.4, .8])
        country = c1.selectbox("国家/地区", countries, index=countries.index("CN") if "CN" in countries else 0, format_func=country_label)
        indicator = c2.selectbox("标准指标", indicators, index=indicators.index("CPI_YOY_M") if "CPI_YOY_M" in indicators else 0, format_func=indicator_label)
        frequency = c3.selectbox("频率", freqs, index=freqs.index("M") if "M" in freqs else 0, format_func=frequency_label)
        query_df = df_all[(df_all["country_code"] == country) & (df_all["indicator_code"] == indicator) & (df_all["frequency"] == frequency)].copy()
        query_df = query_df.dropna(subset=["value"]).sort_values("date")
        st.markdown('<div class="panel module-panel">', unsafe_allow_html=True)
        section_title("查询结果趋势", f"{country_label(country)} · {indicator_label(indicator)} · {frequency_label(frequency)}")
        if query_df.empty:
            st.warning("当前条件下暂无数据。")
        else:
            fig = px.line(query_df, x="date", y="value", color="source_organization", markers=True)
            st.plotly_chart(style_plotly(fig, 420), width="stretch", config={"displayModeBar": False})
            st.dataframe(query_df.tail(80), width="stretch", height=280, hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)
        return

    if module == "指标字典":
        st.markdown('<div class="panel module-panel">', unsafe_allow_html=True)
        section_title("标准指标字典", f"{len(indicator_master)} indicators")
        freq_count = indicator_master.groupby("frequency").size().reset_index(name="指标数量") if not indicator_master.empty else pd.DataFrame()
        a, b = st.columns([.85, 1.4])
        if not freq_count.empty:
            fig = px.bar(freq_count, x="frequency", y="指标数量", color="frequency")
            a.plotly_chart(style_plotly(fig, 320), width="stretch", config={"displayModeBar": False})
        b.dataframe(indicator_master, width="stretch", height=360, hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)
        return

    if module == "数据质量":
        st.markdown('<div class="panel module-panel">', unsafe_allow_html=True)
        section_title("质量检查矩阵", f"{len(quality_report)} checks")
        a, b, c = st.columns(3)
        a.metric("缺失观测", fmt_int(df_all["value"].isna().sum()))
        b.metric("重复键", quality_report.loc[quality_report["check_item"] == "duplicate_key_count", "value"].astype(str).head(1).iat[0] if not quality_report.empty and (quality_report["check_item"] == "duplicate_key_count").any() else "0")
        c.metric("异常值", fmt_int(len(outlier_df)))
        st.dataframe(quality_report, width="stretch", height=220, hide_index=True)
        if not coverage_df.empty:
            top_missing = coverage_df.sort_values("missing_rate", ascending=False).head(12)
            fig = px.bar(top_missing, x="indicator_code", y="missing_rate", color="source_organization")
            st.plotly_chart(style_plotly(fig, 340), width="stretch", config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)
        return

    if module == "JSON输出":
        sample = df_all.dropna(subset=["value"]).head(6)
        payload = {
            "service": "EconAtlas",
            "endpoint": "/query",
            "request": {"country": "CN", "indicator_code": "CPI_YOY_M", "frequency": "M"},
            "series_count": int(sample["series_id"].nunique()) if "series_id" in sample else 1,
            "observations": [
                {
                    "country": row.country_code,
                    "indicator": row.indicator_code,
                    "date": row.date,
                    "value": float(row.value),
                    "source": row.source_organization,
                }
                for row in sample.itertuples(index=False)
            ],
        }
        st.markdown('<div class="panel module-panel">', unsafe_allow_html=True)
        section_title("标准 JSON 输出预览", "API response")
        st.json(payload)
        st.markdown("</div>", unsafe_allow_html=True)
        return

    if module == "一致性分析":
        st.markdown('<div class="panel module-panel">', unsafe_allow_html=True)
        section_title("多源一致性分析", f"{len(consistency_df)} common observations")
        if consistency_df.empty:
            st.warning("暂无一致性报告。")
        else:
            status_count = consistency_df.groupby("status").size().reset_index(name="数量")
            a, b = st.columns([.8, 1.5])
            fig = px.pie(status_count, names="status", values="数量", hole=.58)
            a.plotly_chart(style_plotly(fig, 320), width="stretch", config={"displayModeBar": False})
            b.dataframe(consistency_df.sort_values("relative_diff", ascending=False).head(80), width="stretch", height=360, hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)
        return

    if module == "治理驾驶舱":
        st.markdown('<div class="panel module-panel">', unsafe_allow_html=True)
        section_title("治理流程态势", "Collect · Standardize · Validate · Serve")
        cols = st.columns(5)
        for col, label, value in zip(
            cols,
            ["采集源", "标准指标", "国家地区", "入库记录", "高价值资产"],
            [df_all["source_organization"].nunique(), df_all["indicator_code"].nunique(), df_all["country_code"].nunique(), len(df_all), int((asset_rating["asset_score"] >= 80).sum())],
        ):
            col.metric(label, fmt_int(value))
        source_counts = df_all.groupby("source_organization").size().reset_index(name="rows").sort_values("rows")
        fig = px.bar(source_counts, x="rows", y="source_organization", orientation="h")
        st.plotly_chart(style_plotly(fig, 380), width="stretch", config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)
        return

    if module == "指标血缘":
        st.markdown('<div class="panel module-panel">', unsafe_allow_html=True)
        section_title("指标血缘映射", f"{len(source_mapping)} mappings")
        if source_mapping.empty:
            st.warning("暂无 source_mapping.csv。")
        else:
            fig = px.sunburst(source_mapping, path=["source", "indicator_code"], values=None)
            st.plotly_chart(style_plotly(fig, 430), width="stretch", config={"displayModeBar": False})
            st.dataframe(source_mapping, width="stretch", height=260, hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)
        return

    if module == "治理规则":
        rules = pd.DataFrame(
            [
                ["指标映射", "来源指标统一映射为平台标准指标编码"],
                ["频率统一", "年度、月度、日度统一为 A/M/D"],
                ["单位统一", "百分比、指数、现价货币等单位标准化"],
                ["缺失处理", "空值统一进入质量报告和预警中心"],
                ["多源冲突", "通过共同观测期偏差率识别口径差异"],
                ["数据血缘", "保留来源机构、原始代码、标准指标和来源 URL"],
            ],
            columns=["规则类型", "治理说明"],
        )
        st.markdown('<div class="panel module-panel">', unsafe_allow_html=True)
        section_title("治理规则中心", "Rule Engine")
        st.dataframe(rules, width="stretch", height=260, hide_index=True)
        fig = px.bar(rules, x="规则类型", y=[1] * len(rules), text="规则类型")
        st.plotly_chart(style_plotly(fig, 300), width="stretch", config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)
        return

    if module == "API服务中心":
        api_df = pd.DataFrame(
            [
                ["GET", "/query", "单指标时间序列查询"],
                ["POST", "/batch_query", "批量指标查询"],
                ["GET", "/metadata", "元数据资产概览"],
                ["GET", "/health", "服务状态检查"],
            ],
            columns=["方法", "接口", "能力说明"],
        )
        st.markdown('<div class="panel module-panel">', unsafe_allow_html=True)
        section_title("API 服务中心", "FastAPI")
        st.dataframe(api_df, width="stretch", height=220, hide_index=True)
        st.code("uvicorn api_service.app:app --reload\nhttp://127.0.0.1:8000/docs", language="bash")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    if module == "数据资产目录":
        st.markdown('<div class="panel module-panel">', unsafe_allow_html=True)
        section_title("数据资产目录", f"{len(asset_rating)} assets")
        st.dataframe(asset_rating, width="stretch", height=520, hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)
        return

    if module == "风险预警":
        st.markdown('<div class="panel module-panel">', unsafe_allow_html=True)
        section_title("风险预警中心", "Quality Alerts")
        a, b, c = st.columns(3)
        a.metric("质量警示项", fmt_int((quality_report["status"].astype(str) == "warning").sum()) if not quality_report.empty else "0")
        b.metric("多源偏差警示", fmt_int((consistency_df["status"].astype(str) == "warning").sum()) if not consistency_df.empty else "0")
        c.metric("异常观测", fmt_int(len(outlier_df)))
        if not consistency_df.empty:
            st.dataframe(consistency_df[consistency_df["status"].astype(str) == "warning"].head(100), width="stretch", height=360, hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)
        return

    if module in ["智能分析", "智能报告"]:
        countries = sorted(df_all["country_code"].dropna().unique().tolist())
        indicators = sorted(df_all["indicator_code"].dropna().unique().tolist())
        c1, c2 = st.columns([.8, 1.2])
        country = c1.selectbox("分析国家/地区", countries, index=countries.index("CN") if "CN" in countries else 0, format_func=country_label)
        indicator = c2.selectbox("分析指标", indicators, index=indicators.index("CPI_YOY_M") if "CPI_YOY_M" in indicators else 0, format_func=indicator_label)
        data = latest_series(df_all, country, indicator)
        country_display = country_label(country)
        indicator_display = indicator_label(indicator)
        st.markdown('<div class="panel module-panel">', unsafe_allow_html=True)
        section_title(module, f"{country_display} · {indicator_display}")
        if data.empty:
            st.warning("当前条件暂无可分析数据。")
        else:
            recent = data.tail(24)
            latest_value = recent["value"].iloc[-1]
            first_value = recent["value"].iloc[0]
            trend = "上升" if latest_value > first_value else ("下降" if latest_value < first_value else "平稳")
            unit = indicator_meta.get(indicator, {}).get("unit") or ""
            source_text = "、".join(sorted(recent["source_organization"].dropna().astype(str).unique()))
            fig = px.line(recent, x="date", y="value", color="source_organization", markers=True)
            st.plotly_chart(style_plotly(fig, 360), width="stretch", config={"displayModeBar": False})
            report = (
                f"系统识别 {country_display} 的 {indicator_display} 最近 {len(recent)} 条有效观测整体呈现{trend}态势。"
                f"最新值为 {fmt_float(latest_value)}{unit}，样本均值为 {fmt_float(recent['value'].mean())}{unit}。"
                "建议结合来源口径、发布时间和多源一致性报告进行交叉判断。"
            )
            st.info(report)
            if module == "智能报告":
                report_md = f"""# {country_display} {indicator_display} 智能分析报告

## 一、报告摘要

本报告基于 EconAtlas 全球宏观经济指标数据要素服务平台，对 **{country_display}** 的 **{indicator_display}** 进行趋势分析、风险识别与数据治理说明。数据来源包括：**{source_text}**。

## 二、核心统计

- 指标代码：{indicator}
- 数据来源：{source_text}
- 有效观测数量：{len(recent)}
- 时间范围：{recent["date"].iloc[0]}—{recent["date"].iloc[-1]}
- 最新值：{fmt_float(latest_value)}{unit}
- 历史均值：{fmt_float(recent["value"].mean())}{unit}
- 历史最大值：{fmt_float(recent["value"].max())}{unit}
- 历史最小值：{fmt_float(recent["value"].min())}{unit}

## 三、智能解读

{report}

## 四、数据治理说明

平台已对多来源宏观经济数据进行标准化治理，包括指标编码统一、频率统一、单位统一、元数据保留、多源一致性分析和结构化服务输出。

---
报告由 EconAtlas 自动生成。
"""
                st.markdown("### 报告预览")
                st.markdown(report_md)
                b1, b2, b3, b4 = st.columns(4)
                governance_note = "平台已对多来源宏观经济数据进行标准化治理，包括指标编码统一、频率统一、单位统一、元数据保留、多源一致性分析和结构化服务输出。"
                stats_rows = [
                    ["指标代码", indicator],
                    ["数据来源", source_text],
                    ["有效观测数量", str(len(recent))],
                    ["时间范围", f"{recent['date'].iloc[0]}—{recent['date'].iloc[-1]}"],
                    ["最新值", f"{fmt_float(latest_value)}{unit}"],
                    ["历史均值", f"{fmt_float(recent['value'].mean())}{unit}"],
                    ["历史最大值", f"{fmt_float(recent['value'].max())}{unit}"],
                    ["历史最小值", f"{fmt_float(recent['value'].min())}{unit}"],
                ]
                if REPORTLAB_AVAILABLE:
                    pdf_bytes = build_pdf_report(
                        title=f"{country_display} {indicator_display} 智能分析报告",
                        summary=report,
                        stats_rows=stats_rows,
                        governance_note=governance_note,
                    )
                    b1.download_button(
                        "下载 PDF 报告",
                        data=pdf_bytes,
                        file_name=f"{country}_{indicator}_report.pdf",
                        mime="application/pdf",
                    )
                else:
                    b1.warning("当前环境未安装 reportlab，暂无法生成 PDF。")
                b2.download_button(
                    "下载 Markdown 报告",
                    data=report_md,
                    file_name=f"{country}_{indicator}_report.md",
                    mime="text/markdown",
                )
                report_json = {
                    "country": country,
                    "country_label": country_display,
                    "indicator": indicator,
                    "indicator_label": indicator_display,
                    "latest_value": float(latest_value),
                    "mean_value": float(recent["value"].mean()),
                    "trend": trend,
                    "sources": source_text,
                    "summary": report,
                }
                b3.download_button(
                    "下载 JSON 报告",
                    data=json.dumps(report_json, ensure_ascii=False, indent=2),
                    file_name=f"{country}_{indicator}_report.json",
                    mime="application/json",
                )
                b4.download_button(
                    "下载报告数据 CSV",
                    data=csv_download_bytes(recent),
                    file_name=f"{country}_{indicator}_report_data.csv",
                    mime="text/csv",
                )
        st.markdown("</div>", unsafe_allow_html=True)
        return

    if module == "资产评级":
        st.markdown('<div class="panel module-panel">', unsafe_allow_html=True)
        section_title("数据资产评级", "S/A/B/C/D")
        level_count = asset_rating.groupby("asset_level").size().reset_index(name="资产数量")
        a, b = st.columns([.75, 1.5])
        fig = px.pie(level_count, names="asset_level", values="资产数量", hole=.55)
        a.plotly_chart(style_plotly(fig, 330), width="stretch", config={"displayModeBar": False})
        b.dataframe(asset_rating.head(30), width="stretch", height=360, hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)
        return

    if module == "指标对齐审核":
        st.markdown('<div class="panel module-panel">', unsafe_allow_html=True)
        section_title("指标对齐审核", f"{len(alignment_df)} candidates")
        if alignment_df.empty:
            st.warning("暂无候选对齐表。")
        else:
            conf = alignment_df.groupby("confidence_level").size().reset_index(name="数量")
            fig = px.bar(conf, x="confidence_level", y="数量", color="confidence_level")
            st.plotly_chart(style_plotly(fig, 300), width="stretch", config={"displayModeBar": False})
            st.dataframe(alignment_df, width="stretch", height=420, hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)
        return


st.markdown(
    """
    <style>
    :root {
        --bg: #020617;
        --panel: rgba(8, 18, 50, .74);
        --panel-strong: rgba(10, 25, 72, .90);
        --line: rgba(56, 189, 248, .42);
        --line-soft: rgba(96, 165, 250, .18);
        --cyan: #22d3ee;
        --blue: #3b82f6;
        --green: #34d399;
        --yellow: #facc15;
        --red: #fb7185;
    }
    .stApp {
        background:
            radial-gradient(circle at 50% 46%, rgba(37, 99, 235, .34), transparent 34%),
            radial-gradient(circle at 78% 18%, rgba(34, 211, 238, .16), transparent 26%),
            linear-gradient(135deg, #020617 0%, #061340 42%, #020617 100%);
        color: #e0f2fe;
        font-family: Inter, "PingFang SC", "Microsoft YaHei", sans-serif;
    }
    .block-container { padding: .35rem 1.05rem 1.05rem; max-width: 100%; }
    #MainMenu, footer, header, [data-testid="stToolbar"] { visibility: hidden; height: 0; }
    div[data-testid="stVerticalBlock"] { gap: .75rem; }
    div[data-testid="stDownloadButton"] button {
        width: 100%;
        min-height: 46px;
        border: 1px solid rgba(34, 211, 238, .78) !important;
        border-radius: 8px !important;
        background:
            linear-gradient(135deg, rgba(37, 99, 235, .96), rgba(14, 165, 233, .78)) !important;
        color: #ffffff !important;
        font-weight: 800 !important;
        box-shadow: 0 0 18px rgba(34, 211, 238, .28), inset 0 0 14px rgba(255, 255, 255, .10);
    }
    div[data-testid="stDownloadButton"] button p,
    div[data-testid="stDownloadButton"] button span {
        color: #ffffff !important;
        font-weight: 800 !important;
    }
    div[data-testid="stDownloadButton"] button:hover {
        border-color: rgba(255, 255, 255, .92) !important;
        background:
            linear-gradient(135deg, rgba(59, 130, 246, 1), rgba(34, 211, 238, .92)) !important;
        box-shadow: 0 0 24px rgba(34, 211, 238, .42), inset 0 0 18px rgba(255, 255, 255, .14);
    }
    .screen-frame {
        position: fixed;
        inset: 7px;
        pointer-events: none;
        border: 1px solid rgba(34, 211, 238, .35);
        box-shadow: inset 0 0 42px rgba(37, 99, 235, .18), 0 0 32px rgba(34, 211, 238, .12);
        z-index: 0;
    }
    .screen-frame:before, .screen-frame:after {
        content: "";
        position: absolute;
        width: 210px;
        height: 24px;
        border-top: 3px solid rgba(34, 211, 238, .72);
        top: -2px;
    }
    .screen-frame:before { left: 30px; border-left: 3px solid rgba(34, 211, 238, .72); }
    .screen-frame:after { right: 30px; border-right: 3px solid rgba(34, 211, 238, .72); }
    .topbar {
        display: flex;
        justify-content: center;
        align-items: center;
        margin: 0 12px 2px;
        min-height: 86px;
        position: relative;
    }
    .topbar:before, .topbar:after {
        content: "";
        position: absolute;
        top: 32px;
        width: calc(50% - 500px);
        min-width: 260px;
        height: 34px;
        border-top: 2px solid rgba(34,211,238,.68);
        border-bottom: 1px solid rgba(59,130,246,.18);
        background:
            repeating-linear-gradient(115deg, rgba(34,211,238,.26) 0 4px, transparent 4px 13px),
            linear-gradient(90deg, transparent, rgba(34,211,238,.14), rgba(59,130,246,.05));
        box-shadow: 0 0 16px rgba(34,211,238,.5);
    }
    .topbar:before { left: 16px; }
    .topbar:after {
        right: 16px;
        background:
            repeating-linear-gradient(65deg, rgba(34,211,238,.26) 0 4px, transparent 4px 13px),
            linear-gradient(90deg, rgba(59,130,246,.05), rgba(34,211,238,.14), transparent);
    }
    .title-box {
        position: relative;
        text-align: center;
        width: min(860px, 50vw);
        min-width: 760px;
        padding: 12px 42px 15px;
        border: 1px solid rgba(34,211,238,.40);
        border-bottom-color: rgba(34,211,238,.78);
        background:
            linear-gradient(180deg, rgba(37,99,235,.68), rgba(8,18,50,.78) 68%, rgba(5,13,38,.80)),
            radial-gradient(circle at 50% 0%, rgba(103,232,249,.26), transparent 58%);
        box-shadow: inset 0 0 26px rgba(34,211,238,.18), 0 0 30px rgba(59,130,246,.22);
        clip-path: polygon(5% 0, 95% 0, 100% 44%, 94% 100%, 6% 100%, 0 44%);
    }
    .title-box:before, .title-box:after {
        content: "";
        position: absolute;
        top: 50%;
        width: 80px;
        height: 2px;
        background: linear-gradient(90deg, transparent, rgba(125,211,252,.9));
        box-shadow: 0 0 12px rgba(34,211,238,.8);
    }
    .title-box:before { left: 18px; }
    .title-box:after { right: 18px; transform: rotate(180deg); }
    .title-box h1 {
        margin: 0;
        font-size: 34px;
        letter-spacing: 0;
        color: #f8fafc;
        white-space: nowrap;
        text-shadow: 0 0 18px rgba(34,211,238,.75);
    }
    .title-box p { margin: 7px 0 0; color: #93c5fd; font-size: 13px; font-weight: 700; }
    .status-row {
        display: flex;
        justify-content: space-between;
        color: #bfdbfe;
        font-size: 13px;
        margin: 0 8px 6px;
        padding: 0 7px;
        font-weight: 700;
    }
    .module-dock {
        display: grid;
        grid-template-columns: 172px 1fr;
        align-items: center;
        gap: 14px;
        margin: 0 0 6px;
        padding: 10px 13px;
        border: 1px solid rgba(56,189,248,.30);
        background:
            linear-gradient(90deg, rgba(5,13,38,.94), rgba(8,28,72,.82) 48%, rgba(5,13,38,.90)),
            repeating-linear-gradient(90deg, rgba(96,165,250,.08) 0 1px, transparent 1px 52px);
        box-shadow: inset 0 0 22px rgba(37,99,235,.18), 0 0 18px rgba(14,165,233,.12);
        position: relative;
    }
    .module-dock:before, .module-dock:after {
        content: "";
        position: absolute;
        top: -1px;
        width: 120px;
        height: 2px;
        background: #22d3ee;
        box-shadow: 0 0 12px rgba(34,211,238,.9);
    }
    .module-dock:before { left: 18px; }
    .module-dock:after { right: 18px; }
    .module-dock-title-wrap {
        display: flex;
        align-items: center;
        gap: 8px;
        min-width: 0;
    }
    .module-dock-title {
        color: #e0f2fe;
        font-size: 16px;
        font-weight: 800;
        text-align: center;
        padding: 2px 12px 0 8px;
        white-space: nowrap;
    }
    .system-lights {
        display: flex;
        gap: 8px;
        align-items: center;
        padding: 3px 12px 2px 8px;
        border-right: 1px solid rgba(56,189,248,.38);
        color: #93c5fd;
        font-size: 9px;
        font-weight: 900;
    }
    .system-lights span {
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background: #34d399;
        box-shadow: 0 0 10px rgba(52, 211, 153, .95);
        animation: statusPulse 1.8s ease-in-out infinite;
    }
    .system-lights span:nth-child(3) { animation-delay: .4s; }
    .system-lights span:nth-child(5) { animation-delay: .8s; }
    .module-dock-title-wrap i {
        width: 5px;
        height: 24px;
        background: linear-gradient(180deg, #67e8f9, #2563eb);
        box-shadow: 0 0 12px rgba(34,211,238,.8);
    }
    .module-dock-links {
        display: flex;
        gap: 8px;
        overflow-x: auto;
        white-space: nowrap;
        padding-bottom: 1px;
    }
    .module-dock a {
        color: #bfdbfe;
        text-decoration: none;
        font-size: 12px;
        font-weight: 800;
        border: 1px solid rgba(56,189,248,.28);
        background: linear-gradient(180deg, rgba(15,36,86,.72), rgba(7,18,50,.82));
        padding: 8px 13px;
        box-shadow: inset 0 0 10px rgba(14,165,233,.08);
    }
    .module-dock a:hover {
        color: #ffffff;
        border-color: rgba(34,211,238,.82);
        box-shadow: 0 0 12px rgba(34,211,238,.28);
    }
    .module-dock a.active {
        color: #ffffff;
        border-color: rgba(125,211,252,.95);
        background: linear-gradient(180deg, rgba(14,165,233,.62), rgba(30,64,175,.82));
        box-shadow: 0 0 14px rgba(34,211,238,.32), inset 0 0 12px rgba(125,211,252,.14);
    }
    .module-dock a.primary {
        color: #020617;
        font-weight: 900;
        border-color: rgba(125,211,252,.9);
        background: linear-gradient(135deg, #7dd3fc, #38bdf8 52%, #2563eb);
        box-shadow: 0 0 16px rgba(56,189,248,.38), inset 0 0 10px rgba(255,255,255,.22);
    }
    .module-hero {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin: 6px 0 8px;
        padding: 18px 24px;
        border: 1px solid rgba(56,189,248,.30);
        background:
            radial-gradient(circle at 20% 10%, rgba(34,211,238,.18), transparent 34%),
            linear-gradient(90deg, rgba(8,18,50,.92), rgba(15,36,86,.72), rgba(8,18,50,.90));
        box-shadow: inset 0 0 24px rgba(37,99,235,.18), 0 0 18px rgba(14,165,233,.10);
    }
    .module-hero h2 {
        margin: 0;
        color: #f8fafc;
        font-size: 30px;
        letter-spacing: 0;
        text-shadow: 0 0 16px rgba(34,211,238,.56);
    }
    .module-hero p {
        margin: 7px 0 0;
        color: #bfdbfe;
        font-size: 14px;
    }
    .module-kicker {
        color: #67e8f9;
        font-size: 12px;
        font-weight: 900;
        text-transform: uppercase;
    }
    .module-hero a {
        color: #020617;
        text-decoration: none;
        font-weight: 900;
        padding: 9px 15px;
        border: 1px solid rgba(125,211,252,.9);
        background: linear-gradient(135deg, #7dd3fc, #38bdf8);
        box-shadow: 0 0 16px rgba(56,189,248,.34);
        white-space: nowrap;
    }
    .module-panel {
        min-height: 540px;
    }
    .panel {
        position: relative;
        border: 1px solid var(--line-soft);
        background: linear-gradient(180deg, rgba(8,18,50,.84), rgba(2,6,23,.62));
        box-shadow: inset 0 0 28px rgba(37,99,235,.13), 0 0 22px rgba(14,165,233,.09);
        padding: 14px;
        min-height: 104px;
        overflow: hidden;
    }
    .panel:before {
        content: "";
        position: absolute;
        inset: 0;
        background: linear-gradient(90deg, transparent, rgba(34,211,238,.08), transparent);
        transform: translateX(-100%);
        animation: scan 7s linear infinite;
    }
    .earth-panel {
        background:
            radial-gradient(circle at 50% 58%, rgba(125, 211, 252, .24), transparent 24%),
            radial-gradient(circle at 52% 55%, rgba(59, 130, 246, .22), transparent 39%),
            radial-gradient(circle at 50% 52%, rgba(2, 6, 23, .10), transparent 57%),
            linear-gradient(180deg, rgba(5,13,38,.92), rgba(2,6,23,.74));
        box-shadow:
            inset 0 0 60px rgba(37, 99, 235, .20),
            inset 0 -40px 80px rgba(2, 6, 23, .55),
            0 0 26px rgba(14, 165, 233, .10);
    }
    .earth-panel:after {
        content: "";
        position: absolute;
        inset: 72px 12% 72px;
        pointer-events: none;
        border-radius: 50%;
        box-shadow: 0 0 70px rgba(103, 232, 249, .20), inset 0 0 38px rgba(34, 211, 238, .14);
        opacity: .72;
    }
    .event-ticker {
        display: grid;
        grid-template-columns: 96px 1fr;
        align-items: center;
        gap: 12px;
        margin-top: 8px;
        padding: 8px 12px;
        border: 1px solid rgba(56, 189, 248, .28);
        background: linear-gradient(90deg, rgba(5,13,38,.94), rgba(8,28,72,.72), rgba(5,13,38,.94));
        box-shadow: inset 0 0 18px rgba(37,99,235,.15), 0 0 16px rgba(14,165,233,.10);
        overflow: hidden;
    }
    .event-ticker strong {
        color: #e0f2fe;
        font-size: 14px;
        text-align: center;
        border-right: 1px solid rgba(56,189,248,.35);
    }
    .event-track {
        overflow: hidden;
        white-space: nowrap;
    }
    .event-content {
        display: inline-flex;
        gap: 14px;
        animation: tickerMove 34s linear infinite;
    }
    .event-content span {
        color: #bfdbfe;
        font-size: 12px;
        font-weight: 800;
        border: 1px solid rgba(56,189,248,.20);
        background: rgba(15,23,42,.58);
        padding: 5px 10px;
    }
    @keyframes cardBreathe {
        0%, 100% { box-shadow: inset 0 0 18px rgba(59,130,246,.10), 0 0 0 rgba(34,211,238,0); }
        50% { box-shadow: inset 0 0 24px rgba(59,130,246,.20), 0 0 18px rgba(34,211,238,.16); }
    }
    @keyframes kpiSweep {
        0%, 18% { left: -60%; opacity: 0; }
        32% { opacity: 1; }
        58%, 100% { left: 120%; opacity: 0; }
    }
    @keyframes tickerMove {
        from { transform: translateX(0); }
        to { transform: translateX(-50%); }
    }
    @keyframes statusPulse {
        0%, 100% { transform: scale(.82); opacity: .62; }
        50% { transform: scale(1.18); opacity: 1; }
    }
    @keyframes scan { to { transform: translateX(100%); } }
    .section-title {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 8px;
        color: #e0f2fe;
    }
    .section-title span {
        display: inline-block;
        width: 5px;
        height: 22px;
        background: linear-gradient(180deg, #67e8f9, #2563eb);
        box-shadow: 0 0 12px rgba(34,211,238,.8);
    }
    .section-title strong { font-size: 16px; }
    .section-title em { margin-left: auto; font-style: normal; font-size: 11px; color: #7dd3fc; }
    .kpi-card {
        position: relative;
        border: 1px solid rgba(56,189,248,.22);
        background: radial-gradient(circle at 80% 10%, rgba(34,211,238,.18), transparent 35%), rgba(15,23,42,.54);
        padding: 11px 12px;
        min-height: 94px;
        box-shadow: inset 0 0 18px rgba(59,130,246,.10);
        overflow: hidden;
    }
    .live-kpi {
        animation: cardBreathe 4.8s ease-in-out infinite;
    }
    .live-kpi:after {
        content: "";
        position: absolute;
        top: 0;
        left: -60%;
        width: 44%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(125,211,252,.28), transparent);
        transform: skewX(-18deg);
        animation: kpiSweep 5.2s ease-in-out infinite;
    }
    .kpi-label { color: #93c5fd; font-size: 12px; }
    .kpi-value {
        color: #67e8f9;
        font-size: 26px;
        font-weight: 900;
        line-height: 1.2;
        text-shadow: 0 0 14px rgba(34,211,238,.6);
    }
    .kpi-sub { color: #cbd5e1; font-size: 11px; margin-top: 4px; }
    .green .kpi-value { color: #6ee7b7; }
    .yellow .kpi-value { color: #fde68a; }
    .red .kpi-value { color: #fda4af; }
    .hero-metric {
        text-align: center;
        padding: 18px 12px;
        border: 1px solid rgba(34,211,238,.26);
        background: radial-gradient(circle, rgba(34,211,238,.18), rgba(37,99,235,.05) 54%, transparent 72%);
    }
    .hero-metric .number {
        font-size: 44px;
        font-weight: 900;
        color: #f8fafc;
        text-shadow: 0 0 24px rgba(34,211,238,.8);
    }
    .hero-metric .label { color: #7dd3fc; font-size: 14px; }
    .rank-row {
        display: grid;
        grid-template-columns: 30px 1fr 66px;
        align-items: center;
        gap: 8px;
        margin: 8px 0;
        color: #dbeafe;
        font-size: 13px;
    }
    .rank-index {
        color: #020617;
        background: linear-gradient(135deg, #67e8f9, #60a5fa);
        font-weight: 900;
        text-align: center;
        padding: 2px 0;
    }
    .bar {
        height: 9px;
        margin-top: 4px;
        background: rgba(30,64,175,.46);
        overflow: hidden;
    }
    .bar span {
        display: block;
        height: 100%;
        background: linear-gradient(90deg, #22d3ee, #3b82f6);
        box-shadow: 0 0 10px rgba(34,211,238,.7);
    }
    .ticker {
        display: flex;
        gap: 10px;
        overflow: hidden;
        color: #bfdbfe;
        font-size: 12px;
        white-space: nowrap;
        margin-top: 6px;
    }
    .ticker span {
        border: 1px solid rgba(56,189,248,.18);
        padding: 4px 8px;
        background: rgba(15,23,42,.52);
    }
    .stDataFrame { border: 1px solid rgba(56,189,248,.22); }
    </style>
    <div class="screen-frame"></div>
    """,
    unsafe_allow_html=True,
)


try:
    df_all = load_observations()
except Exception as exc:
    st.error(f"大屏数据读取失败：{exc}")
    st.stop()

quality_report = load_quality_report()
alignment_df = load_csv("alignment_candidates.csv")
source_mapping = load_csv("source_mapping.csv")
update_status = load_update_status()

asset_rating = build_asset_rating(df_all)
country_panel = build_country_panel(df_all)

total_rows = len(df_all)
valid_rows = int(df_all["value"].notna().sum())
missing_rows = total_rows - valid_rows
quality_rate = valid_rows / total_rows * 100 if total_rows else 0
latest_year = int(df_all["date_year"].max()) if pd.notna(df_all["date_year"].max()) else 0
earliest_year = int(df_all["date_year"].min()) if pd.notna(df_all["date_year"].min()) else 0
multi_source_assets = int((asset_rating["source_count"] >= 2).sum())
high_value_assets = int((asset_rating["asset_score"] >= 80).sum())
warning_count = 0
if not quality_report.empty and "status" in quality_report.columns:
    warning_count = int((quality_report["status"].astype(str) == "warning").sum())

status_text = update_status.get("status", "local")
finished_at = update_status.get("finished_at", "本地标准库")
selected_module = get_selected_module()

st.markdown(
    f"""
    <div class="topbar">
      <div class="title-box">
        <h1>EconAtlas 全球宏观经济数据要素大屏</h1>
        <p>Global Macro Data Asset Command Center</p>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)
render_live_status_row(status_text, finished_at)
module_dock(selected_module)

if selected_module:
    render_module_page(
        selected_module,
        df_all,
        asset_rating,
        country_panel,
        quality_report,
        alignment_df,
        source_mapping,
    )
    st.stop()

left, center, right = st.columns([1.15, 1.72, 1.15], gap="medium")

with left:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    section_title("数据资产总览", f"{earliest_year}-{latest_year}")
    k1, k2 = st.columns(2)
    with k1:
        kpi_card("标准观测总量", fmt_int(total_rows), "统一长表 macro_observations")
    with k2:
        kpi_card("有效观测占比", f"{quality_rate:.1f}%", f"缺失 {fmt_int(missing_rows)} 条", "green")
    k3, k4 = st.columns(2)
    with k3:
        kpi_card("标准指标", fmt_int(df_all["indicator_code"].nunique()), f"高价值资产 {high_value_assets} 个", "yellow")
    with k4:
        kpi_card("国家/地区", fmt_int(df_all["country_code"].nunique()), f"数据源 {df_all['source_organization'].nunique()} 类")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="panel">', unsafe_allow_html=True)
    section_title("数据源接入规模", "Source Coverage")
    source_counts = (
        df_all.groupby("source_organization")
        .size()
        .reset_index(name="rows")
        .sort_values("rows", ascending=True)
    )
    fig_source = px.bar(source_counts, x="rows", y="source_organization", orientation="h", text="rows")
    fig_source.update_traces(marker_color="#22d3ee", texttemplate="%{text:,}", textposition="outside")
    fig_source.update_layout(showlegend=False)
    st.plotly_chart(style_plotly(fig_source, 285), width="stretch", config={"displayModeBar": False})
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="panel">', unsafe_allow_html=True)
    section_title("资产排行 TOP 6", "Asset Score")
    top_assets = asset_rating.head(6).copy()
    max_score = max(top_assets["asset_score"].max(), 1)
    for idx, row in enumerate(top_assets.itertuples(index=False), start=1):
        name = row.indicator_name_zh if pd.notna(row.indicator_name_zh) else row.indicator_code
        width = max(8, float(row.asset_score) / max_score * 100)
        st.markdown(
            f"""
            <div class="rank-row">
              <div class="rank-index">{idx}</div>
              <div>
                <div>{name}</div>
                <div class="bar"><span style="width:{width:.1f}%"></span></div>
              </div>
              <div>{row.asset_score:.1f}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)

with center:
    st.markdown('<div class="panel earth-panel">', unsafe_allow_html=True)
    hero1, hero2, hero3 = st.columns(3)
    with hero1:
        st.markdown(
            f'<div class="hero-metric"><div class="number">{fmt_int(valid_rows)}</div><div class="label">有效观测记录</div></div>',
            unsafe_allow_html=True,
        )
    with hero2:
        st.markdown(
            f'<div class="hero-metric"><div class="number">{fmt_int(multi_source_assets)}</div><div class="label">多源可交叉验证资产</div></div>',
            unsafe_allow_html=True,
        )
    with hero3:
        st.markdown(
            f'<div class="hero-metric"><div class="number">{fmt_int(len(alignment_df))}</div><div class="label">指标对齐候选关系</div></div>',
            unsafe_allow_html=True,
        )
    section_title("全球数据资产态势", "Country Nodes")
    st.plotly_chart(draw_world_map(country_panel), width="content", config={"displayModeBar": False})
    ticker_items = []
    for row in country_panel.sort_values("valid_rows", ascending=False).head(8).itertuples(index=False):
        ticker_items.append(f"{row.country_name} {fmt_int(row.valid_rows)} 条 · {row.indicators} 指标")
    st.markdown(
        '<div class="ticker">' + "".join(f"<span>{item}</span>" for item in ticker_items) + "</div>",
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

    c1, c2 = st.columns([1, 1], gap="medium")
    with c1:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        section_title("近年数据增量", "Observation Flow")
        year_counts = (
            df_all.dropna(subset=["date_year"])
            .groupby("date_year")
            .size()
            .reset_index(name="rows")
            .sort_values("date_year")
        )
        year_counts = year_counts[year_counts["date_year"] >= max(earliest_year, latest_year - 12)]
        fig_year = px.area(year_counts, x="date_year", y="rows", markers=True)
        fig_year.update_traces(line_color="#67e8f9", fillcolor="rgba(34,211,238,.22)")
        st.plotly_chart(style_plotly(fig_year, 230), width="stretch", config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        section_title("频率结构", "A / M / D")
        freq_counts = df_all.groupby("frequency").size().reset_index(name="rows")
        fig_freq = px.pie(freq_counts, names="frequency", values="rows", hole=.66)
        fig_freq.update_traces(
            textinfo="label+percent",
            marker=dict(colors=["#22d3ee", "#3b82f6", "#34d399", "#facc15"]),
        )
        st.plotly_chart(style_plotly(fig_freq, 230), width="stretch", config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)
with right:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    section_title("治理健康度", "Quality Radar")
    radar = pd.DataFrame(
        {
            "dimension": ["完整性", "覆盖度", "多源性", "规模化", "新鲜度"],
            "score": [
                quality_rate,
                asset_rating["coverage_score"].mean(),
                asset_rating["source_score"].mean(),
                asset_rating["scale_score"].mean(),
                asset_rating["freshness_score"].mean(),
            ],
        }
    )
    fig_radar = go.Figure()
    fig_radar.add_trace(
        go.Scatterpolar(
            r=radar["score"],
            theta=radar["dimension"],
            fill="toself",
            line=dict(color="#22d3ee", width=2),
            fillcolor="rgba(34,211,238,.22)",
        )
    )
    fig_radar.update_layout(
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(visible=True, range=[0, 100], gridcolor="rgba(96,165,250,.22)"),
            angularaxis=dict(gridcolor="rgba(96,165,250,.18)"),
        ),
        showlegend=False,
    )
    st.plotly_chart(style_plotly(fig_radar, 260), width="stretch", config={"displayModeBar": False})
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    section_title("风险预警中心", f"{warning_count} 项质量警示")
    q1, q2 = st.columns(2)
    with q1:
        kpi_card("缺失观测", fmt_int(missing_rows), f"{100 - quality_rate:.2f}% missing", "red" if missing_rows else "green")
    with q2:
        kpi_card("映射关系", fmt_int(len(source_mapping)), "source_mapping.csv")
    if not quality_report.empty:
        warn_df = quality_report.copy()
        warn_df["status"] = warn_df["status"].astype(str)
        st.dataframe(
            warn_df,
            width="stretch",
            height=190,
            hide_index=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="panel">', unsafe_allow_html=True)
    section_title("国家节点 TOP 8", "Valid Rows")
    top_country = country_panel.sort_values("valid_rows", ascending=False).head(8)
    max_rows = max(top_country["valid_rows"].max(), 1)
    for idx, row in enumerate(top_country.itertuples(index=False), start=1):
        width = row.valid_rows / max_rows * 100
        st.markdown(
            f"""
            <div class="rank-row">
              <div class="rank-index">{idx}</div>
              <div>
                <div>{row.country_name} · {row.indicators} 指标 · {row.sources} 源</div>
                <div class="bar"><span style="width:{width:.1f}%"></span></div>
              </div>
              <div>{fmt_int(row.valid_rows)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)

render_event_ticker(df_all, quality_rate, warning_count, latest_year)
