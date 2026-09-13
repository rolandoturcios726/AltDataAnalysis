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


def make_total(df: pd.DataFrame) -> pd.DataFrame:

    total = df.groupby("date", as_index=False).agg(
        {
            "Spend (USD)": "sum",
            # first grabs first value from grouping
            "quarter_name": "first",
            "begin_date": "first",
        }
    )
    total["segment_name"] = "Total"
    return total[df.columns]


def add_diq(df: pd.DataFrame) -> pd.DataFrame:
    df["diq"] = (df["date"] - df["begin_date"]).dt.days + 1
    return df


def add_previous_quarter_year(df: pd.DataFrame) -> pd.DataFrame:
    # There has to be a better way ... COME BACK TO THIS
    lookup_df = df.assign(
        previous_year_quarter=(
                (df["quarter_name"].str.extract(r"(\d{4})").astype(int) - 1).astype(str)
                + df["quarter_name"].str.extract(r"(.{2}$)")
            )
    )
    yoy_df = lookup_df.merge(
        df[
            [
                "segment_name",
                "quarter_name",
                "diq",
            ]
        ],
        left_on=["segment_name", "previous_year_quarter", "diq"],
        right_on=["segment_name", "quarter_name", "diq"],
        how="left",
        suffixes=("", "_ly"),
        validate="many_to_one",
    )
    yoy_df = yoy_df.drop(columns="quarter_name_ly")
    return yoy_df


def rename_to_schema(df: pd.DataFrame) -> pd.DataFrame:
    df = df.rename(
        columns={"Spend (USD)": "daily_spend", "begin_date": "quarter_start_date"}
    )
    return df
