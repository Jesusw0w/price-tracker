import datetime
import json
import pandas as pd


class ProcessData:
    def __init__(self, raw_data: list, url_list: list, historical_data: pd.DataFrame):
        self.raw_data = raw_data
        self.historical_data = historical_data
        self.url_list = url_list
        self.gpu_info = {}
        self.processed_data = pd.DataFrame()

    def create_gpu_df(self):
        print("Creating Dataframe...", flush=True)

        # Create column with GPU Names
        self.processed_data["GPU"] = [html.find("title").text.strip() for html in self.raw_data]

        # Create column with URL Names
        self.processed_data["URL"] = [url for url in self.url_list]

        # Creates a list with prices with a element that has price value
        find_prices = [
            json.loads(
                html.find("div",
                          {"class": "a-section aok-hidden twister-plus-buying-options-price-data"}).text.strip())
            for
            html in self.raw_data]

        # Create new column with the prices
        self.processed_data["Price"] = [dic[0]["priceAmount"] for dic in find_prices]

        # Associate extraction date to each row
        self.processed_data["Date"] = [pd.to_datetime(datetime.date.today()) for i in
                                       self.processed_data.index]

    def concat_historical_data(self):
        """
        Concatenates newly extracted data to the existing one in the CSV file from previous runs.
        """
        complete_data = pd.concat([self.historical_data, self.processed_data])

        complete_data.drop_duplicates(inplace=True)

        return complete_data
