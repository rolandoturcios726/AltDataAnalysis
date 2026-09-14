# Followed this youtube video https://www.youtube.com/watch?v=baqxBO4PhI8
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error
from normalization import normalize_quarters
def backtest(train_df, model, predictors, start=750, step=1):
    all_predictions = []

    for _, group in train_df.groupby(["company", "segment_name"]):
        group = group.sort_values("date").dropna(
            subset=[*predictors, "target"]
        )

        for i in range(start, len(group), step):
            train = group.iloc[:i]
            test = group.iloc[i:i + step]

            model.fit(train[predictors], train["target"])
            preds = model.predict(test[predictors])

            combined = test[
                ["company", "segment_name", "date", "target"]
            ].rename(columns={"target": "actual"})
            combined["prediction"] = preds
            combined["diff"] = (
                combined["prediction"] - combined["actual"]
            ).abs()

            all_predictions.append(combined)

    return pd.concat(all_predictions, ignore_index=True)
df = pd.read_excel("forecasting_data.xlsx")

null_pct = df.apply(pd.isnull).sum()/df.shape[0]
valid_columns = df.columns[null_pct < .20]

df = df[valid_columns].copy()

df = df.sort_values(["company", "segment_name", "date"])
df["target"] = df.groupby(["company", "segment_name"])["daily_spend"].shift(-1)
train_df = df.dropna(subset=["target"])

rr = Ridge(alpha=.1)

predictors = ["daily_spend", "mtd_spend", "qtd_spend", "t7d_spend"]
print(predictors)

predictions = backtest(train_df, rr, predictors)
print(
    predictions.groupby(["company", "segment_name"])["diff"].mean()
)

keys = ["company", "segment_name"]
quarter_keys = [*keys, "year", "quarter"]
#######################################################################################
# Everthing below was fully AI generated - making a note about this in write up
# Each prediction is for the following day; use that day's fiscal quarter.
predicted_days = predictions.assign(date=predictions["date"] + pd.Timedelta(days=1))
daily = df.merge(
    predicted_days[[*keys, "date", "prediction"]],
    on=[*keys, "date"], how="left", validate="one_to_one",
)
prior_year = df[[*quarter_keys, "diq", "daily_spend"]].rename(columns={
    "daily_spend": "prior_year_spend",
})
# Shift historical keys forward so each year receives the prior year's spend.
prior_year["year"] += 1
daily = daily.merge(
    prior_year, on=[*quarter_keys, "diq"],
    how="left", validate="many_to_one",
)
calendar = pd.read_excel("src/data/Qtr_Dates.xlsx").rename(columns={"symbol": "company"})
calendar = normalize_quarters(calendar)
daily = daily.merge(
    calendar[["company", "year", "quarter", "end_date"]],
    on=["company", "year", "quarter"], how="left", validate="many_to_one",
)

# Use completed quarters and matching DIQs, excluding the unmatched leap-year tail.
complete = daily.groupby(quarter_keys)["date"].transform("max").eq(daily["end_date"])
daily = daily.loc[complete & daily["prior_year_spend"].notna()]
quarterly = daily.groupby(quarter_keys, as_index=False).agg(
    predicted_spend=("prediction", "sum"),
    actual_spend=("daily_spend", "sum"),
    prior_year_spend=("prior_year_spend", "sum"),
    days=("diq", "size"),
    predicted_days=("prediction", "count"),
)
quarterly = quarterly.loc[quarterly["predicted_days"].eq(quarterly["days"])].copy()
quarterly["predicted_panel_yoy"] = quarterly["predicted_spend"] / quarterly["prior_year_spend"] - 1
quarterly["va_metric_name"] = quarterly["segment_name"].str.strip().map({
    "ANTHROPOLOGIE GROUP (US)": "Comps store sales growth - Anthropologie",
    "FREE PEOPLE (US)": "Comps store sales growth - Free people",
    "URBAN OUTFITTERS (US)": "Comps store sales growth - Urban outfitters",
    "Total": "Comps store sales growth",
})
actuals = pd.read_excel("src/data/kpi_actuals.xlsx").rename(columns={
    "symbol": "company", "qtr_name": "quarter_name",
})
actuals = normalize_quarters(actuals)
comparison = quarterly.merge(
    actuals, on=["company", "year", "quarter", "va_metric_name"],
    how="left", validate="one_to_one",
)
comparison["gap_pp"] = 100 * (comparison["predicted_panel_yoy"] - comparison["yoy_val"])
print("\nRolling next-day panel forecasts versus reported quarterly comps:")
print(comparison.assign(
    quarter_name=comparison["year"].astype(str) + "Q" + comparison["quarter"].astype(str)
)[
    [*keys, "quarter_name", "predicted_panel_yoy", "yoy_val", "gap_pp"]
].round(4).to_string(index=False))

