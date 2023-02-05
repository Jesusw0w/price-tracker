import requests
from bs4 import BeautifulSoup


class ExtractData:
    def __init__(self, gpu_list: list, config: dict, category: str):
        self.gpu_url_list = gpu_list
        self.category = category
        self.config = config
        self.header = {(config["amz_header"]["firefox"])}

    def bs_extraction(self):
        print("Loading data...", flush=True)

        # Set to url all links provided in gpu list selected
        gpu_url_list = [url.url for gpu in self.gpu_url_list[self.category] for url in gpu]

        # Get data from each link
        request_res = [requests.get(url, headers=self.header) for url in gpu_url_list]

        soup = [BeautifulSoup(req.content, feature="lxml") for req in request_res]

        return soup
