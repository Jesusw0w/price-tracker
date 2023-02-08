import json
import pandas as pd


class ProcessData:
    def __init__(self, raw_data: list, url_list: list):
        self.raw_data = raw_data
        self.url_list = url_list
        self.gpu_info = {}

    def format_and_organize_soup(self):
        print("Formatting and organizing data...")

        # Add GPU titles to gpu_info
        self.gpu_info = {f"gpu_{count}": {"title": html.find("title").text.strip()} for count, html in
                         enumerate(self.raw_data)}

        # Add Urls
        self.gpu_info = {f"gpu_{count}": {"url": url} for count, url in enumerate(self.url_list)}

        test = [
            json.dumps(
                html.find("div",
                          {"class": "a-section aok-hidden twister-plus-buying-options-price-data"}).text.strip())
            for
            html in self.raw_data]
        # Creates a list with prices with a element that has price value
        find_prices = [
            json.loads(
                html.find("div",
                          {"class": "a-section aok-hidden twister-plus-buying-options-price-data"}).text.strip())
            for
            html in self.raw_data]
        # This step may be avoided if we convert json to dataframe . Check tomorrow
        lists_to_dict = [data[0] for count, data in enumerate(find_prices)]

        to_df = pd.DataFrame.from_dict(data=lists_to_dict[0], orient="index")

        self.gpu_info = {f"gpu_{count}": {"price": json.loads(dic["priceAmount"])} for count, dic in
                         enumerate(find_prices)}

    def data_to_df(self):
        gpus_df = [pd.DataFrame(dic) for dic in self.gpu_info]
