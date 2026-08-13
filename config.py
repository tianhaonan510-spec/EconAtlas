from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_RAW = BASE_DIR / "data_raw"
DATA_CLEAN = BASE_DIR / "data_clean"
CACHE_DIR = BASE_DIR / "cache"
LOG_DIR = BASE_DIR / "logs"
METADATA_DIR = BASE_DIR / "metadata"
DB_PATH = DATA_CLEAN / "macrohub.db"

START_YEAR = 2015
END_YEAR = 2025

COUNTRIES = {
    "US": {"iso2": "US", "iso3": "USA", "zh": "美国", "en": "United States"},
    "CN": {"iso2": "CN", "iso3": "CHN", "zh": "中国", "en": "China"},
    "JP": {"iso2": "JP", "iso3": "JPN", "zh": "日本", "en": "Japan"},
    "DE": {"iso2": "DE", "iso3": "DEU", "zh": "德国", "en": "Germany"},
    "GB": {"iso2": "GB", "iso3": "GBR", "zh": "英国", "en": "United Kingdom"},
    "IN": {"iso2": "IN", "iso3": "IND", "zh": "印度", "en": "India"},
    "VN": {"iso2": "VN", "iso3": "VNM", "zh": "越南", "en": "Vietnam"},
    "ID": {"iso2": "ID", "iso3": "IDN", "zh": "印度尼西亚", "en": "Indonesia"},
    "MX": {"iso2": "MX", "iso3": "MEX", "zh": "墨西哥", "en": "Mexico"},
    "BR": {"iso2": "BR", "iso3": "BRA", "zh": "巴西", "en": "Brazil"},
    "ZA": {"iso2": "ZA", "iso3": "ZAF", "zh": "南非", "en": "South Africa"},
    "TR": {"iso2": "TR", "iso3": "TUR", "zh": "土耳其", "en": "Turkiye"},
    "AR": {"iso2": "AR", "iso3": "ARG", "zh": "阿根廷", "en": "Argentina"},
    "SA": {"iso2": "SA", "iso3": "SAU", "zh": "沙特阿拉伯", "en": "Saudi Arabia"},
    "FR": {"iso2": "FR", "iso3": "FRA", "zh": "法国", "en": "France"},
    "IT": {"iso2": "IT", "iso3": "ITA", "zh": "意大利", "en": "Italy"},
    "ES": {"iso2": "ES", "iso3": "ESP", "zh": "西班牙", "en": "Spain"},
    "EA": {"iso2": "EA", "iso3": "EA20", "zh": "欧元区", "en": "Euro area"},
}

IMF_WEO_MAPPING = {
    "NGDP_RPCH": "GDP_REAL_GROWTH_YOY_A",
    "PCPIPCH": "CPI_YOY_A",
    "LUR": "UNEMPLOYMENT_RATE_A",
    "GGXWDG_NGDP": "GOV_DEBT_GDP_A",
    "BCA_NGDPD": "CURRENT_ACCOUNT_GDP_A",
}

FRED_SERIES = {
    "US_CPI_INDEX_M": {
        "fred_series_id": "CPIAUCSL",
        "indicator_name_zh": "美国居民消费价格指数",
        "indicator_name_en": "U.S. Consumer Price Index",
        "unit": "index 1982-1984=100",
        "calculation": "level",
        "seasonal_adjustment": "SA",
    },
    "US_UNEMPLOYMENT_RATE_M": {
        "fred_series_id": "UNRATE",
        "indicator_name_zh": "美国失业率",
        "indicator_name_en": "U.S. Unemployment Rate",
        "unit": "%",
        "calculation": "level",
        "seasonal_adjustment": "SA",
    },
    "US_INDUSTRIAL_PRODUCTION_M": {
        "fred_series_id": "INDPRO",
        "indicator_name_zh": "美国工业生产指数",
        "indicator_name_en": "U.S. Industrial Production Index",
        "unit": "index 2017=100",
        "calculation": "level",
        "seasonal_adjustment": "SA",
    },
    "US_FED_FUNDS_RATE_M": {
        "fred_series_id": "FEDFUNDS",
        "indicator_name_zh": "美国联邦基金有效利率",
        "indicator_name_en": "U.S. Effective Federal Funds Rate",
        "unit": "%",
        "calculation": "level",
        "seasonal_adjustment": "NSA",
    },
}

OECD_SERIES = {
    "CPI_YOY_M": {
        "url": "https://sdmx.oecd.org/public/rest/v1/data/OECD.SDD.TPS,DSD_PRICES@DF_PRICES_ALL/.M.N.CPI.PA._T.N.GY?startPeriod=2015-01&dimensionAtObservation=AllDimensions",
        "indicator_name_zh": "居民消费价格指数同比",
        "indicator_name_en": "Consumer Price Index YoY",
        "unit": "%",
        "frequency": "M",
        "seasonal_adjustment": "NSA",
        "calculation": "YoY",
        "source_series_code": "DF_PRICES_ALL.CPI.GY",
    }
}

