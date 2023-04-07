import datetime
import json
import pandas as pd

from app.config import config_obj


class ProcessData:
    def __init__(self, raw_data: list, url_list: list, historical_data: pd.DataFrame):
        self.raw_data = raw_data
        self.historical_data = historical_data
        self.url_list = url_list
        self.gpu_info = {}
        self.processed_data = pd.DataFrame()

    def create_gpu_df(self):
        print("Creating Dataframe...", flush=True)

        # Create column with URL Names
        self.processed_data["URL"] = [url for url in self.url_list]

        # Create column with GPU Names removing Amazon category suffix
        self.processed_data["GPU"] = [(html.find("title").text.strip().replace(": Amazon.es: Informática", "")) for html
                                      in self.raw_data]

        # Creates a list with prices with an element that has price value
        find_prices = [self.check_prices(html) for html in self.raw_data]

        # Create new column with the prices
        self.processed_data["Price"] = [dic[0]["priceAmount"] if dic is not None else "N/A" for dic in find_prices]

        # Associate extraction date to each row
        self.processed_data["Date"] = [pd.to_datetime(datetime.date.today()) for i in
                                       self.processed_data.index]

    def concat_historical_data(self):
        """
        Concatenates newly extracted data to the existing one in the CSV file from previous runs.
        """
        complete_data = pd.concat([self.historical_data, self.processed_data]).replace(config_obj["AMZ Category"], "")

        complete_data.drop_duplicates(inplace=True)

        return complete_data

    @staticmethod
    def check_prices(x):
        try:
            if x is not None:
                try:
                    html_json = x.find("div",
                                       {"class": "a-section aok-hidden twister-plus-buying-options-price-data"})
                    if html_json is not None:
                        return json.loads(html_json.text.strip())

                except TypeError or AttributeError:
                    print(f"HTML not readable for {x}")

        except TypeError or AttributeError:
            print(f"HTML not readable for {x}")
