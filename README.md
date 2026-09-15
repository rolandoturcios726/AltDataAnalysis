# URBN alternative-data KPI forecasting

Forecast quarterly reported comparable-sales growth ("comps") for Anthropologie,
Free People, Urban Outfitters and URBN in total from a daily credit-card spend panel.
The forecast works at any observed day of the fiscal quarter, is backtested against
reported actuals with no lookahead, and is compared with consensus for the
in-progress quarter (fiscal 2027Q3, August 1 to October 31, 2026; the panel ends
August 30, 2026, day 30 of the quarter).

- **[PM_WRITEUP.docx](PM_WRITEUP.docx)**: findings for an investment-literate reader. What the panel says about each segment, where we sit versus consensus, how much to trust it.
- **[TECHNICAL_WRITEUP.docx](TECHNICAL_WRITEUP.docx)**: pipeline design, methodology and the paths that did not work, assumptions and limitations, next steps, AI usage.

## Run

Requires Python 3.13+ and `uv`. From the repository root:

```powershell
uv sync
uv run python src/main.py   # everything: outputs/forecasting_data.xlsx, kpi_forecasts.xlsx, urbn_kpi_nowcast.xlsx, *.png
```


Run settings are plain variables at the top of `main()` in each script. In
`src/forecasting.py`, `as_of` is `None` for the latest panel date; set it to
`"2026-08-15"` to reproduce the day-15 view, or to a quarter-end date such as
`"2026-07-31"` to evaluate completed quarters at every day 1 to 92. `output`
names the workbook. In `src/report.py`, the two workbook paths and the output
directory are set the same way. No output file may be open in Excel while the
pipeline runs.

## Outputs

All generated files land in `outputs/`.

| Output | For | Question it answers |
|---|---|---|
| `urbn_kpi_nowcast.xlsx` | PM | The one file to hand over. **Summary**: where the model sits for the in-progress quarter versus the last reported comp and consensus, what moved it, and how far a forecast at this day usually misses, with the two charts below. **By quarter**: reported comp against the day-30 forecast and the naive baseline for every scored quarter. **By day**: model and naive error for a forecast made on each day of the quarter. **Panel trends**: daily, trailing-7-day and QTD YoY by KPI for the last 13 months, newest first. **Notes**: who each sheet is for, definitions and assumptions. Every derived cell (panel change, forecast, model vs Street, errors, averages) is a live Excel formula; only pipeline outputs are pasted as values. |
| `kpi_forecasts.xlsx`, sheet **Forecast** | Analyst | Where does the model sit for the in-progress quarter versus the last reported comp and consensus, and what drives it (reference quarter, panel change, fitted slope, training size)? |
| `kpi_forecasts.xlsx`, sheet **Backtest** | Analyst | For every quarter with a prior-year comparison (fiscal 2023Q2 onward) and every day 1..N (N = days observed in the current quarter), what would the model, the naive baseline and the raw panel have said, and what was reported? |
| `kpi_forecasts.xlsx`, sheet **Errors by day** | Analyst | MAE, RMSE and bias in percentage points by KPI, day-in-quarter and method, scored on identical quarters. |
| `forecast_vs_actual.png` | PM | Has the day-N forecast tracked reported comps quarter by quarter, and where is it versus the Street now? |
| `error_by_day.png` | Analyst | How early in the quarter is the read trustworthy, and does it beat simply repeating the last comp? |
| `yoy_trends.png` | Analyst / PM | What is the panel saying about momentum right now: daily, trailing-7-day and quarter-to-date YoY, DIQ-aligned, for the last 13 months? |
| `forecasting_data.xlsx` | Engineer | The tidy daily dataset (spend, QTD, MTD, T7D and their DIQ-aligned YoY) for other consumers. |

Rates are stored as decimals (0.062 = 6.2%). Columns ending in `_pp` are percentage points.

## Repo layout

- `src/main.py`: entry point and shared loaders; exports the daily dataset, then runs the forecaster and the report.
- `src/normalization.py`, `src/calculations.py`, `src/schema.py`: daily and KPI transformations and pandera validation.
- `src/forecasting.py`: inputs, reference-quarter join, per-day model, scoring, workbook output.
- `src/report.py`: charts and the PM workbook.
- `src/workbook.py`: builds `urbn_kpi_nowcast.xlsx` (Summary, By quarter, By day, Panel trends, Notes).
- `src/data/`: the four source workbooks.
- `outputs/`: generated workbooks and charts.
- `PM_WRITEUP.docx`, `TECHNICAL_WRITEUP.docx`: the two writeups.
