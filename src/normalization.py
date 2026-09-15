import pandas as pd

# Reported KPI metric names and the panel segment each one measures.
SEGMENTS = {
    "Comps store sales growth - Anthropologie": "ANTHROPOLOGIE GROUP (US)",
    "Comps store sales growth - Free people": "FREE PEOPLE (US)",
    "Comps store sales growth - Urban outfitters": "URBAN OUTFITTERS (US)",
    "Comps store sales growth": "Total",
}


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
    return daily_sales_df.merge(
        quarter_dates_df[["quarter_name", "begin_date", "end_date"]],
        how="inner",
        on=["quarter_name"],
    )


def make_total(df: pd.DataFrame) -> pd.DataFrame:

    total = df.groupby("date", as_index=False).agg(
        {
            "Spend (USD)": "sum",
            # first grabs first value from grouping
            "company": "first",
            "quarter_name": "first",
            "begin_date": "first",
            "end_date": "first",
        }
    )
    total["segment_name"] = "Total"
    return total[df.columns]


def add_diq(df: pd.DataFrame) -> pd.DataFrame:
    df["diq"] = (df["date"] - df["begin_date"]).dt.days + 1
    return df


def normalize_quarters(df: pd.DataFrame) -> pd.DataFrame:
    df[["year", "quarter"]] = (
        df["quarter_name"].str.extract(r"^(\d{4})Q([1-4])$").astype(int)
    )
    return df


def rename_to_schema(df: pd.DataFrame) -> pd.DataFrame:
    df = df.rename(
        columns={
            "Spend (USD)": "daily_spend",
            "begin_date": "quarter_start_date",
            "end_date": "quarter_end_date",
        }
    )
    return normalize_quarters(df)


def normalize_kpi(df: pd.DataFrame) -> pd.DataFrame:
    """Map a KPI workbook (actuals or estimates) onto panel segment and quarter names."""
    df = df.rename(columns={"qtr_name": "quarter_name"})
    df["segment_name"] = df["va_metric_name"].map(SEGMENTS.get)
    return df[["segment_name", "quarter_name", "yoy_val"]]
