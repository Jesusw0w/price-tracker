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

    processed_data = ProcessData(raw_data=data["gpu_raw_data"], url_list=data["url_list"])

    gpu_dictionary = processed_data.format_and_organize_soup()

    print(gpu_dictionary)


if __name__ == "__main__":
    main(category="all")
