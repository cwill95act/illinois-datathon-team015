import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.metrics import mean_absolute_error, mean_squared_error


# =========================================================
# Paths
# =========================================================
RAW_DATA = Path("data/raw")  # adjust if needed


# =========================================================
# Data loading
# =========================================================
def clean_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Standardize column names.
    """
    df = df.copy()
    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.replace("\n", " ", regex=False)
        .str.replace(r"\s+", " ", regex=True)
    )
    return df


def load_datathon_data(file_name: str = "datathon_data.xlsx") -> dict:
    """
    Load multi-sheet datathon workbook.

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
            "staffing": staffing dataframe,
            "daily_by_client": dict of daily dataframes,
            "interval_by_client": dict of interval dataframes
        }
    """
    file_path = RAW_DATA / file_name
    xls = pd.ExcelFile(file_path)

    daily_by_client = {}
    interval_by_client = {}
    staffing_df = None

    for sheet_name in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet_name)
        df = clean_columns(df)

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

    daily_df = (
        pd.concat(daily_by_client.values(), ignore_index=True)
        if daily_by_client else pd.DataFrame()
    )

    interval_df = (
        pd.concat(interval_by_client.values(), ignore_index=True)
        if interval_by_client else pd.DataFrame()
    )

    return {
        "daily": daily_df,
        "interval": interval_df,
        "staffing": staffing_df,
        "daily_by_client": daily_by_client,
        "interval_by_client": interval_by_client,
    }


def load_forecast_data(file_name: str = "forecast.xlsx") -> pd.DataFrame:
    """
    Load forecast template workbook or sheet.

    If there are multiple sheets, the first one is used unless
    there is a sheet named 'Forecast'.
    """
    file_path = RAW_DATA / file_name
    xls = pd.ExcelFile(file_path)

    sheet_to_use = "Forecast" if "Forecast" in xls.sheet_names else xls.sheet_names[0]
    df = pd.read_excel(xls, sheet_name=sheet_to_use)
    df = clean_columns(df)

    return df


# =========================================================
# Date and time cleaning
# =========================================================
def clean_daily_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean daily aggregate dataset.

    Expected columns:
    - Date
    - Call Volume
    - CCT
    - Service Level
    - Abandon Rate
    - client
    """
    df = df.copy()
    df = clean_columns(df)

    if "Date" in df.columns:
        df["Date_raw"] = df["Date"]
        df["Date"] = df["Date"].astype(str).str.split().str[0]
        df["Date"] = pd.to_datetime(df["Date"], format="%m/%d/%y", errors="coerce")

    numeric_cols = ["Call Volume", "CCT", "Service Level", "Abandon Rate"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "Call Volume" in df.columns:
        df = df[df["Call Volume"].isna() | (df["Call Volume"] >= 0)]

    if "CCT" in df.columns:
        df = df[df["CCT"].isna() | (df["CCT"] >= 0)]

    if "Service Level" in df.columns:
        df["Service Level"] = df["Service Level"].clip(lower=0, upper=1)

    if "Abandon Rate" in df.columns:
        df["Abandon Rate"] = df["Abandon Rate"].clip(lower=0, upper=1)

    cols_to_drop = ["hour", "minute", "datetime", "time_index"]
    df = df.drop(columns=[c for c in cols_to_drop if c in df.columns], errors="ignore")

    sort_cols = [c for c in ["client", "Date"] if c in df.columns]
    if sort_cols:
        df = df.sort_values(sort_cols).reset_index(drop=True)

    return df


def clean_interval_data(df: pd.DataFrame, date_col: str = "Date") -> pd.DataFrame:
    """
    Clean historical intraday interval data from A/B/C/D sheets.

    Expected examples:
    - Date
    - Interval
    - Call Volume / Calls Offered
    - CCT
    - Abandon Rate
    - client
    """
    df = df.copy()
    df = clean_columns(df)

    if date_col in df.columns:
        df["Date_raw"] = df[date_col]
        parsed = df[date_col].astype(str).str.split().str[0]
        df["Date"] = pd.to_datetime(parsed, format="%m/%d/%y", errors="coerce")

    if "Interval" in df.columns:
        df["Interval"] = df["Interval"].astype(str).str.strip()
        parts = df["Interval"].str.split(":", expand=True)
        if parts.shape[1] >= 2:
            df["hour"] = pd.to_numeric(parts[0], errors="coerce")
            df["minute"] = pd.to_numeric(parts[1], errors="coerce")
            df["time_index"] = df["hour"] * 2 + (df["minute"] // 30)

    if {"Date", "Interval"}.issubset(df.columns):
        df["datetime"] = pd.to_datetime(
            df["Date"].dt.strftime("%Y-%m-%d") + " " + df["Interval"],
            errors="coerce"
        )

    numeric_candidates = [
        "Call Volume", "Calls Offered", "Calls_Offered",
        "Abandoned Calls", "Abandoned Rate",
        "CCT", "Service Level"
    ]

    for col in df.columns:
        if col in numeric_candidates:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    sort_cols = [c for c in ["client", "datetime"] if c in df.columns]
    if sort_cols:
        df = df.sort_values(sort_cols).reset_index(drop=True)

    return df


def clean_intraday_template(df: pd.DataFrame, year: int = 2024) -> pd.DataFrame:
    """
    Clean forecast template.

    Expected columns:
    - Month
    - Day
    - Interval
    - Calls_Offered_A ... Calls_Offered_D
    - Abandoned_Calls_A ... Abandoned_Calls_D
    - Abandoned_Rate_A ... Abandoned_Rate_D
    - CCT_A ... CCT_D
    """
    df = df.copy()
    df = clean_columns(df)

    if "Month" in df.columns:
        df["Month"] = df["Month"].astype(str).str.strip()

    if "Day" in df.columns:
        df["Day"] = pd.to_numeric(df["Day"], errors="coerce")

    if "Interval" in df.columns:
        df["Interval"] = df["Interval"].astype(str).str.strip()

        parts = df["Interval"].str.split(":", expand=True)
        if parts.shape[1] >= 2:
            df["hour"] = pd.to_numeric(parts[0], errors="coerce")
            df["minute"] = pd.to_numeric(parts[1], errors="coerce")
            df["time_index"] = df["hour"] * 2 + (df["minute"] // 30)

    if "Month" in df.columns:
        df["month_num"] = pd.to_datetime(
            df["Month"],
            format="%B",
            errors="coerce"
        ).dt.month

    if {"month_num", "Day", "Interval"}.issubset(df.columns):
        date_str = (
            str(year) + "-"
            + df["month_num"].astype("Int64").astype(str) + "-"
            + df["Day"].astype("Int64").astype(str) + " "
            + df["Interval"]
        )
        df["datetime"] = pd.to_datetime(date_str, errors="coerce")

    if "datetime" in df.columns:
        df = df.sort_values("datetime").reset_index(drop=True)

    return df


# =========================================================
# Missing value handling
# =========================================================
def fill_missing(
    df: pd.DataFrame,
    method: str = "ffill_then_bfill",
    group_col: str | None = None
) -> pd.DataFrame:
    """
    Fill missing values, optionally within groups.
    """
    df = df.copy()

    if group_col is not None and group_col in df.columns:
        if method == "ffill":
            return df.groupby(group_col, group_keys=False).apply(lambda x: x.ffill())
        if method == "bfill":
            return df.groupby(group_col, group_keys=False).apply(lambda x: x.bfill())
        if method == "ffill_then_bfill":
            return df.groupby(group_col, group_keys=False).apply(lambda x: x.ffill().bfill())
        if method == "zero":
            return df.fillna(0)
        raise ValueError("Unsupported fill method.")

    if method == "ffill":
        return df.ffill()
    if method == "bfill":
        return df.bfill()
    if method == "ffill_then_bfill":
        return df.ffill().bfill()
    if method == "zero":
        return df.fillna(0)

    raise ValueError("Unsupported fill method.")


# =========================================================
# Time-based feature engineering
# =========================================================
def add_time_features(
    df: pd.DataFrame,
    datetime_col: str = "Date"
) -> pd.DataFrame:
    df = df.copy()

    if datetime_col not in df.columns:
        return df

    if not pd.api.types.is_datetime64_any_dtype(df[datetime_col]):
        return df

    df["day_of_week"] = df[datetime_col].dt.dayofweek
    df["day_name"] = df[datetime_col].dt.day_name()

    df["month"] = df[datetime_col].dt.month
    df["month_name"] = df[datetime_col].dt.month_name()

    df["day_of_month"] = df[datetime_col].dt.day
    df["week_of_year"] = df[datetime_col].dt.isocalendar().week.astype(int)
    df["quarter"] = df[datetime_col].dt.quarter
    df["quarter_label"] = "Q" + df["quarter"].astype(str)

    df["is_weekend"] = df["day_of_week"].isin([5, 6]).astype(int)
    df["is_monday"] = (df["day_of_week"] == 0).astype(int)
    df["is_sunday"] = (df["day_of_week"] == 6).astype(int)

    df["is_month_start"] = (df["day_of_month"] <= 3).astype(int)
    df["is_month_end"] = (df["day_of_month"] >= 28).astype(int)
    df["is_pay_period"] = df["day_of_month"].isin([1, 15]).astype(int)

    df["dow_sin"] = np.sin(2 * np.pi * df["day_of_week"] / 7)
    df["dow_cos"] = np.cos(2 * np.pi * df["day_of_week"] / 7)

    df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)
    df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)

    try:
        df["hour"] = df[datetime_col].dt.hour
        df["minute"] = df[datetime_col].dt.minute
        df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24)
        df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24)
        if "hour" in df.columns and "minute" in df.columns:
            interval_num = df["hour"] * 2 + (df["minute"] // 30)
            df["interval_num"] = interval_num
            df["interval_sin"] = np.sin(2 * np.pi * interval_num / 48)
            df["interval_cos"] = np.cos(2 * np.pi * interval_num / 48)
    except Exception:
        pass

    return df


# =========================================================
# Lag Features
# =========================================================
def add_lag_features(
    df: pd.DataFrame,
    column: str,
    lags=None,
    group_col: str = "client",
    sort_col: str = "Date"
) -> pd.DataFrame:
    df = df.copy()

    if column not in df.columns:
        return df

    if lags is None:
        lags = [1, 2, 7, 14, 21, 28]

    sort_cols = [c for c in [group_col, sort_col] if c in df.columns]
    if sort_cols:
        df = df.sort_values(sort_cols).reset_index(drop=True)

    for lag in lags:
        if group_col in df.columns:
            df[f"{column}_lag_{lag}"] = df.groupby(group_col)[column].shift(lag)
        else:
            df[f"{column}_lag_{lag}"] = df[column].shift(lag)

    return df


# =========================================================
# Rolling Features
# =========================================================
def add_rolling_features(
    df: pd.DataFrame,
    column: str,
    windows=None,
    group_col: str = "client",
    sort_col: str = "Date"
) -> pd.DataFrame:
    df = df.copy()

    if column not in df.columns:
        return df

    if windows is None:
        windows = [3, 7, 14, 30]

    sort_cols = [c for c in [group_col, sort_col] if c in df.columns]
    if sort_cols:
        df = df.sort_values(sort_cols).reset_index(drop=True)

    if group_col in df.columns:
        for window in windows:
            shifted = df.groupby(group_col)[column].shift(1)

            df[f"{column}_rollmean_{window}"] = (
                shifted.groupby(df[group_col])
                .rolling(window)
                .mean()
                .reset_index(level=0, drop=True)
            )

            df[f"{column}_rollstd_{window}"] = (
                shifted.groupby(df[group_col])
                .rolling(window)
                .std()
                .reset_index(level=0, drop=True)
            )

            df[f"{column}_rollmin_{window}"] = (
                shifted.groupby(df[group_col])
                .rolling(window)
                .min()
                .reset_index(level=0, drop=True)
            )

            df[f"{column}_rollmax_{window}"] = (
                shifted.groupby(df[group_col])
                .rolling(window)
                .max()
                .reset_index(level=0, drop=True)
            )
    else:
        for window in windows:
            rolling_obj = df[column].shift(1).rolling(window)
            df[f"{column}_rollmean_{window}"] = rolling_obj.mean()
            df[f"{column}_rollstd_{window}"] = rolling_obj.std()
            df[f"{column}_rollmin_{window}"] = rolling_obj.min()
            df[f"{column}_rollmax_{window}"] = rolling_obj.max()

    return df

def add_interaction_features(df: pd.DataFrame) -> pd.DataFrame:

    df = df.copy()

    # =========================================================
    # Lag Difference
    # =========================================================

    if {"Call Volume", "Call Volume_lag_7"}.issubset(df.columns):

        df["diff_lag7"] = (
            df["Call Volume"]
            - df["Call Volume_lag_7"]
        )

    # =========================================================
    # SAFE pct_change_7
    # =========================================================

    if "Call Volume" in df.columns:

        if "client" in df.columns:

            lag7 = df.groupby("client")["Call Volume"].shift(7)

        else:

            lag7 = df["Call Volume"].shift(7)

        df["pct_change_7"] = (
            (df["Call Volume"] - lag7)
            / lag7.replace(0, np.nan)
        )

        # Replace bad values
        df["pct_change_7"] = (
            df["pct_change_7"]
            .replace([np.inf, -np.inf], np.nan)
            .fillna(0)
        )

        # Optional stabilization (recommended)
        df["pct_change_7"] = df["pct_change_7"].clip(-5, 5)

    # =========================================================
    # Volatility Ratio
    # =========================================================

    if {"Call Volume_rollstd_7", "Call Volume_rollmean_7"}.issubset(df.columns):

        df["volatility_ratio"] = (
            df["Call Volume_rollstd_7"]
            / df["Call Volume_rollmean_7"].replace(0, np.nan)
        )

        df["volatility_ratio"] = (
            df["volatility_ratio"]
            .replace([np.inf, -np.inf], np.nan)
            .fillna(0)
        )

    # =========================================================
    # Interaction Features
    # =========================================================

    if {"Call Volume", "Service Level"}.issubset(df.columns):

        df["volume_x_service"] = (
            df["Call Volume"]
            * df["Service Level"]
        )

    if {"Call Volume", "Abandon Rate"}.issubset(df.columns):

        df["volume_x_abandon"] = (
            df["Call Volume"]
            * df["Abandon Rate"]
        )

    if {"Call Volume_lag_7", "is_weekend"}.issubset(df.columns):

        df["lag7_x_weekend"] = (
            df["Call Volume_lag_7"]
            * df["is_weekend"]
        )

    if {"interval_num", "day_of_week"}.issubset(df.columns):

        df["interval_x_dow"] = (
            df["interval_num"]
            * df["day_of_week"]
        )

    return df


# =========================================================
# Trend features
# =========================================================
def add_trend_features(
    df: pd.DataFrame,
    group_col: str | None = None
) -> pd.DataFrame:
    df = df.copy()

    if group_col is not None and group_col in df.columns:
        df["trend"] = df.groupby(group_col).cumcount()
    else:
        df["trend"] = np.arange(len(df))

    df["trend_squared"] = df["trend"] ** 2

    return df


# =========================================================
# Validation cleaning
# =========================================================
def drop_rows_created_by_lags(df: pd.DataFrame) -> pd.DataFrame:
    return df.dropna().reset_index(drop=True)


def validate_daily_data(df: pd.DataFrame, date_col: str = "Date") -> dict:
    df = df.copy()
    results = {}

    results["missing_values"] = df.isna().sum()

    subset_cols = [c for c in ["client", date_col] if c in df.columns]
    if date_col in df.columns:
        results["duplicate_dates"] = df[
            df.duplicated(subset=subset_cols, keep=False)
        ].copy()
    else:
        results["duplicate_dates"] = pd.DataFrame()

    results["negative_call_volume"] = (
        df[df["Call Volume"] < 0].copy()
        if "Call Volume" in df.columns else pd.DataFrame()
    )

    results["negative_cct"] = (
        df[df["CCT"] < 0].copy()
        if "CCT" in df.columns else pd.DataFrame()
    )

    results["invalid_service_level"] = (
        df[(df["Service Level"] < 0) | (df["Service Level"] > 1)].copy()
        if "Service Level" in df.columns else pd.DataFrame()
    )

    results["invalid_abandon_rate"] = (
        df[(df["Abandon Rate"] < 0) | (df["Abandon Rate"] > 1)].copy()
        if "Abandon Rate" in df.columns else pd.DataFrame()
    )

    all_null_cols = [col for col in df.columns if df[col].isna().all()]
    results["all_null_columns"] = all_null_cols

    constant_cols = [col for col in df.columns if df[col].nunique(dropna=True) <= 1]
    results["constant_columns"] = constant_cols

    return results


def validate_interval_data(df: pd.DataFrame) -> dict:
    df = df.copy()
    results = {}

    results["missing_values"] = df.isna().sum()

    # choose the correct interval-level uniqueness key
    if {"client", "Date", "Interval"}.issubset(df.columns):
        dup_subset = ["client", "Date", "Interval"]
    elif {"client", "datetime", "Interval"}.issubset(df.columns):
        df["date_only"] = pd.to_datetime(df["datetime"], errors="coerce").dt.date
        dup_subset = ["client", "date_only", "Interval"]
    else:
        dup_subset = []

    if dup_subset:
        results["duplicate_client_interval_rows"] = df[
            df.duplicated(subset=dup_subset, keep=False)
        ].copy()
    else:
        results["duplicate_client_interval_rows"] = pd.DataFrame()

    # check interval count per client-day
    if {"client", "Date", "Interval"}.issubset(df.columns):
        interval_counts = (
            df.groupby(["client", "Date"])
              .size()
              .reset_index(name="interval_count")
        )
        results["bad_interval_counts"] = interval_counts[
            interval_counts["interval_count"] != 48
        ].copy()

    elif {"client", "datetime"}.issubset(df.columns):
        temp = df.copy()
        temp["date_only"] = pd.to_datetime(temp["datetime"], errors="coerce").dt.date
        interval_counts = (
            temp.groupby(["client", "date_only"])
                .size()
                .reset_index(name="interval_count")
        )
        results["bad_interval_counts"] = interval_counts[
            interval_counts["interval_count"] != 48
        ].copy()
    else:
        results["bad_interval_counts"] = pd.DataFrame()

    all_null_cols = [col for col in df.columns if df[col].isna().all()]
    results["all_null_columns"] = all_null_cols

    constant_cols = [col for col in df.columns if df[col].nunique(dropna=True) <= 1]
    results["constant_columns"] = constant_cols

    return results


def validate_forecast_template(df: pd.DataFrame) -> dict:
    df = df.copy()
    results = {}

    results["missing_values"] = df.isna().sum()

    if "datetime" in df.columns:
        results["duplicate_datetimes"] = df[
            df.duplicated(subset=["datetime"], keep=False)
        ].copy()
    else:
        results["duplicate_datetimes"] = pd.DataFrame()

    if {"Month", "Day", "Interval"}.issubset(df.columns):
        results["duplicate_interval_rows"] = df[
            df.duplicated(subset=["Month", "Day", "Interval"], keep=False)
        ].copy()
    else:
        results["duplicate_interval_rows"] = pd.DataFrame()

    if "datetime" in df.columns and pd.api.types.is_datetime64_any_dtype(df["datetime"]):
        temp = df.copy()
        temp["date_only"] = temp["datetime"].dt.date
        interval_counts = temp.groupby("date_only").size().reset_index(name="interval_count")
        results["bad_interval_counts"] = interval_counts[
            interval_counts["interval_count"] != 48
        ].copy()
    elif {"Month", "Day"}.issubset(df.columns):
        interval_counts = df.groupby(["Month", "Day"]).size().reset_index(name="interval_count")
        results["bad_interval_counts"] = interval_counts[
            interval_counts["interval_count"] != 48
        ].copy()
    else:
        results["bad_interval_counts"] = pd.DataFrame()

    if "Interval" in df.columns:
        valid_minutes = {"00", "30"}
        invalid_rows = []

        for idx, val in df["Interval"].dropna().items():
            parts = str(val).split(":")
            if len(parts) != 2:
                invalid_rows.append(idx)
                continue
            hour, minute = parts[0], parts[1]
            if not hour.isdigit():
                invalid_rows.append(idx)
                continue
            if minute not in valid_minutes:
                invalid_rows.append(idx)
                continue
            hour_int = int(hour)
            if hour_int < 0 or hour_int > 23:
                invalid_rows.append(idx)

        results["invalid_interval_format_rows"] = (
            df.loc[invalid_rows].copy() if invalid_rows else pd.DataFrame()
        )
    else:
        results["invalid_interval_format_rows"] = pd.DataFrame()

    all_null_cols = [col for col in df.columns if df[col].isna().all()]
    results["all_null_columns"] = all_null_cols

    constant_cols = [col for col in df.columns if df[col].nunique(dropna=True) <= 1]
    results["constant_columns"] = constant_cols

    return results


def run_validation_checks(
    df_daily: pd.DataFrame,
    df_interval: pd.DataFrame,
    df_forecast: pd.DataFrame
) -> dict:
    return {
        "daily_validation": validate_daily_data(df_daily),
        "interval_validation": validate_interval_data(df_interval),
        "forecast_validation": validate_forecast_template(df_forecast),
    }


def print_validation_summary(results: dict) -> None:
    daily = results.get("daily_validation", {})
    interval = results.get("interval_validation", {})
    forecast = results.get("forecast_validation", {})

    print("\n==============================")
    print("DAILY DATA VALIDATION SUMMARY")
    print("==============================")
    print("Duplicate dates:", len(daily.get("duplicate_dates", [])))
    print("Negative Call Volume rows:", len(daily.get("negative_call_volume", [])))
    print("Negative CCT rows:", len(daily.get("negative_cct", [])))
    print("Invalid Service Level rows:", len(daily.get("invalid_service_level", [])))
    print("Invalid Abandon Rate rows:", len(daily.get("invalid_abandon_rate", [])))
    print("All-null columns:", daily.get("all_null_columns", []))
    print("Constant columns:", daily.get("constant_columns", []))

    print("\n================================")
    print("INTERVAL DATA VALIDATION SUMMARY")
    print("================================")
    print("Duplicate client/date/interval rows:",
          len(interval.get("duplicate_client_interval_rows", [])))
    print("Bad interval counts:", len(interval.get("bad_interval_counts", [])))
    print("All-null columns:", interval.get("all_null_columns", []))
    print("Constant columns:", interval.get("constant_columns", []))

    print("\n===================================")
    print("FORECAST TEMPLATE VALIDATION SUMMARY")
    print("===================================")
    print("Duplicate datetimes:", len(forecast.get("duplicate_datetimes", [])))
    print("Duplicate interval rows:", len(forecast.get("duplicate_interval_rows", [])))
    print("Bad interval counts:", len(forecast.get("bad_interval_counts", [])))
    print("Invalid interval format rows:",
          len(forecast.get("invalid_interval_format_rows", [])))
    print("All-null columns:", forecast.get("all_null_columns", []))
    print("Constant columns:", forecast.get("constant_columns", []))

# =========================================================
# Prediction post-processing
# =========================================================
def clip_predictions(preds, lower: float = 0.0):
    preds = np.asarray(preds)
    return np.clip(preds, lower, None)


def apply_overforecast_buffer(preds, pct: float = 0.03):
    preds = np.asarray(preds)
    return preds * (1 + pct)


# =========================================================
# Workload and scoring helpers
# =========================================================
def calculate_workload(volume, cct):
    volume = np.asarray(volume)
    cct = np.asarray(cct)
    return volume * cct


def asymmetric_error(y_true, y_pred, under_weight: float = 2.0, over_weight: float = 1.0):
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)

    diff = y_pred - y_true
    penalties = np.where(diff < 0, np.abs(diff) * under_weight, np.abs(diff) * over_weight)
    return penalties.mean()


