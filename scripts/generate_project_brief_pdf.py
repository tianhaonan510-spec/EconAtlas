# -*- coding: utf-8 -*-
from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


PROJECT_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = PROJECT_DIR.parents[1]
OUT_FILE = ROOT_DIR / "MacroHub全球宏观经济指标数据要素服务平台项目详解.pdf"
DB_PATH = PROJECT_DIR / "data_clean" / "macrohub.db"
INDICATOR_PATH = PROJECT_DIR / "metadata" / "indicator_master.csv"
QUALITY_PATH = PROJECT_DIR / "data_clean" / "quality_report.csv"


def register_fonts():
    font_candidates = [
        Path("C:/Windows/Fonts/msyh.ttc"),
        Path("C:/Windows/Fonts/simhei.ttf"),
        Path("C:/Windows/Fonts/simsun.ttc"),
    ]
    bold_candidates = [
        Path("C:/Windows/Fonts/msyhbd.ttc"),
        Path("C:/Windows/Fonts/simhei.ttf"),
        Path("C:/Windows/Fonts/simsunb.ttf"),
    ]
    font = next((p for p in font_candidates if p.exists()), None)
    bold = next((p for p in bold_candidates if p.exists()), font)
    if not font:
        return "Helvetica", "Helvetica-Bold"
    pdfmetrics.registerFont(TTFont("MacroHubCN", str(font)))
    pdfmetrics.registerFont(TTFont("MacroHubCN-Bold", str(bold)))
    return "MacroHubCN", "MacroHubCN-Bold"


FONT, FONT_BOLD = register_fonts()


def p(text, style):
    return Paragraph(str(text).replace("\n", "<br/>"), style)


def make_styles():
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="CNTitle",
            parent=styles["Title"],
            fontName=FONT_BOLD,
            fontSize=22,
            leading=30,
            alignment=1,
            textColor=colors.HexColor("#0f2f5f"),
            spaceAfter=18,
        )
    )
    styles.add(
        ParagraphStyle(
            name="CNH1",
            parent=styles["Heading1"],
            fontName=FONT_BOLD,
            fontSize=15,
            leading=22,
            textColor=colors.HexColor("#123d7a"),
            spaceBefore=12,
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="CNH2",
            parent=styles["Heading2"],
            fontName=FONT_BOLD,
            fontSize=12,
            leading=18,
            textColor=colors.HexColor("#1d4f91"),
            spaceBefore=8,
            spaceAfter=5,
        )
    )
    styles.add(
        ParagraphStyle(
            name="CNBody",
            parent=styles["BodyText"],
            fontName=FONT,
            fontSize=9.5,
            leading=15,
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="CNSmall",
            parent=styles["BodyText"],
            fontName=FONT,
            fontSize=8,
            leading=12,
        )
    )
    return styles


STYLES = make_styles()


def load_data():
    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql_query("SELECT * FROM macro_observations", conn)
    indicators = pd.read_csv(INDICATOR_PATH, encoding="utf-8-sig")
    quality = pd.read_csv(QUALITY_PATH, encoding="utf-8-sig")
    return df, indicators, quality


def build_table(rows, col_widths=None, font_size=8):
    converted = []
    for row in rows:
        converted.append([p(cell, STYLES["CNSmall"]) for cell in row])
    table = Table(converted, colWidths=col_widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), FONT),
                ("FONTSIZE", (0, 0), (-1, -1), font_size),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dbeafe")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def source_table(df):
    rows = [["数据源", "机构类型", "数据内容", "频率", "观测值", "接入方式"]]
    source_desc = {
        "World Bank": ["国际组织", "GDP、CPI、失业率、贸易、外储、债务、经常账户等跨国年频指标", "A", "World Bank Indicators API"],
        "IMF": ["国际组织", "WEO 年频宏观指标，支持与 World Bank 多来源校验", "A", "本地 IMF WEO 公开 CSV 转换"],
        "FRED": ["官方研究数据库", "美国 CPI、失业率、工业生产、联邦基金利率等月频指标", "M", "FRED graph CSV"],
        "OECD": ["国际组织", "OECD/G20 经济体 CPI 月频同比", "M", "OECD SDMX API"],
        "Eurostat": ["区域官方统计机构", "欧元区及欧洲主要国家 HICP 月频同比", "M", "Eurostat Dissemination API"],
        "ECB": ["区域央行", "欧元兑美元日频参考汇率", "D", "ECB Data Portal API"],
        "BIS": ["国际组织", "多国本币兑美元日频汇率", "D", "BIS SDMX CSV API"],
        "National Bureau of Statistics of China": ["国家官方统计机构", "中国 CPI、PPI、工业增加值等月频指标（本地官方文件导入）", "M", "国家统计局官方数据文件导入"],
    }
    counts = df.groupby("source_organization").size().to_dict()
    for source in ["World Bank", "IMF", "FRED", "OECD", "Eurostat", "ECB", "BIS", "National Bureau of Statistics of China"]:
        if source not in source_desc:
            continue
        meta = source_desc[source]
        rows.append([source, meta[0], meta[1], meta[2], f"{counts.get(source, 0):,}", meta[3]])
    return rows


