import numpy as np
import pandas as pd
from pathlib import Path
from normalization import (
    apply_quarter_names,
    add_MTD_spend,
    add_QTD_spend,
    add_T7D_spend,
    make_total,
)
from datetime import timedelta

# Adding this since path directory technically at root not src
SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "data"


def main():
    daily_sales_df = pd.read_excel(DATA_DIR / "Daily_Sales.xlsx")
    quarter_dates_df = pd.read_excel(DATA_DIR / "Qtr_Dates.xlsx")
    daily_sales_df = apply_quarter_names(daily_sales_df, quarter_dates_df)
    print(daily_sales_df)
    daily_sales_df = add_MTD_spend(daily_sales_df)
    daily_sales_df = add_QTD_spend(daily_sales_df)
    daily_sales_df = add_T7D_spend(daily_sales_df)

    total_df = make_total(daily_sales_df)
    daily_sales_df = pd.concat([daily_sales_df, total_df], ignore_index=True)

    daily_sales_df["DIQ"] = (
        daily_sales_df["date"] - daily_sales_df["begin_date"]
    ) + timedelta(days=1)
    print(len(daily_sales_df))
    # There has to be a better way ... COME BACK TO THIS
    lookup_df = daily_sales_df.assign(
        **{
            "previous_year_quarter": (
                (
                    daily_sales_df["quarter_name"].str.extract(r"(\d{4})").astype(int)
                    - 1
                ).astype(str)
                + daily_sales_df["quarter_name"].str.extract(r"(.{2}$)")
            )
        }
    )
    yoy_df = lookup_df.merge(
        daily_sales_df[
            [
                "segment_name",
                "quarter_name",
                "DIQ",
                "MTD spend",
                "QTD spend",
                "T7D spend",
                "Spend (USD)",
            ]
        ],
        left_on=["segment_name", "previous_year_quarter", "DIQ"],
        right_on=["segment_name", "quarter_name", "DIQ"],
        how="left",
        suffixes=("", "_ly"),
        validate="many_to_one",
    )

    yoy_df["daily_spend_yoy"] = yoy_df["Spend (USD)"] / yoy_df["Spend (USD)_ly"] -1
    yoy_df["mtd_spend_yoy"] = yoy_df["MTD spend"] / yoy_df["MTD spend_ly"] -1
    yoy_df["qtd_spend_yoy"] = yoy_df["QTD spend"] / yoy_df["QTD spend_ly"] -1
    yoy_df["t7d_spend_yoy"] = yoy_df["T7D spend"] / yoy_df["T7D spend_ly"] -1
    print(yoy_df)
if __name__ == "__main__":
    main()