def competition_style_score(
    actual_volume,
    pred_volume,
    actual_cct,
    pred_cct,
    actual_abandon,
    pred_abandon,
    w_volume: float = 1.0,
    w_cct: float = 1.0,
    w_abandon: float = 1.0,
    w_workload: float = 1.0,
    under_weight: float = 2.0,
    over_weight: float = 1.0,
):
    actual_volume = np.asarray(actual_volume)
    pred_volume = np.asarray(pred_volume)
    actual_cct = np.asarray(actual_cct)
    pred_cct = np.asarray(pred_cct)
    actual_abandon = np.asarray(actual_abandon)
    pred_abandon = np.asarray(pred_abandon)

    vol_err = asymmetric_error(actual_volume, pred_volume, under_weight, over_weight)
    cct_err = asymmetric_error(actual_cct, pred_cct, under_weight, over_weight)
    abd_err = asymmetric_error(actual_abandon, pred_abandon, under_weight, over_weight)

    actual_workload = calculate_workload(actual_volume, actual_cct)
    pred_workload = calculate_workload(pred_volume, pred_cct)
    workload_penalty = asymmetric_error(actual_workload, pred_workload, under_weight, over_weight)

    composite = (
        w_volume * vol_err
        + w_cct * cct_err
        + w_abandon * abd_err
        + w_workload * workload_penalty
    )

    return {
        "volume_error": vol_err,
        "cct_error": cct_err,
        "abandon_error": abd_err,
        "workload_penalty": workload_penalty,
        "composite_score": composite,
    }


