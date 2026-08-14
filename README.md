# EconAtlas 全球宏观经济指标数据要素服务平台

EconAtlas 面向“全球宏观经济指标数据要素采集与结构化服务”场景，提供权威数据源接入、指标语义治理、质量门禁、结构化查询、智能问答与智能研报服务。生产入口为 FastAPI 管理面板；宏观数据问题先检索 EconAtlas，普通问题由 DeepSeek 直接回答。

## 当前能力与数据边界

- 接入 8 类来源：World Bank、IMF WEO、FRED、OECD、Eurostat、ECB、BIS、中国国家统计局样例数据
- 标准库共 66,627 条观测，其中已发布及派生数据 65,272 条、独立隔离的预测情景 1,355 条
- 覆盖 18 个国家（地区）、64 个有数据指标、年/季/月/日 4 种频率
- 123 个来源指标参与自动对齐：48 个自动通过，75 个进入人工复核；候选不会直接覆盖正式映射
- 13 项可执行质量契约、23 组批量查询验收、30 项自动测试
- 当前统计与检索默认排除预测值，预测只在显式情景查询中使用

## 功能结构

管理面板保留“平台总览”，并按用途整合为四组：

- 数据服务：指标查询、指标字典、JSON 输出、数据资产目录、数据源接入中心、批量查询与验收、API 服务中心
- 质量治理：数据质量、一致性分析、治理驾驶舱、指标血缘、治理规则、版本与修订记录、风险预警、资产评级、指标对齐审核
- 智能应用：智能问答、智能研报（原“智能分析”和“智能报告”合并）
- 运行保障：系统运行

智能研报在同一页面完成数据选择、趋势图、基于证据的 DeepSeek 分析及 PDF、Markdown、JSON、CSV 下载。原版 EconAtlas 标志和比赛要求的 JSON 输出等模块均予保留。

## 目录结构

- `main_collect.py`：采集、标准化、合并、治理、质量门禁和入库主流程
- `collectors/`：各数据源采集器
- `standardizer/`：字段、指标和状态标准化
- `governance/`：语义模型、质量契约、版本修订检测
- `quality/`：质量报告与发布门禁
- `services/`：结构化查询和智能问答服务
- `api_service/app.py`：FastAPI 接口
- `api_service/panel.py`：统一管理面板
- `metadata/`：指标字典、来源映射、对齐候选、版本修订和运行清单
- `data_clean/macro_observations.csv`：标准化长表
- `data_clean/macrohub.db`：SQLite 标准库（文件名为开发阶段遗留）
- `dashboard/`：保留的历史展示入口，不作为 Render 生产入口

## 安装与数据构建

```bash
pip install -r requirements.txt
python main_collect.py
```

常用模式：

```bash
python main_collect.py --force-refresh
python main_collect.py --merge-only
python main_collect.py --standardize-only
```

主要产物：

- `data_clean/macro_observations.csv`
- `data_clean/macrohub.db`
- `data_clean/quality_report.csv`
- `data_clean/quality_coverage_report.csv`
- `data_clean/quality_consistency_report.csv`
- `data_clean/quality_outlier_report.csv`
- `data_clean/quality_gate.json`
- `metadata/alignment_candidates.csv`
- `metadata/revision_events.csv`
- `metadata/run_manifest.json`

## CLI 与 FastAPI

```bash
python query_cli.py --country US --indicator CPI_YOY_A --start 2020 --end 2024 --frequency A
python query_cli.py --batch examples/sample_queries.json --output examples/sample_outputs.json
uvicorn api_service.app:app --reload
```

本地接口文档：`http://127.0.0.1:8000/docs`。

核心接口：

- 查询输出：`GET /query`、`POST /batch_query`、`GET /metadata`
- 数据治理：`GET /quality-status`、`GET /quality-contracts`、`GET /lineage`、`GET /alignment-candidates`、`POST /alignment-reviews`
- 运行审计：`GET /source-center`、`GET /revision-history`、`POST /acceptance-tests`、`GET /system-status`
- 智能应用：`POST /chat`、`POST /reports/generate`、`GET /reports/pdf`

## 指标对齐与发布治理

正式映射以 `metadata/source_mapping.csv` 为准。候选生成采用“硬约束 + 词法/语义相似度 + 单位与频率 + 数值行为 + 上下文证据”的混合评分：

```bash
python scripts/generate_alignment_candidates.py
```

系统保留每个候选的备选项、分项得分、推荐理由和审核状态。人工批准仅写入审核台账；必须再合并进正式映射并通过下一次质量门禁，才会进入发布库，避免在线审核直接篡改标准库。

## Render 部署与自定义域名

`render.yaml` 使用 Python 3.11，生产启动命令为：

```bash
uvicorn api_service.app:app --host 0.0.0.0 --port $PORT
```

健康检查路径为 `/health`。Render 连接 GitHub 后随 `main` 分支提交自动部署，正式地址为 `https://data.shiwenbrief.com`。

`DEEPSEEK_API_KEY`、飞书 Webhook 和邮箱授权码必须通过 Render Environment Variables 或 GitHub Actions Secrets 注入。默认 DeepSeek 模型由 `DEEPSEEK_MODEL` 配置；未配置密钥时，结构化查询、质量治理和证据检索仍可使用。

## 自动更新与通知

`.github/workflows/scheduled-data-update.yml` 默认每周一北京时间 09:20 自动执行，也支持手动触发。任务依次运行测试、采集、标准化、对齐候选、质量契约、发布门禁、SQLite 重建、审计归档与通知；门禁失败不会提交数据。

可按需配置：

- 飞书：`FEISHU_WEBHOOK_URL`
- 邮件：`SMTP_HOST`、`SMTP_PORT`、`SMTP_USERNAME`、`SMTP_PASSWORD`、`SMTP_FROM`、`SMTP_TO`
- DeepSeek：`DEEPSEEK_API_KEY`、`DEEPSEEK_BASE_URL`、`DEEPSEEK_MODEL`

本地检查：

```bash
python scripts/scheduled_update.py --dry-run
python scripts/notify_update.py --dry-run
python -m unittest discover -s tests -v
```

## 已知边界

- IMF WEO 当前通过本地官方 CSV 导入
- 中国官方数据当前使用本地官方样例文件，已形成标准化流程，但仍需扩充正式批次
- 在线采集依赖外部机构可用性及网络环境
- 预测情景与当前已发布数据物理共表、逻辑隔离；所有当前统计接口显式过滤 `observation_type = 'forecast'`
