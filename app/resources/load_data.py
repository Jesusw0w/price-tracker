import requests
from bs4 import BeautifulSoup


class ExtractData:
    def __init__(self, gpu_list: list, config: dict, category: str):
        self.gpu_url_list = gpu_list
        self.category = category
        self.config = config
        self.header = {'User-Agent': ('Mozilla/5.0 (X11; Linux x86_64)'
                                      'AppleWebKit/537.36 (KHTML, like Gecko)'
                                      'Chrome/44.0.2403.157 Safari/537.36'),
                       'Accept-Language': 'en-US, en;q=0.5'}
        # self.raw_data = []

    def bs_extraction(self):
        """
        To add class with the process stepwise later, self.raw_data = [BeautifulSoup(req) for req in request_res]
        """
        print("Loading data...", flush=True)

        # Add urls to info dict
        # {f"gpu_{count}": html.find("title").text.strip() for count, html in enumerate(self.gpu_url_list)}
        # Get data from each link
        request_res = [requests.get(url, headers=self.header).text for url in self.gpu_url_list]

        # BS the html received from request
        amz_raw_data = [BeautifulSoup(req) for req in request_res]

        # Creates dict with url list and gpu_
        raw_data = {"url_list": self.gpu_url_list, "gpu_raw_data": amz_raw_data}

        return raw_data
