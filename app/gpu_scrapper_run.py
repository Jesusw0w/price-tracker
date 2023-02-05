import os
from config import config_obj
from resources.load_data import ExtractData
from resources.process_data import ProcessData


def main(category: str):
    """
    Amazon Spain Web Scrapper Main file - calls all the resources necessary to display the data
    """
    print("App Starting...", flush=True)

    if category == "":
        category = "all"

    data = ExtractData(gpu_list=config_obj["gpu_links"]["all"], category=category, config=config_obj).bs_extraction()

    processed_data = ProcessData(data)
    print(data)


if __name__ == "__main__":
    main(category="all")