# =========================================================
# Standard regression metrics
# =========================================================
def regression_metrics(y_true, y_pred):
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)

    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))

    return {
        "mae": mae,
        "rmse": rmse,
    }


# =========================================================
# Wide/long reshaping helpers
# =========================================================
def melt_portfolio_columns(df: pd.DataFrame, id_vars=None) -> pd.DataFrame:
    df = df.copy()

    if id_vars is None:
        id_vars = [col for col in ["Month", "Day", "Interval", "datetime"] if col in df.columns]

    value_vars = [col for col in df.columns if col not in id_vars]

    return df.melt(
        id_vars=id_vars,
        value_vars=value_vars,
        var_name="feature",
        value_name="value"
    )


# =========================================================
# Quick pipeline helpers
# =========================================================
def prepare_daily_data(df: pd.DataFrame) -> pd.DataFrame:
    df = clean_daily_data(df)
    df = add_time_features(df, datetime_col="Date")
    return df


def prepare_interval_data(df: pd.DataFrame) -> pd.DataFrame:
    df = clean_interval_data(df)
    df = add_time_features(df, datetime_col="datetime")
    return df


def prepare_intraday_data(df: pd.DataFrame, year: int = 2024) -> pd.DataFrame:
    df = clean_intraday_template(df, year=year)
    df = add_time_features(df, datetime_col="datetime")
    return df