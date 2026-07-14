import pandas as pd
from pathlib import Path

# -------------------------
# Project Root Detection
# -------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# -------------------------
# Data Paths
# -------------------------

RAW_DATA = PROJECT_ROOT / "data" / "raw"
PROCESSED_DATA = PROJECT_ROOT / "data" / "processed"
OUTPUT_DATA = PROJECT_ROOT / "data" / "output"

DATATHON_PATH = RAW_DATA / "datathon_data.csv"

# -------------------------
# Load Functions
# -------------------------

def load_datathon_data():
    """
    Load the multi-sheet datathon Excel workbook.

    Expected sheets:
    - A - Daily
    - A - Interval
    - B - Daily
    - B - Interval
    - C - Daily
    - C - Interval
    - D - Daily
    - D - Interval
    - Daily Staffing

    Returns
    -------
    dict
        {
            "daily": combined daily dataframe,
            "interval": combined interval dataframe,
            "staffing": daily staffing dataframe,
            "daily_by_client": {...},
            "interval_by_client": {...}
        }
    """

    file_path = RAW_DATA / "datathon_data.xlsx"
    xls = pd.ExcelFile(file_path)

    daily_by_client = {}
    interval_by_client = {}
    staffing_df = None

    for sheet_name in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet_name)

        clean_sheet = sheet_name.strip()

        if clean_sheet.lower() == "daily staffing":
            staffing_df = df.copy()
            continue

        if " - " not in clean_sheet:
            continue

        client, grain = [x.strip() for x in clean_sheet.split(" - ", 1)]
        client = client.upper()
        grain = grain.lower()

        df["client"] = client
        df["source_sheet"] = clean_sheet

        if grain == "daily":
            daily_by_client[client] = df
        elif grain == "interval":
            interval_by_client[client] = df

    daily_df = pd.concat(daily_by_client.values(), ignore_index=True) if daily_by_client else pd.DataFrame()
    interval_df = pd.concat(interval_by_client.values(), ignore_index=True) if interval_by_client else pd.DataFrame()

    return {
        "daily": daily_df,
        "interval": interval_df,
        "staffing": staffing_df,
        "daily_by_client": daily_by_client,
        "interval_by_client": interval_by_client,
    }

def load_forecast_data():
    file_path = RAW_DATA / "forecast_data.csv"
    return pd.read_csv(file_path)


def load_processed_data(filename):
    file_path = PROCESSED_DATA / filename
    return pd.read_csv(file_path)