EUROSTAT_SERIES = {
    "CPI_YOY_M": {
        "dataset": "prc_hicp_manr",
        "params": {"coicop": "CP00"},
        "geos": ["EA20", "DE", "FR", "IT", "ES"],
        "indicator_name_zh": "调和居民消费价格指数同比",
        "indicator_name_en": "HICP annual rate of change",
        "unit": "%",
        "frequency": "M",
        "seasonal_adjustment": "NSA",
        "calculation": "YoY",
        "source_series_code": "prc_hicp_manr.CP00",
    }
}

ECB_SERIES = {
    "EUR_USD_EXCHANGE_RATE_D": {
        "flow": "EXR",
        "key": "D.USD.EUR.SP00.A",
        "indicator_name_zh": "欧元兑美元参考汇率",
        "indicator_name_en": "Euro foreign exchange reference rate: USD",
        "unit": "USD per EUR",
        "frequency": "D",
        "seasonal_adjustment": "NSA",
        "calculation": "level",
        "source_series_code": "EXR.D.USD.EUR.SP00.A",
    }
}

BIS_SERIES = {
    "EXCHANGE_RATE_USD_D": {
        "countries": ["CN", "US", "JP", "DE", "GB", "IN", "BR", "ZA", "TR", "MX", "EA"],
        "indicator_name_zh": "本币兑美元汇率",
        "indicator_name_en": "Exchange rates against USD",
        "unit": "local currency per USD",
        "frequency": "D",
        "seasonal_adjustment": "NSA",
        "calculation": "level",
        "source_series_code": "WS_XRU.D",
    }
}

CHINA_OFFICIAL_SERIES = {
    "CN_CPI_YOY_M": {
        "indicator_name_zh": "中国居民消费价格指数同比",
        "indicator_name_en": "China CPI YoY",
        "unit": "%",
        "frequency": "M",
        "seasonal_adjustment": "NSA",
        "calculation": "YoY",
        "source_series_code": "NBS.CPI.YOY.M",
        "source_dataset": "National Bureau of Statistics monthly data",
    },
    "CN_PPI_YOY_M": {
        "indicator_name_zh": "中国工业生产者出厂价格指数同比",
        "indicator_name_en": "China PPI YoY",
        "unit": "%",
        "frequency": "M",
        "seasonal_adjustment": "NSA",
        "calculation": "YoY",
        "source_series_code": "NBS.PPI.YOY.M",
        "source_dataset": "National Bureau of Statistics monthly data",
    },
    "CN_INDUSTRIAL_VALUE_ADDED_YOY_M": {
        "indicator_name_zh": "中国规模以上工业增加值同比",
        "indicator_name_en": "China industrial value added YoY",
        "unit": "%",
        "frequency": "M",
        "seasonal_adjustment": "NSA",
        "calculation": "YoY",
        "source_series_code": "NBS.IVA.YOY.M",
        "source_dataset": "National Bureau of Statistics monthly data",
    },
}

