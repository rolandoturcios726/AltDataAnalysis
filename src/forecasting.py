"""Nowcast URBN reported comp-sales growth from the daily card panel.

For each KPI, quarter q and day-in-quarter d:

    forecast = comp[ref] + slope_d * (panel_yoy[q, d] - panel_yoy[ref, d])

where ref is the latest quarter whose reported comp was available on the forecast
date, and slope_d is fitted only on earlier quarters that were available that day.
"""

from pathlib import Path

import pandas as pd
from sklearn.linear_model import LinearRegression

from data import DATA_DIR, load_daily_data, load_kpi

KEY = ["segment_name", "quarter_name"]
LAG = pd.Timedelta(days=20)  # assumption: comps usable 20 days after quarter end
MIN_TRAIN = 4  # (panel change, comp change) pairs needed before a slope is fitted
# Scored alongside the model: repeat the reference comp, and the raw panel QTD YoY.
METHODS = {"forecast": "model", "ref_actual": "naive", "panel_yoy": "raw_panel"}
INPUTS = [
    *KEY,
    "date",
    "diq",
    "ref_quarter",
    "ref_actual",
    "panel_yoy",
    "ref_panel_yoy",
]
OUTPUTS = ["panel_change", "coef", "n_train", "forecast", "actual", "error_pp"]


def load_inputs(daily, data_dir=DATA_DIR):
    """Daily panel rows with their reported comp, reference quarter and model inputs."""
    # Days without a prior-year match (first panel year, leap-year tail) are excluded.
    daily = daily.dropna(subset=["qtd_spend_yoy"])
    daily = daily.sort_values("date").rename(columns={"qtd_spend_yoy": "panel_yoy"})
    daily["available_date"] = daily["quarter_end_date"] + LAG
    actuals = load_kpi(data_dir / "kpi_actuals.xlsx").rename(
        columns={"yoy_val": "actual"}
    )
    panel = daily.merge(actuals, on=KEY, how="left")

    # Reference quarter: the latest reported comp available on each panel date.
    refs = (
        daily[[*KEY, "available_date"]]
        .drop_duplicates()
        .merge(actuals, on=KEY)
        .rename(
            columns={
                "quarter_name": "ref_quarter",
                "actual": "ref_actual",
                "available_date": "date",
            }
        )
        .sort_values("date")
    )
    panel = pd.merge_asof(panel, refs, on="date", by="segment_name")

    # The reference quarter's panel YoY at the same DIQ: a like-for-like comparison.
    ref_yoy = daily[[*KEY, "diq", "panel_yoy"]].rename(
        columns={"quarter_name": "ref_quarter", "panel_yoy": "ref_panel_yoy"}
    )
    panel = panel.merge(ref_yoy, on=["segment_name", "ref_quarter", "diq"], how="left")
    panel["panel_change"] = panel["panel_yoy"] - panel["ref_panel_yoy"]
    panel["comp_change"] = panel["actual"] - panel["ref_actual"]
    consensus = load_kpi(data_dir / "kpi_ests.xlsx").rename(
        columns={"yoy_val": "consensus"}
    )
    print(panel)
    print(consensus)
    return panel, consensus


def fit_slope(train):
    """Slope through the origin: a zero panel change repeats the reference comp."""
    model = LinearRegression(fit_intercept=False)
    return model.fit(train[["panel_change"]], train["comp_change"]).coef_[0]


def forecast(panel, max_diq):
    """Forecast every quarter at DIQ 1..max_diq using only comps available that day."""
    rows = []
    for _, day in panel[panel["diq"].le(max_diq)].groupby(["segment_name", "diq"]):
        history = day.dropna(subset=["panel_change", "comp_change"])
        for _, row in day.sort_values("quarter_name").iterrows():
            # Lookahead guard: only quarters whose comp was public on the forecast date.
            train = history[history["available_date"].le(row["date"])]
            if len(train) >= MIN_TRAIN:
                row["n_train"] = len(train)
                row["coef"] = fit_slope(train)
            rows.append(row)
    out = pd.DataFrame(rows)
    out["forecast"] = out["ref_actual"] + out["coef"] * out["panel_change"]
    return out


def score(backtest):
    """MAE, RMSE and bias (pp) by KPI, DIQ and method, scored on identical quarters."""
    scored = backtest.dropna(subset=["actual", "forecast"])
    errors = scored.melt(
        id_vars=["segment_name", "diq", "actual"],
        value_vars=list(METHODS),
        var_name="method",
    )
    errors["method"] = errors["method"].map(METHODS)
    errors["error_pp"] = 100 * (errors["value"] - errors["actual"])
    grouped = errors.groupby(["segment_name", "diq", "method"])["error_pp"]
    stats = grouped.agg(
        n="size",
        mae_pp=lambda e: e.abs().mean(),
        rmse_pp=lambda e: (e**2).mean() ** 0.5,
        bias_pp="mean",
    )
    return stats.reset_index()


def run(panel, consensus, as_of=None):
    """Forecast every quarter as of one panel date; returns the output sheets as frames."""
    cutoff = panel["date"].max() if as_of is None else pd.Timestamp(as_of)
    current = panel.loc[panel["date"].eq(cutoff)]
    if len(current) != panel["segment_name"].nunique():
        raise ValueError(f"No complete panel day at {cutoff:%Y-%m-%d}.")
    max_diq = current["diq"].iloc[0]  # every series shares the fiscal calendar

    backtest = forecast(panel, max_diq)
    # Only show actuals that were public on the as-of date.
    backtest["actual"] = backtest["actual"].where(backtest["available_date"].le(cutoff))
    backtest["error_pp"] = 100 * (backtest["forecast"] - backtest["actual"])
    latest = backtest[backtest["date"].eq(cutoff)].merge(consensus, on=KEY, how="left")
    latest["vs_consensus_pp"] = 100 * (latest["forecast"] - latest["consensus"])

    columns = [*INPUTS, *OUTPUTS]
    return {
        "Forecast": latest[[*columns, "consensus", "vs_consensus_pp"]],
        "Backtest": backtest[columns],
        "Errors by day": score(backtest),
    }


def write_sheets(sheets, path):
    path.parent.mkdir(exist_ok=True)
    with pd.ExcelWriter(path) as writer:
        for name, frame in sheets.items():
            frame.to_excel(writer, sheet_name=name, index=False, freeze_panes=(1, 0))


def main():
    as_of = None  # None = latest panel date, or e.g. "2026-08-15" for day 15 of 2027Q3
    output = Path("outputs/kpi_forecasts.xlsx")

    panel, consensus = load_inputs(load_daily_data(DATA_DIR), DATA_DIR)
    sheets = run(panel, consensus, as_of)
    write_sheets(sheets, output)
    print(sheets["Forecast"].to_string(index=False))


if __name__ == "__main__":
    main()
