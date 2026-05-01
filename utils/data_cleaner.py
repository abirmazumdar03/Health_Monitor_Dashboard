import pandas as pd

def clean_timestamps(df: pd.DataFrame) -> pd.DataFrame:
    df["meta.event_date"] = pd.to_datetime(df["meta.event_date"])
    return df.sort_values("meta.timestamp")