INDICATOR_MAP = {
    "GDP_NOMINAL_USD_A": {
        "indicator_name_zh": "名义GDP",
        "indicator_name_en": "Nominal GDP",
        "unit": "current USD",
        "frequency": "A",
        "seasonal_adjustment": "NSA",
        "calculation": "level",
        "sources": [
            {"organization": "World Bank", "dataset": "World Development Indicators", "source_series_code": "NY.GDP.MKTP.CD"},
        ],
    },
    "GDP_REAL_GROWTH_YOY_A": {
        "indicator_name_zh": "实际GDP增速",
        "indicator_name_en": "Real GDP Growth",
        "unit": "%",
        "frequency": "A",
        "seasonal_adjustment": "NSA",
        "calculation": "YoY",
        "sources": [
            {"organization": "World Bank", "dataset": "World Development Indicators", "source_series_code": "NY.GDP.MKTP.KD.ZG"},
            {"organization": "IMF", "dataset": "World Economic Outlook", "source_series_code": "NGDP_RPCH"},
        ],
    },
    "GDP_PER_CAPITA_USD_A": {
        "indicator_name_zh": "人均GDP",
        "indicator_name_en": "GDP per capita",
        "unit": "current USD",
        "frequency": "A",
        "seasonal_adjustment": "NSA",
        "calculation": "level",
        "sources": [
            {"organization": "World Bank", "dataset": "World Development Indicators", "source_series_code": "NY.GDP.PCAP.CD"},
        ],
    },
    "CPI_YOY_A": {
        "indicator_name_zh": "居民消费价格指数同比",
        "indicator_name_en": "Consumer Price Index YoY",
        "unit": "%",
        "frequency": "A",
        "seasonal_adjustment": "NSA",
        "calculation": "YoY",
        "sources": [
            {"organization": "World Bank", "dataset": "World Development Indicators", "source_series_code": "FP.CPI.TOTL.ZG"},
            {"organization": "IMF", "dataset": "World Economic Outlook", "source_series_code": "PCPIPCH"},
        ],
    },
    "UNEMPLOYMENT_RATE_A": {
        "indicator_name_zh": "失业率",
        "indicator_name_en": "Unemployment Rate",
        "unit": "% of labor force",
        "frequency": "A",
        "seasonal_adjustment": "NSA",
        "calculation": "level",
        "sources": [
            {"organization": "World Bank", "dataset": "World Development Indicators", "source_series_code": "SL.UEM.TOTL.ZS"},
            {"organization": "IMF", "dataset": "World Economic Outlook", "source_series_code": "LUR"},
            {"organization": "FRED", "dataset": "Federal Reserve Economic Data (annual average from UNRATE)", "source_series_code": "UNRATE.AAVG"},
        ],
    },
    "EXPORTS_USD_A": {
        "indicator_name_zh": "货物和服务出口",
        "indicator_name_en": "Exports of goods and services",
        "unit": "current USD",
        "frequency": "A",
        "seasonal_adjustment": "NSA",
        "calculation": "level",
        "sources": [
            {"organization": "World Bank", "dataset": "World Development Indicators", "source_series_code": "NE.EXP.GNFS.CD"},
        ],
    },
    "IMPORTS_USD_A": {
        "indicator_name_zh": "货物和服务进口",
        "indicator_name_en": "Imports of goods and services",
        "unit": "current USD",
        "frequency": "A",
        "seasonal_adjustment": "NSA",
        "calculation": "level",
        "sources": [
            {"organization": "World Bank", "dataset": "World Development Indicators", "source_series_code": "NE.IMP.GNFS.CD"},
        ],
    },
    "RESERVES_USD_A": {
        "indicator_name_zh": "外汇储备",
        "indicator_name_en": "Total reserves",
        "unit": "current USD",
        "frequency": "A",
        "seasonal_adjustment": "NSA",
        "calculation": "level",
        "sources": [
            {"organization": "World Bank", "dataset": "World Development Indicators", "source_series_code": "FI.RES.TOTL.CD"},
        ],
    },
    "GOV_DEBT_GDP_A": {
        "indicator_name_zh": "政府债务占GDP比重",
        "indicator_name_en": "Central government debt, total",
        "unit": "% of GDP",
        "frequency": "A",
        "seasonal_adjustment": "NSA",
        "calculation": "level",
        "sources": [
            {"organization": "World Bank", "dataset": "World Development Indicators", "source_series_code": "GC.DOD.TOTL.GD.ZS"},
            {"organization": "IMF", "dataset": "World Economic Outlook", "source_series_code": "GGXWDG_NGDP"},
        ],
    },
    "CURRENT_ACCOUNT_GDP_A": {
        "indicator_name_zh": "经常账户余额占GDP比重",
        "indicator_name_en": "Current account balance",
        "unit": "% of GDP",
        "frequency": "A",
        "seasonal_adjustment": "NSA",
        "calculation": "level",
        "sources": [
            {"organization": "World Bank", "dataset": "World Development Indicators", "source_series_code": "BN.CAB.XOKA.GD.ZS"},
            {"organization": "IMF", "dataset": "World Economic Outlook", "source_series_code": "BCA_NGDPD"},
        ],
    },
    "CPI_YOY_M": {
        "indicator_name_zh": "居民消费价格指数同比",
        "indicator_name_en": "Consumer Price Index YoY",
        "unit": "%",
        "frequency": "M",
        "seasonal_adjustment": "NSA",
        "calculation": "YoY",
        "sources": [
            {"organization": "OECD", "dataset": "Prices: Consumer prices", "source_series_code": "DF_PRICES_ALL.CPI.GY"},
            {"organization": "Eurostat", "dataset": "HICP monthly annual rate of change", "source_series_code": "prc_hicp_manr.CP00"},
            {"organization": "FRED", "dataset": "Federal Reserve Economic Data (derived from CPIAUCSL)", "source_series_code": "CPIAUCSL.YOY"},
            {"organization": "National Bureau of Statistics of China", "dataset": "National Bureau of Statistics monthly data (aligned)", "source_series_code": "NBS.CPI.YOY.M.ALIGNED"},
        ],
    },
    "EUR_USD_EXCHANGE_RATE_D": {
        "indicator_name_zh": "欧元兑美元参考汇率",
        "indicator_name_en": "Euro foreign exchange reference rate: USD",
        "unit": "USD per EUR",
        "frequency": "D",
        "seasonal_adjustment": "NSA",
        "calculation": "level",
        "sources": [
            {"organization": "ECB", "dataset": "Euro foreign exchange reference rates", "source_series_code": "EXR.D.USD.EUR.SP00.A"},
        ],
    },
    "EXCHANGE_RATE_USD_D": {
        "indicator_name_zh": "本币兑美元汇率",
        "indicator_name_en": "Exchange rates against USD",
        "unit": "local currency per USD",
        "frequency": "D",
        "seasonal_adjustment": "NSA",
        "calculation": "level",
        "sources": [
            {"organization": "BIS", "dataset": "Exchange rates", "source_series_code": "WS_XRU.D"},
            {"organization": "ECB", "dataset": "Euro foreign exchange reference rates (inverted)", "source_series_code": "EXR.D.USD.EUR.SP00.A.INV"},
        ],
    },
}


