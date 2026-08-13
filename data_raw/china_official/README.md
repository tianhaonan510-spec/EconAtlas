# 中国官方数据导入说明

国家统计局网页接口在自动化环境中不稳定，因此项目提供本地官方文件导入器。

使用方式：

1. 从国家统计局数据网站下载月度数据：`https://data.stats.gov.cn/`
2. 整理为 UTF-8 CSV，放在本目录下。
3. CSV 至少包含以下字段：

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

导入命令：

```bash
python main_collect.py --china-official-only
python main_collect.py --merge-only
```
