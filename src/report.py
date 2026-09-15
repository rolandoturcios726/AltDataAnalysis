"""Charts for the forecasts written by forecasting.py, and the PM workbook built on them."""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import PercentFormatter

from data import DATA_DIR, load_daily_data
from workbook import COLORS, TITLES, build

# Series on each chart: column -> (legend label, color, line style). One color per entity.
COMPS = {
    "actual": ("Reported comp", COLORS["reported"], "o-"),
    "forecast": ("Model forecast", COLORS["model"], "o-"),
    "ref_actual": ("Naive: repeat last reported comp", COLORS["naive"], "-"),
}
ERRORS = {
    "model": ("Model", COLORS["model"]),
    "naive": ("Naive: repeat last reported comp", COLORS["naive"]),
    "raw_panel": ("Raw panel QTD YoY", COLORS["raw_panel"]),
}
# Daily is a visible slate and plotted every few days; T7D/QTD stay a blue ramp.
WINDOWS = {
    "daily_spend_yoy": ("Daily", "#334155", 1.0),
    "t7d_spend_yoy": ("Trailing 7 days", "#5598e7", 1.6),
    "qtd_spend_yoy": ("Quarter to date", COLORS["header"], 2.2),
}
DAILY_STEP = 5
GRAY = "#c3c2b7"

plt.switch_backend("Agg")
plt.rcParams.update(
    {
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.edgecolor": GRAY,
        "axes.grid": True,
        "grid.color": "#e6e5e1",
        "axes.titleweight": "bold",
        "font.size": 9,
        "legend.frameon": False,
    }
)


def grid(title):
    """A 2x2 figure with one panel per KPI, keyed by segment name."""
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), constrained_layout=True)
    fig.suptitle(title, fontsize=13, fontweight="bold")
    return fig, dict(zip(TITLES, axes.ravel(), strict=True))


def finish(fig, axes, path):
    """Panel titles, a zero line, one shared legend under the panels, then save."""
    for seg, ax in axes.items():
        ax.set_title(TITLES[seg])
        ax.axhline(0, color=GRAY, linewidth=1)
    handles, labels = axes["Total"].get_legend_handles_labels()
    fig.legend(handles, labels, loc="outside lower center", ncol=len(labels))
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def forecast_vs_actual(backtest, latest, out_dir):
    """PM view: has the model tracked reported comps, and where is it versus the Street?"""
    diq = latest["diq"].iloc[0]
    fig, axes = grid(
        f"Reported comp growth vs model forecast made on day {diq} of each quarter"
    )
    rows = backtest[backtest["diq"].eq(diq)].dropna(subset=["forecast"])
    for seg, ax in axes.items():
        s = rows[rows["segment_name"].eq(seg)].reset_index(drop=True)
        for column, (label, color, style) in COMPS.items():
            ax.plot(s.index, s[column], style, color=color, ms=5, lw=2, label=label)
        est = latest[latest["segment_name"].eq(seg)]
        ax.plot(
            [len(s) - 1],
            est["consensus"],
            "D",
            color=COLORS["consensus"],
            ms=7,
            label="Consensus (in-progress quarter)",
        )
        ax.set_xticks(s.index, s["quarter_name"], rotation=45, ha="right")
        ax.yaxis.set_major_formatter(PercentFormatter(1.0, decimals=0))
    return finish(fig, axes, out_dir / "forecast_vs_actual.png")


def error_by_day(errors, out_dir):
    """Analyst view: how early in the quarter is the read trustworthy?"""
    fig, axes = grid(
        "MAE of full-quarter comp forecasts by day of quarter (y-axis capped at 3x the naive baseline)"
    )
    for seg, ax in axes.items():
        mae = errors[errors["segment_name"].eq(seg)].pivot_table(
            index="diq", columns="method", values="mae_pp"
        )
        for method, (label, color) in ERRORS.items():
            ax.plot(mae.index, mae[method], color=color, lw=2, label=label)
        ax.set_ylim(0, 3 * mae["naive"].max())
        ax.set(xlabel="Day in quarter", ylabel="MAE, percentage points")
    return finish(fig, axes, out_dir / "error_by_day.png")