# Expanded macro indicator mappings. These entries keep the project focused on
# multi-source alignment first, then add single-source coverage for broader
# macroeconomic use cases.
IMF_WEO_MAPPING.update({
    "NGDPD": "GDP_NOMINAL_USD_A",
    "NGDPDPC": "GDP_PER_CAPITA_USD_A",
    "NGDP": "GDP_CURRENT_LCU_A",
    "NGDP_R": "GDP_REAL_LCU_A",
    "NGDP_D": "GDP_DEFLATOR_INDEX_A",
    "NGSD_NGDP": "GROSS_SAVINGS_GDP_A",
    "NID_NGDP": "GROSS_CAPITAL_FORMATION_GDP_A",
    "GGR_NGDP": "GOV_REVENUE_GDP_A",
    "GGX_NGDP": "GOV_EXPENSE_GDP_A",
    "GGXCNL_NGDP": "GOV_NET_LENDING_GDP_A",
    "NGAP_NPGDP": "OUTPUT_GAP_GDP_A",
    "LP": "POPULATION_TOTAL_A",
    "BX": "EXPORTS_USD_A",
    "BM": "IMPORTS_USD_A",
})

INDICATOR_MAP["GDP_NOMINAL_USD_A"]["sources"].append(
    {"organization": "IMF", "dataset": "World Economic Outlook", "source_series_code": "NGDPD"}
)
INDICATOR_MAP["GDP_PER_CAPITA_USD_A"]["sources"].append(
    {"organization": "IMF", "dataset": "World Economic Outlook", "source_series_code": "NGDPDPC"}
)
INDICATOR_MAP["EXPORTS_USD_A"]["sources"].append(
    {"organization": "IMF", "dataset": "World Economic Outlook", "source_series_code": "BX"}
)
INDICATOR_MAP["IMPORTS_USD_A"]["sources"].append(
    {"organization": "IMF", "dataset": "World Economic Outlook", "source_series_code": "BM"}
)

EXPANDED_WB_IMF_INDICATORS = {
    "GDP_CURRENT_LCU_A": {
        "indicator_name_zh": "本币计价名义GDP",
        "indicator_name_en": "Nominal GDP in local currency",
        "unit": "current LCU",
        "frequency": "A",
        "seasonal_adjustment": "NSA",
        "calculation": "level",
        "sources": [
            {"organization": "World Bank", "dataset": "World Development Indicators", "source_series_code": "NY.GDP.MKTP.CN"},
            {"organization": "IMF", "dataset": "World Economic Outlook", "source_series_code": "NGDP"},
        ],
    },
    "GDP_REAL_LCU_A": {
        "indicator_name_zh": "本币计价实际GDP",
        "indicator_name_en": "Real GDP in local currency",
        "unit": "constant LCU",
        "frequency": "A",
        "seasonal_adjustment": "NSA",
        "calculation": "level",
        "sources": [
            {"organization": "World Bank", "dataset": "World Development Indicators", "source_series_code": "NY.GDP.MKTP.KN"},
            {"organization": "IMF", "dataset": "World Economic Outlook", "source_series_code": "NGDP_R"},
        ],
    },
    "GDP_DEFLATOR_INDEX_A": {
        "indicator_name_zh": "GDP平减指数",
        "indicator_name_en": "GDP deflator index",
        "unit": "index",
        "frequency": "A",
        "seasonal_adjustment": "NSA",
        "calculation": "level",
        "sources": [
            {"organization": "World Bank", "dataset": "World Development Indicators", "source_series_code": "NY.GDP.DEFL.ZS"},
            {"organization": "IMF", "dataset": "World Economic Outlook", "source_series_code": "NGDP_D"},
        ],
    },
    "GROSS_SAVINGS_GDP_A": {
        "indicator_name_zh": "国民总储蓄占GDP比重",
        "indicator_name_en": "Gross national savings as percent of GDP",
        "unit": "% of GDP",
        "frequency": "A",
        "seasonal_adjustment": "NSA",
        "calculation": "level",
        "sources": [
            {"organization": "World Bank", "dataset": "World Development Indicators", "source_series_code": "NY.GNS.ICTR.ZS"},
            {"organization": "IMF", "dataset": "World Economic Outlook", "source_series_code": "NGSD_NGDP"},
        ],
    },
    "GROSS_CAPITAL_FORMATION_GDP_A": {
        "indicator_name_zh": "资本形成总额占GDP比重",
        "indicator_name_en": "Gross capital formation as percent of GDP",
        "unit": "% of GDP",
        "frequency": "A",
        "seasonal_adjustment": "NSA",
        "calculation": "level",
        "sources": [
            {"organization": "World Bank", "dataset": "World Development Indicators", "source_series_code": "NE.GDI.TOTL.ZS"},
            {"organization": "IMF", "dataset": "World Economic Outlook", "source_series_code": "NID_NGDP"},
        ],
    },
    "GOV_REVENUE_GDP_A": {
        "indicator_name_zh": "政府收入占GDP比重",
        "indicator_name_en": "General government revenue as percent of GDP",
        "unit": "% of GDP",
        "frequency": "A",
        "seasonal_adjustment": "NSA",
        "calculation": "level",
        "sources": [
            {"organization": "World Bank", "dataset": "World Development Indicators", "source_series_code": "GC.REV.XGRT.GD.ZS"},
            {"organization": "IMF", "dataset": "World Economic Outlook", "source_series_code": "GGR_NGDP"},
        ],
    },
    "GOV_EXPENSE_GDP_A": {
        "indicator_name_zh": "政府支出占GDP比重",
        "indicator_name_en": "General government expense as percent of GDP",
        "unit": "% of GDP",
        "frequency": "A",
        "seasonal_adjustment": "NSA",
        "calculation": "level",
        "sources": [
            {"organization": "World Bank", "dataset": "World Development Indicators", "source_series_code": "GC.XPN.TOTL.GD.ZS"},
            {"organization": "IMF", "dataset": "World Economic Outlook", "source_series_code": "GGX_NGDP"},
        ],
    },
    "GOV_NET_LENDING_GDP_A": {
        "indicator_name_zh": "政府净借贷占GDP比重",
        "indicator_name_en": "General government net lending or borrowing as percent of GDP",
        "unit": "% of GDP",
        "frequency": "A",
        "seasonal_adjustment": "NSA",
        "calculation": "level",
        "sources": [
            {"organization": "World Bank", "dataset": "World Development Indicators", "source_series_code": "GC.NLD.TOTL.GD.ZS"},
            {"organization": "IMF", "dataset": "World Economic Outlook", "source_series_code": "GGXCNL_NGDP"},
        ],
    },
    "OUTPUT_GAP_GDP_A": {
        "indicator_name_zh": "产出缺口占潜在GDP比重",
        "indicator_name_en": "Output gap as percent of potential GDP",
        "unit": "% of potential GDP",
        "frequency": "A",
        "seasonal_adjustment": "NSA",
        "calculation": "level",
        "sources": [
            {"organization": "IMF", "dataset": "World Economic Outlook", "source_series_code": "NGAP_NPGDP"},
        ],
    },
}
INDICATOR_MAP.update(EXPANDED_WB_IMF_INDICATORS)

