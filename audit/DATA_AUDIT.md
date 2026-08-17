# EconAtlas 2.0 数据资产资格审计

生成时间：2026-08-17 10:41:51 CST

## 总体结果

- 总记录：65,079 条；有效数值：65,079 条（100.00%）。
- 覆盖：8 类来源、18 个国家（地区）、64 个标准指标、4 类频率。
- 序列数：950；多源指标：24 个。
- 原始/直接标准化记录：59,819；派生对齐记录：5,260（8.08%）。
- 业务键重复：0；未登记指标：0。

## 需要优先复核

- 仅覆盖单一国家（地区）的指标：16 个。
- 有效记录少于 100 条的来源：1 个。
- 完全无有效值的序列：0 条，不应计入有效覆盖。
- 当前数据层中的未来记录：0 条；预测情景层独立保存 1,355 条，不与历史实绩混合。
- 数据性质、来源状态和发布状态已经拆分为 `observation_type`、`source_status` 与 `release_status`。
- 完整性不能只用总缺失值衡量，还需结合指标的预期发布频率和适用国家建立预期时间轴。

### 覆盖较弱的国家（地区）

| country_code | country_name_zh | indicator_count | source_count | valid_rows |
| --- | --- | --- | --- | --- |
| EA | 欧元区 | 7 | 4 | 9671 |
| ID | 印度尼西亚 | 32 | 3 | 1110 |
| VN | 越南 | 36 | 2 | 984 |
| AR | 阿根廷 | 37 | 3 | 1141 |
| MX | 墨西哥 | 37 | 4 | 4237 |

### 数据量较少的来源

| source_organization | valid_rows | country_count | indicator_count | start_date | end_date |
| --- | --- | --- | --- | --- | --- |
| National Bureau of Statistics of China | 73 | 1 | 9 | 2024 | 2024-12 |
| FRED | 2086 | 1 | 19 | 2015 | 2026-07 |
| Eurostat | 2132 | 5 | 4 | 2015-01 | 2026-Q2 |
| OECD | 2171 | 17 | 1 | 2015-01 | 2026-07 |
| World Bank | 6054 | 17 | 37 | 2015 | 2025 |

## 审计产物

- `source_audit.csv`：来源真实贡献。
- `country_audit.csv`：国家覆盖广度与深度。
- `indicator_audit.csv`：指标覆盖、时间范围与多源情况。
- `series_audit.csv`：每条数据序列的长度、完整率和新鲜度。
- `country_indicator_matrix.csv`：国家—指标覆盖矩阵。
- `field_completeness.csv`：核心字段完整率。
- `zero_valid_series.csv`：完全没有有效数值的序列。
- `future_records.csv`：需区分预测与历史实绩的未来记录。
- `status_semantics.csv`：各来源状态字段的当前取值。