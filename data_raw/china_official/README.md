# 中国官方数据导入说明

国家统计局网页接口在无人值守环境中会拒绝请求，因此项目使用“官方文件＋清单＋SHA-256＋云端导入”方案，不绕过官方网站访问限制。

使用方式：

1. 从国家统计局数据网站下载月度数据：`https://data.stats.gov.cn/`
2. 整理为 UTF-8 CSV，放在本目录下。
3. 计算文件 SHA-256，将文件名、哈希、发布机构、官方页面和获取方式登记到 `manifest.json`。
4. CSV 至少包含以下字段：

```csv
indicator_code,date,value,source_url,last_updated,status,data_version
CN_CPI_YOY_M,2024-01,0.3,https://data.stats.gov.cn/,2024-02-08,official,2024-02-08
CN_PPI_YOY_M,2024-01,-2.5,https://data.stats.gov.cn/,2024-02-08,official,2024-02-08
CN_INDUSTRIAL_VALUE_ADDED_YOY_M,2024-01,6.8,https://data.stats.gov.cn/,2024-02-08,official,2024-02-08
```

支持的 `indicator_code`：

- `CN_CPI_YOY_M`：中国居民消费价格指数同比
- `CN_PPI_YOY_M`：中国工业生产者出厂价格指数同比
- `CN_INDUSTRIAL_VALUE_ADDED_YOY_M`：中国规模以上工业增加值同比
- `CN_RETAIL_SALES_YOY_M`：社会消费品零售总额同比
- `CN_FIXED_ASSET_INVESTMENT_YTD_YOY_M`：固定资产投资累计同比
- `CN_URBAN_SURVEYED_UNEMPLOYMENT_RATE_M`：城镇调查失业率
- `CN_MANUFACTURING_PMI_M`：制造业 PMI
- `CN_M1_YOY_M`、`CN_M2_YOY_M`：人民银行货币供应量同比
- `CN_TOTAL_SOCIAL_FINANCING_FLOW_M`：社会融资规模增量
- `CN_EXPORTS_USD_YOY_M`、`CN_IMPORTS_USD_YOY_M`：海关总署月度进出口同比

当前 `nbs_2024_monthly_sample.csv` 在清单中标记为 `sample`，只用于初赛功能验证，不计入 2.0 核心资产。

导入命令：

```bash
python main_collect.py --china-official-only
python main_collect.py --merge-only
```