EXPANDED_WB_ONLY_INDICATORS = {
    "POPULATION_TOTAL_A": {"indicator_name_zh": "总人口", "indicator_name_en": "Population, total", "unit": "persons", "frequency": "A", "seasonal_adjustment": "NSA", "calculation": "level", "sources": [{"organization": "World Bank", "dataset": "World Development Indicators", "source_series_code": "SP.POP.TOTL"}, {"organization": "IMF", "dataset": "World Economic Outlook", "source_series_code": "LP"}]},
    "POPULATION_GROWTH_A": {"indicator_name_zh": "人口增长率", "indicator_name_en": "Population growth", "unit": "%", "frequency": "A", "seasonal_adjustment": "NSA", "calculation": "YoY", "sources": [{"organization": "World Bank", "dataset": "World Development Indicators", "source_series_code": "SP.POP.GROW"}]},
    "URBAN_POPULATION_RATE_A": {"indicator_name_zh": "城镇人口比重", "indicator_name_en": "Urban population share", "unit": "% of total population", "frequency": "A", "seasonal_adjustment": "NSA", "calculation": "level", "sources": [{"organization": "World Bank", "dataset": "World Development Indicators", "source_series_code": "SP.URB.TOTL.IN.ZS"}]},
    "GNI_CURRENT_USD_A": {"indicator_name_zh": "国民总收入", "indicator_name_en": "GNI, current US dollars", "unit": "current USD", "frequency": "A", "seasonal_adjustment": "NSA", "calculation": "level", "sources": [{"organization": "World Bank", "dataset": "World Development Indicators", "source_series_code": "NY.GNP.MKTP.CD"}]},
    "GNI_PER_CAPITA_USD_A": {"indicator_name_zh": "人均国民总收入", "indicator_name_en": "GNI per capita", "unit": "current USD", "frequency": "A", "seasonal_adjustment": "NSA", "calculation": "level", "sources": [{"organization": "World Bank", "dataset": "World Development Indicators", "source_series_code": "NY.GNP.PCAP.CD"}]},
    "FDI_NET_INFLOWS_GDP_A": {"indicator_name_zh": "外商直接投资净流入占GDP比重", "indicator_name_en": "FDI net inflows as percent of GDP", "unit": "% of GDP", "frequency": "A", "seasonal_adjustment": "NSA", "calculation": "level", "sources": [{"organization": "World Bank", "dataset": "World Development Indicators", "source_series_code": "BX.KLT.DINV.WD.GD.ZS"}]},
    "TRADE_GDP_A": {"indicator_name_zh": "贸易开放度", "indicator_name_en": "Trade as percent of GDP", "unit": "% of GDP", "frequency": "A", "seasonal_adjustment": "NSA", "calculation": "level", "sources": [{"organization": "World Bank", "dataset": "World Development Indicators", "source_series_code": "NE.TRD.GNFS.ZS"}]},
    "EXPORTS_GROWTH_A": {"indicator_name_zh": "出口实际增速", "indicator_name_en": "Exports real growth", "unit": "%", "frequency": "A", "seasonal_adjustment": "NSA", "calculation": "YoY", "sources": [{"organization": "World Bank", "dataset": "World Development Indicators", "source_series_code": "NE.EXP.GNFS.KD.ZG"}]},
    "IMPORTS_GROWTH_A": {"indicator_name_zh": "进口实际增速", "indicator_name_en": "Imports real growth", "unit": "%", "frequency": "A", "seasonal_adjustment": "NSA", "calculation": "YoY", "sources": [{"organization": "World Bank", "dataset": "World Development Indicators", "source_series_code": "NE.IMP.GNFS.KD.ZG"}]},
    "GDP_DEFLATOR_GROWTH_A": {"indicator_name_zh": "GDP平减指数增速", "indicator_name_en": "Inflation, GDP deflator", "unit": "%", "frequency": "A", "seasonal_adjustment": "NSA", "calculation": "YoY", "sources": [{"organization": "World Bank", "dataset": "World Development Indicators", "source_series_code": "NY.GDP.DEFL.KD.ZG"}]},
    "BROAD_MONEY_GDP_A": {"indicator_name_zh": "广义货币占GDP比重", "indicator_name_en": "Broad money as percent of GDP", "unit": "% of GDP", "frequency": "A", "seasonal_adjustment": "NSA", "calculation": "level", "sources": [{"organization": "World Bank", "dataset": "World Development Indicators", "source_series_code": "FM.LBL.BMNY.GD.ZS"}]},
    "DOMESTIC_CREDIT_PRIVATE_GDP_A": {"indicator_name_zh": "对私营部门国内信贷占GDP比重", "indicator_name_en": "Domestic credit to private sector as percent of GDP", "unit": "% of GDP", "frequency": "A", "seasonal_adjustment": "NSA", "calculation": "level", "sources": [{"organization": "World Bank", "dataset": "World Development Indicators", "source_series_code": "FS.AST.PRVT.GD.ZS"}]},
    "TAX_REVENUE_GDP_A": {"indicator_name_zh": "税收收入占GDP比重", "indicator_name_en": "Tax revenue as percent of GDP", "unit": "% of GDP", "frequency": "A", "seasonal_adjustment": "NSA", "calculation": "level", "sources": [{"organization": "World Bank", "dataset": "World Development Indicators", "source_series_code": "GC.TAX.TOTL.GD.ZS"}]},
    "MILITARY_EXPENDITURE_GDP_A": {"indicator_name_zh": "军费支出占GDP比重", "indicator_name_en": "Military expenditure as percent of GDP", "unit": "% of GDP", "frequency": "A", "seasonal_adjustment": "NSA", "calculation": "level", "sources": [{"organization": "World Bank", "dataset": "World Development Indicators", "source_series_code": "MS.MIL.XPND.GD.ZS"}]},
    "CO2_EMISSIONS_KT_A": {"indicator_name_zh": "二氧化碳排放量", "indicator_name_en": "CO2 emissions", "unit": "kt", "frequency": "A", "seasonal_adjustment": "NSA", "calculation": "level", "sources": [{"organization": "World Bank", "dataset": "World Development Indicators", "source_series_code": "EN.ATM.CO2E.KT"}]},
    "ENERGY_USE_PER_CAPITA_A": {"indicator_name_zh": "人均能源使用量", "indicator_name_en": "Energy use per capita", "unit": "kg of oil equivalent per capita", "frequency": "A", "seasonal_adjustment": "NSA", "calculation": "level", "sources": [{"organization": "World Bank", "dataset": "World Development Indicators", "source_series_code": "EG.USE.PCAP.KG.OE"}]},
    "ELECTRIC_POWER_CONSUMPTION_A": {"indicator_name_zh": "人均电力消费", "indicator_name_en": "Electric power consumption per capita", "unit": "kWh per capita", "frequency": "A", "seasonal_adjustment": "NSA", "calculation": "level", "sources": [{"organization": "World Bank", "dataset": "World Development Indicators", "source_series_code": "EG.USE.ELEC.KH.PC"}]},
    "INTERNET_USERS_RATE_A": {"indicator_name_zh": "互联网使用率", "indicator_name_en": "Individuals using the Internet", "unit": "% of population", "frequency": "A", "seasonal_adjustment": "NSA", "calculation": "level", "sources": [{"organization": "World Bank", "dataset": "World Development Indicators", "source_series_code": "IT.NET.USER.ZS"}]},
    "LIFE_EXPECTANCY_A": {"indicator_name_zh": "预期寿命", "indicator_name_en": "Life expectancy at birth", "unit": "years", "frequency": "A", "seasonal_adjustment": "NSA", "calculation": "level", "sources": [{"organization": "World Bank", "dataset": "World Development Indicators", "source_series_code": "SP.DYN.LE00.IN"}]},
    "SCHOOL_ENROLLMENT_TERTIARY_A": {"indicator_name_zh": "高等教育毛入学率", "indicator_name_en": "School enrollment, tertiary", "unit": "% gross", "frequency": "A", "seasonal_adjustment": "NSA", "calculation": "level", "sources": [{"organization": "World Bank", "dataset": "World Development Indicators", "source_series_code": "SE.TER.ENRR"}]},
}
INDICATOR_MAP.update(EXPANDED_WB_ONLY_INDICATORS)


