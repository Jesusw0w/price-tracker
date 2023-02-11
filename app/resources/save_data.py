import pandas as pd

from app.config import historical_data_path


def write_csv(df: pd.DataFrame):
    """
    Saves data to csv file, uses pipe as separator in case price values start coming with comma instead of
    point for decimal places as we are working with an European location.
    """

    df.to_csv(historical_data_path, sep="|", index=False)
