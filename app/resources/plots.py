import os

import pandas as pd
import plotly.express as px

from app.config import temp_dir


class Plot:
    def __init__(self, df: pd.DataFrame, x: str, y: str, legend: str, title: str | None):
        self.df = df
        self.x = x
        self.y = y
        self.legend = legend
        self.title = title

    def linear_plot(self):
        """
        Creates a linear plot for the data passed in df argument
        """
        fig = px.line(self.df, self.x, self.y, color=self.legend, template='plotly_dark', title=self.title)

        fig.show()

        fig.write_html(os.path.join(temp_dir, "linear_plot.html"))
