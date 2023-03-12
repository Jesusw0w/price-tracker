import os

import pandas as pd
import plotly.express as px

from app.config import temp_dir


class Plot:
    def __init__(self, df: pd.DataFrame, x: str, y: str, legend: str):
        self.df = df
        self.x = x
        self.y = y
        self.legend = legend

    def linear_plot(self):
        fig = px.line(self.df, self.x, self.y, color=self.legend)
        fig.show()
        fig.write_html(os.path.join(temp_dir, "linear_plot.html"))