def indicator_table(indicators):
    rows = [["标准指标编码", "中文名称", "英文名称", "频率", "单位", "口径", "来源数"]]
    for _, row in indicators.iterrows():
        rows.append(
            [
                row["indicator_code"],
                row["indicator_name_zh"],
                row["indicator_name_en"],
                row["frequency"],
                row["unit"],
                f"{row['seasonal_adjustment']} / {row['calculation']}",
                str(row.get("source_count", "")),
            ]
        )
    return rows


def dashboard_table():
    return [
        ["板块", "功能说明", "面向的展示价值"],
        ["指标查询", "按国家/地区、标准指标、频率、数据源、时间范围查询并绘制趋势图。", "证明工具可按赛题要求进行灵活检索。"],
        ["指标字典", "展示标准指标编码、中文/英文名称、单位、频率、季调和计算口径。", "体现统一指标体系设计。"],
        ["数据质量", "展示缺失值、重复值、来源 URL、覆盖率、一致性、异常值等校验结果。", "体现数据治理和可复核能力。"],
        ["JSON 输出", "将查询结果按标准结构输出为 JSON，包含 request、series、source、observations、error。", "支撑 API、AIGC/Agent 和外部系统调用。"],
        ["一致性分析", "对同一指标在多来源下的数值差异进行比较。", "体现 IMF、World Bank、OECD、Eurostat 等来源的交叉校验能力。"],
        ["治理驾驶舱", "总览数据源、指标、国家、观测值和质量指标。", "适合作为汇报开场页。"],
        ["指标血缘", "展示来源机构、原始指标代码、标准指标编码之间的映射链路。", "证明数据来源可追溯。"],
        ["治理规则", "说明指标映射、频率统一、单位统一、缺失值处理、多来源冲突处理等规则。", "对应赛题标准化治理要求。"],
        ["API 服务中心", "展示 FastAPI 查询地址、参数、请求示例和返回示例。", "证明项目可作为数据服务使用。"],
        ["数据资产目录", "按指标沉淀数据资产，统计覆盖国家、来源数、观测规模和质量分。", "体现数据要素资产化。"],
        ["风险预警", "识别缺失值、多源覆盖不足、更新时间缺失、多来源偏差等风险。", "体现数据质量监控能力。"],
        ["智能分析", "基于趋势、均值、最新值和规则生成指标解读与风险等级。", "体现面向智能投研的应用价值。"],
        ["智能报告", "自动生成 Markdown、PDF、JSON、CSV 报告下载。", "体现端到端报告交付能力。"],
        ["资产评级", "按覆盖度、来源数、质量和可调用性对数据资产进行评级。", "辅助评委理解数据资产价值。"],
    ]


