import pandas as pd

from app.config import historical_data_path


def write_csv(df: pd.DataFrame) -> None:
    historical_data_path.parent.mkdir(parents=True, exist_ok=True)
    # Pipe separator: Spanish prices may arrive with comma decimals
    df.to_csv(historical_data_path, sep="|", index=False)