DROP_EMPTY_EXPANDED_INDICATORS = ["OUTPUT_GAP_GDP_A", "CO2_EMISSIONS_KT_A"]
for _indicator_code in DROP_EMPTY_EXPANDED_INDICATORS:
    INDICATOR_MAP.pop(_indicator_code, None)
IMF_WEO_MAPPING.pop("NGAP_NPGDP", None)
FRED_SERIES.update({
    "US_PPI_INDEX_M": {"fred_series_id": "PPIACO", "indicator_name_zh": "美国生产者价格指数", "indicator_name_en": "U.S. Producer Price Index", "unit": "index 1982=100", "frequency": "M", "calculation": "level", "seasonal_adjustment": "NSA"},
    "US_CORE_CPI_INDEX_M": {"fred_series_id": "CPILFESL", "indicator_name_zh": "美国核心CPI指数", "indicator_name_en": "U.S. Core CPI Index", "unit": "index 1982-1984=100", "frequency": "M", "calculation": "level", "seasonal_adjustment": "SA"},
    "US_RETAIL_SALES_M": {"fred_series_id": "RSAFS", "indicator_name_zh": "美国零售销售额", "indicator_name_en": "U.S. Retail Sales", "unit": "millions of dollars", "frequency": "M", "calculation": "level", "seasonal_adjustment": "SA"},
    "US_HOUSING_STARTS_M": {"fred_series_id": "HOUST", "indicator_name_zh": "美国新屋开工", "indicator_name_en": "U.S. Housing Starts", "unit": "thousands of units", "frequency": "M", "calculation": "level", "seasonal_adjustment": "SA"},
    "US_NONFARM_PAYROLLS_M": {"fred_series_id": "PAYEMS", "indicator_name_zh": "美国非农就业人数", "indicator_name_en": "U.S. Nonfarm Payrolls", "unit": "thousands of persons", "frequency": "M", "calculation": "level", "seasonal_adjustment": "SA"},
    "US_M2_MONEY_STOCK_M": {"fred_series_id": "M2SL", "indicator_name_zh": "美国M2货币存量", "indicator_name_en": "U.S. M2 Money Stock", "unit": "billions of dollars", "frequency": "M", "calculation": "level", "seasonal_adjustment": "SA"},
    "US_10Y_TREASURY_RATE_M": {"fred_series_id": "GS10", "indicator_name_zh": "美国10年期国债收益率", "indicator_name_en": "U.S. 10-Year Treasury Rate", "unit": "%", "frequency": "M", "calculation": "level", "seasonal_adjustment": "NSA"},
    "US_2Y_TREASURY_RATE_M": {"fred_series_id": "GS2", "indicator_name_zh": "美国2年期国债收益率", "indicator_name_en": "U.S. 2-Year Treasury Rate", "unit": "%", "frequency": "M", "calculation": "level", "seasonal_adjustment": "NSA"},
})
for indicator_code, meta in FRED_SERIES.items():
    INDICATOR_MAP[indicator_code] = {
        "indicator_name_zh": meta["indicator_name_zh"],
        "indicator_name_en": meta["indicator_name_en"],
        "unit": meta["unit"],
        "frequency": "M",
        "seasonal_adjustment": meta["seasonal_adjustment"],
        "calculation": meta["calculation"],
        "sources": [
            {
                "organization": "FRED",
                "dataset": "Federal Reserve Economic Data",
                "source_series_code": meta["fred_series_id"],
            }
        ],
    }