def rmse_by_day(errors, out_dir):
    fig, axes = grid(
        "RMSE of full-quarter comp forecasts by day of quarter (y-axis capped at 3x the naive baseline)"
    )
    for seg, ax in axes.items():
        rmse = errors[errors["segment_name"].eq(seg)].pivot_table(
            index="diq", columns="method", values="rmse_pp"
        )
        for method, (label, color) in ERRORS.items():
            ax.plot(rmse.index, rmse[method], color=color, lw=2, label=label)
        ax.set_ylim(0, 3 * rmse["naive"].max())
        ax.set(xlabel="Day in quarter", ylabel="RMSE, percentage points")
    return finish(fig, axes, out_dir / "rmse_by_day.png")


def bias_by_day(errors, out_dir):
    fig, axes = grid("Bias of full-quarter comp forecasts by day of quarter (forecast minus actual)")
    for seg, ax in axes.items():
        bias = errors[errors["segment_name"].eq(seg)].pivot_table(
            index="diq", columns="method", values="bias_pp"
        )
        for method, (label, color) in ERRORS.items():
            ax.plot(bias.index, bias[method], color=color, lw=2, label=label)
        limit = 3 * bias["naive"].abs().max()
        ax.set_ylim(-limit, limit)
        ax.set(xlabel="Day in quarter", ylabel="Bias, percentage points")
    return finish(fig, axes, out_dir / "bias_by_day.png")


def yoy_trends(daily, out_dir, months=13):
    """Analyst/PM view: what is the panel saying about momentum right now?"""
    recent = daily[daily["date"].ge(daily["date"].max() - pd.DateOffset(months=months))]
    fig, axes = grid(
        "Panel spend growth YoY, DIQ-aligned: daily, trailing 7 days and quarter to date"
    )
    for seg, ax in axes.items():
        s = recent[recent["segment_name"].eq(seg)].sort_values("date")
        for column, (label, color, width) in WINDOWS.items():
            plotted = s[["date", column]].dropna()
            if column == "daily_spend_yoy":
                plotted = plotted.iloc[::DAILY_STEP]
            ax.plot(plotted["date"], plotted[column], color=color, lw=width, label=label)
        limit = 1.25 * s["t7d_spend_yoy"].abs().max()
        starts = s[s["diq"].eq(1)]
        for date, quarter in zip(starts["date"], starts["quarter_name"], strict=True):
            ax.axvline(date, color=GRAY, lw=1)
            ax.text(date, limit * 0.92, f" {quarter}", color="#52514e", fontsize=7)
        ax.set_ylim(-limit, limit)
        ax.yaxis.set_major_formatter(PercentFormatter(1.0, decimals=0))
    return finish(fig, axes, out_dir / "yoy_trends.png")


def run(sheets, daily, out_dir):
    """Write the charts and the PM workbook for one set of forecast sheets."""
    pm_workbook = out_dir / "urbn_kpi_nowcast.xlsx"
    out_dir.mkdir(exist_ok=True)
    charts = [
        forecast_vs_actual(sheets["Backtest"], sheets["Forecast"], out_dir),
        error_by_day(sheets["Errors by day"], out_dir),
        yoy_trends(daily, out_dir),
    ]
    rmse_by_day(sheets["Errors by day"], out_dir)
    bias_by_day(sheets["Errors by day"], out_dir)
    build(sheets, daily, {chart.stem: chart for chart in charts}, pm_workbook)
    return pm_workbook


def main():
    out_dir = Path("outputs")
    forecasts = out_dir / "kpi_forecasts.xlsx"  # written by forecasting.py

    sheets = pd.read_excel(forecasts, sheet_name=None)
    pm_workbook = run(sheets, load_daily_data(DATA_DIR), out_dir)
    print(f"Wrote {pm_workbook} and {out_dir}/*.png")


if __name__ == "__main__":
    main()
