import requests
from bs4 import BeautifulSoup

class ExtractData:
    def __init__(self, gpu_list:list,config:dict):
        self.gpu_url_list = gpu_list
        self.config = config
        self.header = {("Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:53.0) Gecko/20100101 Firefox/53.0")}

    def bs_extraction(self):
        
        print("Loading data...",flush=True)
        
        #Set to url all links provided in gpu list selected
        gpu_url_list = [gpu_url.url for gpu_url in self.gpu_url_list]
        
        #Get data from each link
        requests = [requests.get(url,headers=self.header) for url in gpu_url_list]
        
        soup = [BeautifulSoup(request.content,feature="lxml") for request in requests]
        
        return  soup