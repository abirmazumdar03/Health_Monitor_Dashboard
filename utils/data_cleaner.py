import pandas as pd

def clean_timestamps(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    df = df.copy()
    df["meta.event_date"] = pd.to_datetime(df["meta.event_date"])

    return df.sort_values("meta.event_date", ascending=True)