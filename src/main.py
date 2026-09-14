from pathlib import Path

import pandas as pd

from calculations import add_MTD_spend, add_QTD_spend, add_T7D_spend, calculate_yoy
from normalization import (
    add_diq,
    apply_quarter_names,
    make_total,
    rename_to_schema,
)
from schema import DailySaleSchema

# Adding this since path directory technically at root not src
SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "data"


def main():
    daily_sales_df = pd.read_excel(DATA_DIR / "Daily_Sales.xlsx")               
    daily_sales_df[["company", "segment_name"]] = (
        daily_sales_df["segment_name"].str.split(": ", n=1, expand=True)
    )
    quarter_dates_df = pd.read_excel(DATA_DIR / "Qtr_Dates.xlsx")

    daily_sales_df = apply_quarter_names(daily_sales_df, quarter_dates_df)
    total_df = make_total(daily_sales_df)

    daily_sales_df = pd.concat([daily_sales_df, total_df], ignore_index=True)

    daily_sales_df = add_diq(daily_sales_df)
    print(daily_sales_df)

    daily_sales_df = rename_to_schema(daily_sales_df)

    df = DailySaleSchema.validate(daily_sales_df)
    # print(df)

    df = add_MTD_spend(df)
    df = add_QTD_spend(df)
    df = add_T7D_spend(df)
    df = DailySaleSchema.validate(df)
    df = calculate_yoy(df, ["daily_spend", "mtd_spend", "qtd_spend", "t7d_spend"])
    df = DailySaleSchema.validate(df)
    df.to_excel("forecasting_data.xlsx")
    print(df.tail())


if __name__ == "__main__":
    main()
