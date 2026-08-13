# -*- coding: utf-8 -*-
"""Streamlit Cloud entrypoint for EconAtlas.

Default view: showcase landing page.
Platform view: append ?page=platform to enter the big-screen dashboard.
"""

from __future__ import annotations

import base64
import mimetypes
import re
import runpy
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components


BASE_DIR = Path(__file__).resolve().parents[1]
SHOWCASE_DIR = BASE_DIR / "showcase"
BIGSCREEN_PATH = BASE_DIR / "dashboard" / "bigscreen_app.py"
MANUAL_PATH = SHOWCASE_DIR / "assets" / "econatlas-manual.pdf"


def query_value(name: str, default: str = "") -> str:
    try:
        value = st.query_params.get(name, default)
    except Exception:
        try:
            value = st.experimental_get_query_params().get(name, [default])[0]
        except Exception:
            value = default
    if isinstance(value, list):
        return value[0] if value else default
    return str(value or default)


page = query_value("page")

if page == "platform":
    runpy.run_path(str(BIGSCREEN_PATH), run_name="__main__")
    st.stop()


def render_manual_page() -> None:
    """Render a reliable in-app manual entry instead of opening a PDF data URI."""
    st.set_page_config(
        page_title="EconAtlas 平台使用手册",
        page_icon="EA",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    st.markdown(
        """
        <style>
        .stApp { background: linear-gradient(135deg, #f5faff 0%, #eef5ff 55%, #f8fbff 100%); }
        .block-container { max-width: 1080px; padding-top: 3rem; padding-bottom: 4rem; }
        #MainMenu, header, footer, [data-testid="stToolbar"] { visibility: hidden; height: 0; }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<a href="./" target="_self">← 返回官网首页</a>', unsafe_allow_html=True)
    st.title("EconAtlas 平台使用手册")
    st.caption("全球宏观经济数据要素服务平台 · 操作与展示指南")
    st.info("使用手册已改为站内入口，避免移动端打开空白新页面。可直接下载 PDF 后离线查看。")

    left, right = st.columns((1.15, 1), gap="large")
    with left:
        st.subheader("快速使用路径")
        st.markdown(
            """
            1. 进入平台后，从顶部导航选择指标查询、数据质量、治理驾驶舱或智能报告。
            2. 在页面筛选国家/地区、标准指标、频率与数据来源。
            3. 查看趋势、质量诊断、血缘关系或风险预警，并按需导出结果。
            4. 进入智能报告，生成可下载的宏观分析报告。
            """
        )
    with right:
        st.subheader("PDF 完整版")
        if MANUAL_PATH.exists():
            st.download_button(
                "下载平台使用手册（PDF）",
                data=MANUAL_PATH.read_bytes(),
                file_name="EconAtlas-平台使用手册.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        else:
            st.error("未找到平台使用手册文件，请联系项目维护者。")

    st.subheader("常用模块说明")
    columns = st.columns(3)
    for column, title, description in zip(
        columns,
        ("数据接入与治理", "指标分析与质量", "智能报告与展示"),
        (
            "统一处理多源宏观数据、字段标准与治理规则。",
            "查询指标、检查数据质量，并追踪一致性与血缘。",
            "汇聚趋势、风险与治理信息，生成报告并进入大屏展示。",
        ),
    ):
        with column:
            st.markdown(f"#### {title}")
            st.write(description)


if page == "manual":
    render_manual_page()
    st.stop()


st.set_page_config(
    page_title="EconAtlas 全球宏观经济数据要素服务平台",
    page_icon="EA",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def asset_data_uri(match: re.Match) -> str:
    relative = match.group(0)
    path = SHOWCASE_DIR / relative
    if not path.exists():
        return relative
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{data}"


def load_showcase_html() -> str:
    html = (SHOWCASE_DIR / "index.html").read_text(encoding="utf-8")
    html = html.replace(
        'href="assets/econatlas-manual.pdf" target="_blank" rel="noreferrer"',
        'href="?page=manual" target="_parent"',
    )
    html = re.sub(r"assets/[A-Za-z0-9_.-]+", asset_data_uri, html)
    html = html.replace('href="http://localhost:8508/" target="_blank"', 'href="?page=platform" target="_parent"')
    html = html.replace('href="http://localhost:8508/"', 'href="?page=platform" target="_parent"')
    resize_script = """
    <script>
      (() => {
        const updateFrameHeight = () => {
          const height = Math.ceil(document.documentElement.scrollHeight);
          window.parent.postMessage({
            isStreamlitMessage: true,
            type: "streamlit:setFrameHeight",
            height,
          }, "*");
        };

        window.addEventListener("load", updateFrameHeight);
        window.addEventListener("resize", updateFrameHeight);
        new ResizeObserver(updateFrameHeight).observe(document.body);
        requestAnimationFrame(updateFrameHeight);
      })();
    </script>
    """
    return html.replace("</body>", f"{resize_script}</body>")


st.markdown(
    """
    <style>
    .stApp { background: #fff; }
    .block-container {
        max-width: 100% !important;
        padding: 0 !important;
    }
    #MainMenu, header, footer, [data-testid="stToolbar"] {
        visibility: hidden;
        height: 0;
    }
    iframe {
        display: block;
        border: 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

components.html(load_showcase_html(), height=5600, scrolling=True)
