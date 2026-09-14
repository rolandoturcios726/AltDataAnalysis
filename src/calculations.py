import pandas as pd
from pandera.typing import DataFrame

from schema import DailySaleSchema


def add_MTD_spend(df: DataFrame[DailySaleSchema]) -> DataFrame[DailySaleSchema]:
    df["mtd_spend"] = df.groupby(
        ["segment_name", df["date"].dt.year, df["date"].dt.month]
    )["daily_spend"].cumsum()
    return df


def add_QTD_spend(df: DataFrame[DailySaleSchema]) -> DataFrame[DailySaleSchema]:
    df["qtd_spend"] = df.groupby(["segment_name", "year", "quarter"])[
        "daily_spend"
    ].cumsum()
    return df


def add_T7D_spend(df: DataFrame[DailySaleSchema]) -> DataFrame[DailySaleSchema]:
    df["t7d_spend"] = (
        df.groupby(["segment_name"])["daily_spend"]
        .rolling(7, min_periods=7)
        .sum()
        .reset_index(level=0, drop=True)
    )
    return df


def _get_previous_df(df: DataFrame[DailySaleSchema]) -> DataFrame[DailySaleSchema]:
    history = df.set_index(
        ["segment_name", "year", "quarter", "diq"],
        verify_integrity=True,
    )

    requested_keys = pd.MultiIndex.from_arrays(
        [df["segment_name"], df["year"] - 1, df["quarter"], df["diq"]],
        names=history.index.names,
    )

    previous = history.reindex(requested_keys)
    previous.index = df.index
    return previous


def calculate_yoy(
    df: DataFrame[DailySaleSchema], fields: list[str]
) -> DataFrame[DailySaleSchema]:
    previous = _get_previous_df(df)
    changes = (df[fields] / previous[fields] - 1).add_suffix("_yoy")
    df[changes.columns] = changes
    return df
