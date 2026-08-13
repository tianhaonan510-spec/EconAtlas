# EconAtlas 2.0 数据资产资格审计

生成时间：2026-08-13 17:27:32 CST

## 总体结果

- 总记录：65,578 条；有效数值：65,578 条（100.00%）。
- 覆盖：8 类来源、18 个国家（地区）、64 个标准指标、4 类频率。
- 序列数：974；多源指标：24 个。
- 原始/直接标准化记录：60,400；派生对齐记录：5,178（7.90%）。
- 业务键重复：0；未登记指标：0。

## 需要优先复核

- 仅覆盖单一国家（地区）的指标：16 个。
- 有效记录少于 100 条的来源：1 个。
- 完全无有效值的序列：0 条，不应计入有效覆盖。
- 当前年份之后的记录：1,355 条，需显式标记为预测值，不能与历史实绩混合。
- `status` 字段存在 3 种值，当前混合数据性质和来源状态码，需拆分语义。
- 完整性不能只用总缺失值衡量，还需结合指标的预期发布频率和适用国家建立预期时间轴。

### 覆盖较弱的国家（地区）

| country_code | country_name_zh | indicator_count | source_count | valid_rows |
| --- | --- | --- | --- | --- |
| EA | 欧元区 | 7 | 4 | 9515 |
| VN | 越南 | 36 | 2 | 1055 |
| ID | 印度尼西亚 | 37 | 3 | 1235 |
| AR | 阿根廷 | 38 | 3 | 1216 |
| SA | 沙特阿拉伯 | 38 | 3 | 1233 |

### 数据量较少的来源

| source_organization | valid_rows | country_count | indicator_count | start_date | end_date |
| --- | --- | --- | --- | --- | --- |
| National Bureau of Statistics of China | 73 | 1 | 9 | 2024 | 2024-12 |
| FRED | 2054 | 1 | 19 | 2015 | 2026-05 |
| Eurostat | 2132 | 5 | 4 | 2015-01 | 2026-Q2 |
| OECD | 2153 | 17 | 1 | 2015-01 | 2026-04 |
| World Bank | 5924 | 17 | 37 | 2015 | 2025 |

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