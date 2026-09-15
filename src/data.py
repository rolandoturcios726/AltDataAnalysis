"""Loaders shared by every stage: the daily card panel and the reported/consensus KPIs."""

from pathlib import Path

import pandas as pd

from calculations import add_mtd_spend, add_qtd_spend, add_t7d_spend, calculate_yoy
from normalization import (
    add_diq,
    apply_quarter_names,
    make_total,
    normalize_kpi,
    rename_to_schema,
)
from schema import DailySaleSchema, KpiSchema

# Adding this since path directory technically at root not src
SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "data"


def load_daily_data(data_dir=DATA_DIR):
    daily_sales_df = pd.read_excel(data_dir / "Daily_Sales.xlsx")
    daily_sales_df[["company", "segment_name"]] = daily_sales_df[
        "segment_name"
    ].str.split(": ", n=1, expand=True)

    quarter_dates_df = pd.read_excel(data_dir / "Qtr_Dates.xlsx").dropna(how="all")

    daily_sales_df = apply_quarter_names(daily_sales_df, quarter_dates_df)
    total_df = make_total(daily_sales_df)

    daily_sales_df = pd.concat([daily_sales_df, total_df], ignore_index=True)
    daily_sales_df = daily_sales_df.sort_values(["company", "segment_name", "date"])

    daily_sales_df = add_diq(daily_sales_df)

    daily_sales_df = rename_to_schema(daily_sales_df)

    df = DailySaleSchema.validate(daily_sales_df)

    df = add_mtd_spend(df)
    df = add_qtd_spend(df)
    df = add_t7d_spend(df)
    df = DailySaleSchema.validate(df)
    df = calculate_yoy(df, ["daily_spend", "mtd_spend", "qtd_spend", "t7d_spend"])
    return DailySaleSchema.validate(df)


def load_kpi(path):
    """Reported actuals or consensus estimates as segment_name, quarter_name, yoy_val."""
    return KpiSchema.validate(normalize_kpi(pd.read_excel(path)))
