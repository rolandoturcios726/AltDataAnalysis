import pandas as pd


def apply_quarter_names(daily_sales_df: pd.DataFrame, quarter_dates_df) -> pd.DataFrame:
    # Side Note: tried doing np.where first but didn't realize both df's have to be the same size
    quarters = pd.IntervalIndex.from_arrays(
        quarter_dates_df["begin_date"], quarter_dates_df["end_date"], closed="both"
    )

    # Assigning quarter_names to quarters
    quarter_labels = dict(zip(quarters, quarter_dates_df["quarter_name"]))

    # Assigning quarter_name to daily_sales_df
    daily_sales_df["quarter_name"] = (
        pd.cut(daily_sales_df["date"], bins=quarters)
        .map(quarter_labels)
        .astype("string")
        .fillna("")
    )
    daily_sales_df = daily_sales_df.merge(
        quarter_dates_df[["quarter_name", "begin_date"]],
        how="inner",
        on=["quarter_name"],
    )
    return daily_sales_df


def add_MTD_spend(df: pd.DataFrame) -> pd.DataFrame:
    df["MTD spend"] = df.groupby(
        ["segment_name", df["date"].dt.year, df["date"].dt.month]
    )["Spend (USD)"].cumsum()
    return df


def add_QTD_spend(df: pd.DataFrame) -> pd.DataFrame:
    df["QTD spend"] = df.groupby(["segment_name", df["quarter_name"]])[
        "Spend (USD)"
    ].cumsum()
    return df


def add_T7D_spend(df: pd.DataFrame) -> pd.DataFrame:
    df["T7D spend"] = (
        df.groupby(["segment_name"])["Spend (USD)"]
        .rolling(7, min_periods=1)
        .sum()
        .reset_index(level=0, drop=True)
    )
    return df


def make_total(df: pd.DataFrame) -> pd.DataFrame:

    total = df.groupby("date", as_index=False).agg(
        {
            "Spend (USD)": "sum",
            "MTD spend": "sum",
            "QTD spend": "sum",
            "T7D spend": "sum",
            # first grabs first value from grouping
            "quarter_name": "first",
            "begin_date": "first",
        }
    )
    total["segment_name"] = "Total"
    return total[df.columns]


def add_yoy(df: pd.DataFrame) -> pd.DataFrame:

    df["YoY Change"] = df.groupby(
        [
            "segment_name",
        ]
    ).pct_change()


def last_year_lookup(df: pd.Series) -> pd.Series:
    pass
