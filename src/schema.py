import pandas as pd
import pandera.pandas as pa
from pandera.typing import Series

# I decided to use Pandera for my schema, since I want to apply Pandas transformations


class DailySaleSchema(pa.DataFrameModel):
    company: Series[str]
    segment_name: Series[str]
    # coerce = True converts compatible date formats to the schema
    date: Series[pd.Timestamp] = pa.Field(coerce=True)
    year: Series[int]
    quarter: Series[int] = pa.Field(ge=1, le=4)
    quarter_start_date: Series[pd.Timestamp] = pa.Field(coerce=True)
    quarter_end_date: Series[pd.Timestamp] = pa.Field(coerce=True)
    quarter_name: Series[str] = pa.Field(coerce=True)
    diq: Series[int] | None
    daily_spend: Series[float] | None
    mtd_spend: Series[float] | None
    qtd_spend: Series[float] | None
    # Making assumption that I do not want incomplete windows
    t7d_spend: Series[float] | None = pa.Field(nullable=True)
    # First Year of Data does not have a quarter to compare yoy, needs to allow potential NULL for yoy calculations
    daily_spend_yoy: Series[float] | None = pa.Field(nullable=True)
    mtd_spend_yoy: Series[float] | None = pa.Field(nullable=True)
    qtd_spend_yoy: Series[float] | None = pa.Field(nullable=True)
    t7d_spend_yoy: Series[float] | None = pa.Field(nullable=True)

    # Adding Config so it errors when columns differ from the schema
    class Config(pa.DataFrameModel.Config):
        strict = True


class KpiSchema(pa.DataFrameModel):
    """Reported actuals or consensus estimates: one row per panel segment and fiscal quarter."""

    # Unmapped metric names arrive as None and fail here instead of vanishing in a merge.
    segment_name: Series[str]
    quarter_name: Series[str] = pa.Field(str_matches=r"^\d{4}Q[1-4]$")
    yoy_val: Series[float]

    class Config(pa.DataFrameModel.Config):
        strict = True
