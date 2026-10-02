from typing import TypedDict

import pandas as pd
import requests
from bs4 import BeautifulSoup

from app.config import historical_data_path

TIMEOUT_S = 30


class RawData(TypedDict):
    url_list: list[str]
    gpu_raw_data: list[BeautifulSoup]


class ExtractData:
    def __init__(self, gpu_list: list[str]) -> None:
        self.gpu_url_list = gpu_list
        self.header = {
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64)"
                "AppleWebKit/537.36 (KHTML, like Gecko)"
                "Chrome/44.0.2403.157 Safari/537.36"
            ),
            "Accept-Language": "en-US, en;q=0.5",
        }

    def bs_extraction(self) -> RawData:
        print("Loading data...", flush=True)

        gpu_list = self.valid_urls(urls=self.gpu_url_list, header=self.header)

        request_res = [
            requests.get(url, headers=self.header, timeout=TIMEOUT_S).text
            for url in gpu_list
        ]

        amz_raw_data = [BeautifulSoup(req, "html.parser") for req in request_res]

        # Must be the filtered list, or URLs and pages misalign when one is invalid
        return {"url_list": gpu_list, "gpu_raw_data": amz_raw_data}

    @staticmethod
    def load_historical_data() -> pd.DataFrame:
        return pd.read_csv(historical_data_path, sep="|")

    @staticmethod
    def valid_urls(urls: list[str], header: dict[str, str]) -> list[str]:
        return [
            url
            for url in urls
            if requests.get(url, headers=header, timeout=TIMEOUT_S).status_code == 200
        ]
