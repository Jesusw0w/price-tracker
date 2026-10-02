import datetime
import json
from typing import Any

import pandas as pd
from bs4 import BeautifulSoup

PRICE_DATA_CLASS = "a-section aok-hidden twister-plus-buying-options-price-data"


class ProcessData:
    def __init__(
        self,
        raw_data: list[BeautifulSoup],
        url_list: list[str],
        historical_data: pd.DataFrame,
    ) -> None:
        self.raw_data = raw_data
        self.historical_data = historical_data
        self.url_list = url_list
        self.processed_data = pd.DataFrame()

    def create_gpu_df(self) -> None:
        print("Creating Dataframe...", flush=True)

        self.processed_data["URL"] = self.url_list

        self.processed_data["GPU"] = [
            html.title.text.replace(": Amazon.es: Informática", "").strip()
            if html.title
            else "N/A"
            for html in self.raw_data
        ]

        find_prices = [self.check_prices(html) for html in self.raw_data]

        self.processed_data["Price"] = [
            dic[0]["priceAmount"] if dic is not None else "N/A" for dic in find_prices
        ]

        # ISO date string, matching what read_csv gives back for older rows
        self.processed_data["Date"] = datetime.date.today().isoformat()

    def concat_historical_data(self) -> pd.DataFrame:
        """Append this run's rows to the CSV history, dropping exact duplicates."""
        complete_data = pd.concat([self.historical_data, self.processed_data])

        return complete_data.drop_duplicates()

    @staticmethod
    def check_prices(html: BeautifulSoup) -> Any:  # noqa: ANN401  # raw Amazon JSON
        price_data = html.find("div", {"class": PRICE_DATA_CLASS})
        if price_data is None:
            return None
        try:
            return json.loads(price_data.text.strip())
        except json.JSONDecodeError:
            print(f"Price data not readable for {html.title}")
            return None
