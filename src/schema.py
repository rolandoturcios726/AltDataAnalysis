import datetime
import pandas as pd
import pandera.pandas as pa
from pandera.typing import DataFrame, Series


# I decided to use Pandera for my schema, since I want to apply Pandas transformations


class DailySaleSchema(pa.DataFrameModel):
    segment_name: Series[str]
    # coerce = True converts compatible date formats to the schema
    date: Series[pd.Timestamp] = pa.Field(coerce=True)
    quarter_name: Series[str]
    previous_year_quarter: Series[str] 
    quarter_start_date: Series[pd.Timestamp] = pa.Field(coerce=True)
    diq: Series[int] | None
    daily_spend: Series[float] | None
    mtd_spend: Series[float] | None
    qtd_spend: Series[float] | None
    t7d_spend: Series[float] | None
    # First Year of Data does not have a quarter to compare yoy, needs to allow potential NULL for yoy calculations
    daily_spend_yoy: Series[float] | None = pa.Field(nullable=True)
    mtd_spend_yoy: Series[float] | None = pa.Field(nullable=True)
    qtd_spend_yoy: Series[float] | None = pa.Field(nullable=True)
    t7d_spend_yoy: Series[float] | None = pa.Field(nullable=True)

    # Adding Config so it errors when columns differ from the schema
    class Config(pa.DataFrameModel.Config):
        strict = True
