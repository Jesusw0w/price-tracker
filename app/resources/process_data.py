import pandas as pd


class ProcessData:
    def __init__(self, gpu_info):
        super().__init__(gpu_info)
    def data_to_df(self):
        gpus_df = [pd.DataFrame(dic) for dic in self.gpu_info]