# Fit on observed targets, then feed each future prediction into the next day's features.
forecast_year, forecast_quarter = 2027, 3
quarter_ends = calendar.loc[
    calendar["year"].eq(forecast_year) & calendar["quarter"].eq(forecast_quarter)
].set_index("company")["end_date"]
future_rows = []
for (company, segment), group in df.groupby(keys):
    train = group.dropna(subset=[*predictors, "target"])
    rr.fit(train[predictors], train["target"])
    features = group[predictors].tail(1).copy()
    recent_spend = group["daily_spend"].tail(7).tolist()

    for date in pd.date_range(group["date"].max() + pd.Timedelta(days=1), quarter_ends[company]):
        spend = float(rr.predict(features)[0])
        future_rows.append((company, segment, date, spend))
        recent_spend.append(spend)
        features.loc[:, "daily_spend"] = spend
        features.loc[:, "mtd_spend"] = spend if date.day == 1 else features["mtd_spend"] + spend
        features.loc[:, "qtd_spend"] = features["qtd_spend"] + spend
        features.loc[:, "t7d_spend"] = sum(recent_spend[-7:])

future_predictions = pd.DataFrame(future_rows, columns=[*keys, "date", "prediction"])
forward = future_predictions.groupby(keys)["prediction"].sum().to_frame("remaining_spend")
forward["observed_qtd_spend"] = df.loc[
    df["year"].eq(forecast_year) & df["quarter"].eq(forecast_quarter)
].groupby(keys)["daily_spend"].sum()
forward["prior_year_spend"] = df.loc[
    df["year"].eq(forecast_year - 1) & df["quarter"].eq(forecast_quarter)
].groupby(keys)["daily_spend"].sum()
forward["forecast_quarter_spend"] = forward["observed_qtd_spend"] + forward["remaining_spend"]
forward["predicted_panel_yoy"] = forward["forecast_quarter_spend"] / forward["prior_year_spend"] - 1

# Translate panel growth to reported comps using the last four observed quarterly gaps.
recent = comparison.dropna(subset=["yoy_val"]).sort_values(["year", "quarter"]).groupby(keys).tail(4).copy()
recent["panel_comp_gap"] = recent["yoy_val"] - (recent["actual_spend"] / recent["prior_year_spend"] - 1)
forward = forward.join(recent.groupby(keys)["panel_comp_gap"].mean()).reset_index()
forward["comp_forecast"] = forward["predicted_panel_yoy"] + forward["panel_comp_gap"]
forward["year"] = forecast_year
forward["quarter"] = forecast_quarter
forward = forward.merge(comparison[[*keys, "va_metric_name"]].drop_duplicates(), on=keys, validate="one_to_one")
consensus = pd.read_excel("src/data/kpi_ests.xlsx").rename(columns={
    "symbol": "company", "qtr_name": "quarter_name", "yoy_val": "consensus",
})
consensus = normalize_quarters(consensus)
forward = forward.merge(
    consensus, on=["company", "year", "quarter", "va_metric_name"],
    how="left", validate="one_to_one",
)
forward["vs_consensus_pp"] = 100 * (forward["comp_forecast"] - forward["consensus"])
print(f"\n{forecast_year}Q{forecast_quarter} recursive forecast using observed spend through {df['date'].max():%Y-%m-%d}:")
print(forward.assign(
    quarter_name=forward["year"].astype(str) + "Q" + forward["quarter"].astype(str)
)[
    [*keys, "quarter_name", "predicted_panel_yoy", "comp_forecast", "consensus", "vs_consensus_pp"]
].round(4).to_string(index=False))
print("Comp forecast adds the recent panel-to-comps gap; the 62-day recursive horizon has not been backtested.")