for indicator_code, meta in CHINA_OFFICIAL_SERIES.items():
    INDICATOR_MAP[indicator_code] = {
        "indicator_name_zh": meta["indicator_name_zh"],
        "indicator_name_en": meta["indicator_name_en"],
        "unit": meta["unit"],
        "frequency": meta["frequency"],
        "seasonal_adjustment": meta["seasonal_adjustment"],
        "calculation": meta["calculation"],
        "sources": [
            {
                "organization": "National Bureau of Statistics of China",
                "dataset": meta["source_dataset"],
                "source_series_code": meta["source_series_code"],
            }
        ],
    }





# Cross-source aligned indicators generated from already collected official/API series.
def _append_indicator_source(indicator_code: str, source: dict):
    if indicator_code not in INDICATOR_MAP:
        return
    existing = {
        (item.get("organization"), item.get("dataset"), item.get("source_series_code"))
        for item in INDICATOR_MAP[indicator_code].get("sources", [])
    }
    key = (source.get("organization"), source.get("dataset"), source.get("source_series_code"))
    if key not in existing:
        INDICATOR_MAP[indicator_code].setdefault("sources", []).append(source)


_append_indicator_source("CPI_YOY_A", {"organization": "FRED", "dataset": "Federal Reserve Economic Data (annualized from CPIAUCSL.YOY)", "source_series_code": "CPIAUCSL.YOY.AAVG"})
_append_indicator_source("CPI_YOY_A", {"organization": "National Bureau of Statistics of China", "dataset": "National Bureau of Statistics monthly data (annualized)", "source_series_code": "NBS.CPI.YOY.M.ALIGNED.AAVG"})

