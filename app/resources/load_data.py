import requests
import json
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
        self.gpu_info = {}

    def bs_extraction(self):
        print("Loading data...", flush=True)

        # Add urls to info dict
        # {f"gpu_{count}": html.find("title").text.strip() for count, html in enumerate(self.gpu_url_list)}
        # Get data from each link
        request_res = [requests.get(url, headers=self.header).text for url in self.gpu_url_list]

        # BS the html received from request
        soup = [BeautifulSoup(req) for req in request_res]

        # Add GPU titles to gpu_info
        self.gpu_info = {f"gpu_{count}": {"title": html.find("title").text.strip()} for count, html in enumerate(soup)}

        # Add Urls
        self.gpu_info = {f"gpu_{count}": {"url": url} for count, url in enumerate(self.gpu_url_list)}

        # Creates a list with prices with a element that has price value
        find_prices = [
            html.find("div", {"class": "a-section aok-hidden twister-plus-buying-options-price-data"}).text.strip() for
            html in soup]
        self.gpu_info = {f"gpu_{count}": {"price": json.loads(dic[1:-1]["priceAmount"])} for count, dic in
                         enumerate(find_prices)}

        return self.gpu_info
