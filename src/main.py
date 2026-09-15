"""Run the whole pipeline: tidy daily panel -> KPI forecasts -> charts and PM workbook."""

from pathlib import Path

import forecasting
import report
from data import DATA_DIR, load_daily_data


def main():
    as_of = None  # None = latest panel date, or e.g. "2026-08-15" for day 15 of 2027Q3
    out_dir = Path("outputs")

    out_dir.mkdir(exist_ok=True)
    daily = load_daily_data(DATA_DIR)
    daily.to_excel(out_dir / "forecasting_data.xlsx", index=False)

    panel, consensus = forecasting.load_inputs(daily, DATA_DIR)
    sheets = forecasting.run(panel, consensus, as_of)
    forecasting.write_sheets(sheets, out_dir / "kpi_forecasts.xlsx")
    print(sheets["Forecast"].to_string(index=False))

    pm_workbook = report.run(sheets, daily, out_dir)
    print(f"Wrote {out_dir}/*.xlsx, {pm_workbook} and {out_dir}/*.png")


if __name__ == "__main__":
    main()