DIRECT_ALIGNED_INDICATORS = {
    "PPI_YOY_M": {
        "indicator_name_zh": "生产者价格指数同比",
        "indicator_name_en": "Producer Price Index YoY",
        "unit": "%",
        "frequency": "M",
        "seasonal_adjustment": "NSA",
        "calculation": "YoY",
        "sources": [
            {"organization": "FRED", "dataset": "Federal Reserve Economic Data (derived from PPIACO)", "source_series_code": "PPIACO.YOY"},
            {"organization": "National Bureau of Statistics of China", "dataset": "National Bureau of Statistics monthly data (aligned)", "source_series_code": "NBS.PPI.YOY.M.ALIGNED"},
        ],
    },
    "PPI_YOY_A": {
        "indicator_name_zh": "生产者价格指数同比",
        "indicator_name_en": "Producer Price Index YoY",
        "unit": "%",
        "frequency": "A",
        "seasonal_adjustment": "NSA",
        "calculation": "annual_average",
        "sources": [
            {"organization": "FRED", "dataset": "Federal Reserve Economic Data (annualized from PPIACO.YOY)", "source_series_code": "PPIACO.YOY.AAVG"},
            {"organization": "National Bureau of Statistics of China", "dataset": "National Bureau of Statistics monthly data (annualized)", "source_series_code": "NBS.PPI.YOY.M.ALIGNED.AAVG"},
        ],
    },
    "INDUSTRIAL_OUTPUT_YOY_M": {
        "indicator_name_zh": "工业生产同比",
        "indicator_name_en": "Industrial Output YoY",
        "unit": "%",
        "frequency": "M",
        "seasonal_adjustment": "NSA",
        "calculation": "YoY",
        "sources": [
            {"organization": "FRED", "dataset": "Federal Reserve Economic Data (derived from INDPRO)", "source_series_code": "INDPRO.YOY"},
            {"organization": "National Bureau of Statistics of China", "dataset": "National Bureau of Statistics monthly data (aligned)", "source_series_code": "NBS.INDUSTRIAL.VALUE.ADDED.YOY.M.ALIGNED"},
        ],
    },
    "INDUSTRIAL_OUTPUT_YOY_A": {
        "indicator_name_zh": "工业生产同比",
        "indicator_name_en": "Industrial Output YoY",
        "unit": "%",
        "frequency": "A",
        "seasonal_adjustment": "NSA",
        "calculation": "annual_average",
        "sources": [
            {"organization": "FRED", "dataset": "Federal Reserve Economic Data (annualized from INDPRO.YOY)", "source_series_code": "INDPRO.YOY.AAVG"},
            {"organization": "National Bureau of Statistics of China", "dataset": "National Bureau of Statistics monthly data (annualized)", "source_series_code": "NBS.INDUSTRIAL.VALUE.ADDED.YOY.M.ALIGNED.AAVG"},
        ],
    },
    "EXCHANGE_RATE_USD_M": {
        "indicator_name_zh": "本币兑美元汇率",
        "indicator_name_en": "Exchange rates against USD",
        "unit": "local currency per USD",
        "frequency": "M",
        "seasonal_adjustment": "NSA",
        "calculation": "period_average",
        "sources": [
            {"organization": "BIS", "dataset": "Exchange rates (monthly average)", "source_series_code": "WS_XRU.D.MAVG"},
            {"organization": "ECB", "dataset": "Euro foreign exchange reference rates (monthly average, inverted)", "source_series_code": "EXR.D.USD.EUR.SP00.A.INV.MAVG"},
        ],
    },
    "EXCHANGE_RATE_USD_A": {
        "indicator_name_zh": "本币兑美元汇率",
        "indicator_name_en": "Exchange rates against USD",
        "unit": "local currency per USD",
        "frequency": "A",
        "seasonal_adjustment": "NSA",
        "calculation": "period_average",
        "sources": [
            {"organization": "BIS", "dataset": "Exchange rates (annual average)", "source_series_code": "WS_XRU.D.AAVG"},
            {"organization": "ECB", "dataset": "Euro foreign exchange reference rates (annual average, inverted)", "source_series_code": "EXR.D.USD.EUR.SP00.A.INV.AAVG"},
        ],
    },
}
INDICATOR_MAP.update(DIRECT_ALIGNED_INDICATORS)
