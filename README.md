# EconAtlas 全球宏观经济指标数据要素服务平台

EconAtlas 面向“全球宏观经济指标数据要素采集与结构化服务”场景，提供权威数据源接入、指标标准化治理、质量校验、SQLite 入库、CLI/FastAPI 查询和 Streamlit 可视化展示。

## 项目能力概览

- 已接入 8 类数据源：World Bank、IMF WEO、FRED、OECD、Eurostat、ECB、BIS、中国国家统计局样例数据
- 已沉淀 61 个标准指标、18 个国家（地区）、66,002 条观测值
- 支持年频、月频、日频数据统一查询
- 支持标准 JSON 输出、批量查询、多来源一致性分析、风险预警、智能报告和资产评级
- 支持半自动指标对齐审核，当前已生成 82 条候选关系，均为高可信且已确认

## 目录结构

- `main_collect.py`：采集、标准化、合并入库主流程
- `collectors/`：各数据源采集器
- `standardizer/`：标准化处理模块
- `services/`：查询服务逻辑
- `api_service/app.py`：FastAPI 接口
- `dashboard/streamlit_app.py`：Streamlit Cloud 入口，默认展示宣传页
- `dashboard/full_platform_app.py`：完整平台旧版入口
- `dashboard/bigscreen_app.py`：EconAtlas 数据要素大屏
- `metadata/`：指标字典、来源映射、国家字典、运行清单、对齐候选结果
- `data_clean/macro_observations.csv`：标准化长表
- `data_clean/macrohub.db`：SQLite 数据库，文件名沿用开发阶段命名，实际承载 EconAtlas 平台标准化数据

## 安装依赖

```bash
pip install -r requirements.txt
```

建议使用 Python 3.9 及以上版本。

## 数据构建

执行完整采集与入库：

```bash
python main_collect.py
```

常用模式：

```bash
python main_collect.py --force-refresh
python main_collect.py --merge-only
python main_collect.py --standardize-only
```

生成结果包括：

- `data_clean/macro_observations.csv`
- `data_clean/macrohub.db`
- `data_clean/quality_report.csv`
- `data_clean/quality_coverage_report.csv`
- `data_clean/quality_consistency_report.csv`
- `data_clean/quality_outlier_report.csv`
- `data_clean/performance_report.csv`
- `metadata/run_manifest.json`

## CLI 查询

单条查询示例：

```bash
python query_cli.py --country US --indicator CPI_YOY_A --start 2020 --end 2024 --frequency A
```

中国日频汇率查询示例：

```bash
python query_cli.py --country CN --indicator EXCHANGE_RATE_USD_D --start 2024-01-02 --end 2024-01-10 --frequency D --source BIS
```

批量查询示例：

```bash
python query_cli.py --batch examples/sample_queries.json --output examples/sample_outputs.json
```

## FastAPI 服务

启动服务：

```bash
uvicorn api_service.app:app --reload
```

访问文档：

```text
http://127.0.0.1:8000/docs
```

主要接口：

- `GET /query`
- `POST /batch_query`
- `GET /metadata`
- `GET /health`

## Streamlit 展示

```bash
streamlit run dashboard/streamlit_app.py
```

默认展示 EconAtlas 宣传页；点击页面中的“进入平台”会跳转到数据要素大屏，也可直接访问 `?page=platform`。若需查看完整平台旧版入口，可运行：

```bash
streamlit run dashboard/full_platform_app.py
```

完整平台包含指标查询、指标字典、数据质量、JSON 输出、一致性分析、治理驾驶舱、指标血缘、治理规则、API 服务中心、数据资产目录、风险预警、智能分析、智能报告、资产评级和指标对齐审核等模块。

## 半自动指标对齐审核

正式映射关系以 `metadata/source_mapping.csv` 为准，同时可使用候选推荐脚本生成审核结果：

```bash
python scripts/generate_alignment_candidates.py
```

输出文件：

```text
metadata/alignment_candidates.csv
```

候选结果包含来源机构、来源数据集、原始指标代码、正式标准指标、候选标准指标、匹配得分、置信等级、推荐理由、审核状态、覆盖国家数量和观测值数量等字段。当前版本共生成 82 条候选关系，全部为高可信且已确认。

## 定时更新与调度

平台查询默认读取本地标准库 `data_clean/macrohub.db`。外部数据源通过调度任务定期刷新，推荐采用“固定时间自动采集 + 必要时手动强制刷新”的运行方式。

手动执行一次调度更新：

```bash
python scripts/scheduled_update.py
```

强制刷新外部数据：

```bash
python scripts/scheduled_update.py --force-refresh
```

仅检查调度配置：

```bash
python scripts/scheduled_update.py --dry-run
```

注册 Windows 定时任务：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/register_windows_task.ps1
```

调度状态写入 `metadata/update_status.json`，调度日志写入 `logs/scheduled_update.log`。

## 已知边界

- IMF WEO 当前通过本地官方 CSV 文件导入
- 中国官方数据当前通过本地官方样例文件导入，并已形成标准化入库流程
- World Bank、FRED、OECD、Eurostat、ECB、BIS 的在线采集依赖外部网络
- 当前数据库文件名仍为 `macrohub.db`，属于开发阶段遗留命名，不影响平台对外统一名称为 EconAtlas