def build_pdf():
    df, indicators, quality = load_data()
    doc = SimpleDocTemplate(
        str(OUT_FILE),
        pagesize=A4,
        rightMargin=1.4 * cm,
        leftMargin=1.4 * cm,
        topMargin=1.4 * cm,
        bottomMargin=1.2 * cm,
        title="MacroHub 全球宏观经济指标数据要素服务平台项目详解",
    )

    countries = sorted(df["country_code"].dropna().unique().tolist())
    sources = sorted(df["source_organization"].dropna().unique().tolist())
    freqs = sorted(df["frequency"].dropna().unique().tolist())
    source_counts = df.groupby(["source_organization", "frequency"]).size().reset_index(name="rows")
    quality_map = dict(zip(quality["check_item"], quality["value"]))

    story = []
    story.append(p("MacroHub 全球宏观经济指标数据要素服务平台项目详解", STYLES["CNTitle"]))
    story.append(p("面向“全球宏观经济指标数据要素采集与结构化服务”赛题的项目说明材料", STYLES["CNBody"]))
    story.append(Spacer(1, 0.2 * cm))

    summary_rows = [
        ["项目指标", "当前规模"],
        ["数据源数量", f"{len(sources)} 个：{', '.join(sources)}"],
        ["标准指标数", f"{df['indicator_code'].nunique()} 个"],
        ["国家/地区覆盖", f"{df['country_code'].nunique()} 个：{', '.join(countries)}"],
        ["总观测值", f"{len(df):,} 条"],
        ["频率覆盖", f"{', '.join(freqs)}（年频/月频/日频）"],
        ["数据库文件", "data_clean/macrohub.db"],
        ["结构化输出", "CLI、FastAPI、Streamlit 页面均支持 JSON 输出"],
    ]
    story.append(build_table(summary_rows, [4 * cm, 12 * cm]))

    story.append(p("一、项目定位", STYLES["CNH1"]))
    story.append(
        p(
            "MacroHub 是一个面向金融研究、宏观分析、数据服务和智能投研场景的全球宏观经济指标数据要素平台。"
            "项目围绕赛题提出的“权威数据源接入、统一指标标准化、结构化查询输出、质量校验与结果展示”要求，"
            "构建了从数据采集、标准化治理、质量检查、数据库入库、API 服务到可视化展示的完整链路。",
            STYLES["CNBody"],
        )
    )

    story.append(p("二、总体架构", STYLES["CNH1"]))
    story.append(
        p(
            "项目采用分层架构：数据源接入层负责从 World Bank、IMF、FRED、OECD、Eurostat、ECB 获取数据；"
            "标准化治理层负责统一国家代码、指标编码、单位、频率、季调标识和计算口径；"
            "数据存储层将标准长表写入 CSV 与 SQLite；服务层通过 CLI 与 FastAPI 提供结构化查询；"
            "展示层通过 Streamlit 提供查询、质量、血缘、资产目录、风险预警和智能报告等交互页面。",
            STYLES["CNBody"],
        )
    )
    arch_rows = [
        ["层级", "核心文件/目录", "职责"],
        ["数据接入层", "collectors/", "实现 World Bank、IMF、FRED、OECD、Eurostat、ECB 采集器，支持缓存和重试。"],
        ["配置与字典层", "config.py, metadata/", "维护国家字典、指标字典、来源映射和采集批次信息。"],
        ["标准化治理层", "standardizer/standardize.py, main_collect.py", "将不同来源转换为统一长表 macro_observations。"],
        ["质量检查层", "quality/check_quality.py", "生成总览、覆盖率、一致性、异常值等质量报告。"],
        ["存储层", "data_clean/macrohub.db", "使用 SQLite 保存标准化观测值，并建立查询索引。"],
        ["服务层", "services/query_service.py, api_service/app.py, query_cli.py", "提供单条查询、批量查询和标准 JSON 输出。"],
        ["展示层", "dashboard/streamlit_app.py", "提供多板块可视化、分析、下载和汇报展示。"],
    ]
    story.append(build_table(arch_rows, [3 * cm, 5 * cm, 8 * cm]))

    story.append(PageBreak())
    story.append(p("三、数据源与数据规模", STYLES["CNH1"]))
    story.append(
        p(
            "当前平台接入 6 个权威来源，覆盖国际组织、区域官方统计机构、央行和官方研究数据库。"
            "数据源既包含跨国年频宏观底座，也包含月频价格指标和日频金融指标。",
            STYLES["CNBody"],
        )
    )
    story.append(build_table(source_table(df), [2.4 * cm, 2.5 * cm, 5.1 * cm, 1.2 * cm, 1.7 * cm, 3.2 * cm]))

    story.append(p("来源与频率分布", STYLES["CNH2"]))
    sf_rows = [["数据源", "频率", "观测值"]]
    for _, row in source_counts.iterrows():
        sf_rows.append([row["source_organization"], row["frequency"], f"{int(row['rows']):,}"])
    story.append(build_table(sf_rows, [5 * cm, 4 * cm, 4 * cm]))

    story.append(p("四、标准指标体系", STYLES["CNH1"]))
    story.append(
        p(
            "平台将不同机构的原始指标代码映射到统一的 indicator_code，并保留原始来源代码、来源机构、数据集名称、"
            "单位、频率、季调状态、计算口径、更新时间和采集时间。这样既能统一查询，又能保持数据可追溯。",
            STYLES["CNBody"],
        )
    )
    story.append(build_table(indicator_table(indicators), [3.6 * cm, 3 * cm, 4.1 * cm, 1 * cm, 2.2 * cm, 1.8 * cm, 1 * cm]))

    story.append(PageBreak())
    story.append(p("五、核心功能板块说明", STYLES["CNH1"]))
    story.append(build_table(dashboard_table(), [3.2 * cm, 7 * cm, 5.6 * cm]))

    story.append(p("六、查询与 JSON 输出", STYLES["CNH1"]))
    story.append(
        p(
            "平台支持按国家/地区、标准指标、频率、时间范围和数据源进行查询。"
            "当同一指标命中多个来源时，返回结果会拆分为多个 series，每个 series 保留独立 source 和 observations，"
            "避免多来源数据在同一个来源字段下混淆。",
            STYLES["CNBody"],
        )
    )
    json_rows = [
        ["方式", "示例"],
        ["CLI 单条查询", "python query_cli.py --country US --indicator CPI_YOY_A --start 2020 --end 2024 --frequency A"],
        ["CLI 批量查询", "python query_cli.py --batch examples/sample_queries.json --output examples/sample_outputs.json"],
        ["API 服务", "uvicorn api_service.app:app --reload"],
        ["GET 查询", "/query?country=DE&indicator=CPI_YOY_M&start=2024-01&end=2024-12&frequency=M"],
        ["POST 批量查询", "/batch_query，提交 queries 数组"],
    ]
    story.append(build_table(json_rows, [3.4 * cm, 12.2 * cm]))
    story.append(
        p(
            "JSON 核心字段包括 request、series、indicator_code、country_code、frequency、unit、seasonal_adjustment、"
            "calculation、source.organization、source.dataset、source.source_series_code、last_updated、observations[].date、"
            "observations[].value、observations[].status 和 error。",
            STYLES["CNBody"],
        )
    )

    story.append(p("七、数据质量与治理机制", STYLES["CNH1"]))
    q_rows = [["质量项", "当前值", "状态"]]
    for _, row in quality.iterrows():
        q_rows.append([row["check_item"], str(row["value"]), row["status"]])
    story.append(build_table(q_rows, [6 * cm, 4 * cm, 3 * cm]))
    story.append(
        p(
            "质量报告包含：总行数、缺失值数量、重复主键数量、来源 URL 缺失数量、国家数量、指标数量、来源数量、"
            "频率数量、覆盖率明细、多来源一致性差异和异常值识别。缺失值和异常值保留为质量预警项，便于后续补源或解释。",
            STYLES["CNBody"],
        )
    )

    story.append(p("八、运行与交付方式", STYLES["CNH1"]))
    run_rows = [
        ["任务", "命令"],
        ["启动可视化页面", "streamlit run dashboard/streamlit_app.py"],
        ["启动 API", "uvicorn api_service.app:app --reload"],
        ["重新合并并入库", "python main_collect.py --merge-only"],
        ["完整重新采集", "python main_collect.py"],
        ["仅采集 OECD", "python main_collect.py --oecd-only"],
        ["仅采集 Eurostat", "python main_collect.py --eurostat-only"],
        ["仅采集 ECB", "python main_collect.py --ecb-only"],
    ]
    story.append(build_table(run_rows, [4 * cm, 11 * cm]))

    story.append(p("九、项目亮点与可讲述方向", STYLES["CNH1"]))
    highlights = [
        "1. 从 6 个权威来源形成统一宏观数据底座，兼顾国际组织、官方统计机构和央行数据。",
        "2. 指标体系统一到 16 个标准指标，覆盖年频、月频、日频，解决来源分散、口径不一和命名不一致问题。",
        "3. JSON 输出既支持单条查询，也支持批量查询，可服务于 AIGC/Agent、金融研究系统和外部数据服务。",
        "4. 保留 source_url、source_dataset、source_indicator_code、last_updated、retrieved_at、data_version 等字段，增强可追溯性。",
        "5. 通过覆盖率、多来源一致性、异常值和风险预警机制，将数据治理从“展示”延伸到“可复核”。",
        "6. Streamlit 页面覆盖查询、字典、质量、血缘、治理规则、API、资产目录、智能分析和报告生成，适合现场演示。",
    ]
    for item in highlights:
        story.append(p(item, STYLES["CNBody"]))

    doc.build(story)
    return OUT_FILE


if __name__ == "__main__":
    print(build_pdf())
