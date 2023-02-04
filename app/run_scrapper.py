import os
from config import config_obj
from resources.load_data import ExtractData

def main():
    """
    Amazon Spain Web Scrapper Main file - calls all the resources necessary to display the data
    """
    print("App Starting...",flush=True)

    data = ExtractData(gpu_list=config_obj["gpu_links"]["nvidia"],config=config_obj).bs_extraction()
    
    print("Stop")
    
    
if __name__ == "main":
    main()