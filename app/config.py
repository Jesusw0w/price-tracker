import os
import json

# Directory list
app_dir = os.path.dirname(os.path.abspath(__file__))
resources_dir = os.path.join(app_dir, "resources")
data_dir = os.path.join(app_dir, "data")
static_dir = os.path.join(data_dir, "static")
views_dir = os.path.join(app_dir, "views")

# Load json file
config_obj = json.load(open(os.path.join(static_dir, "config.json")))

# Historical Data Path
historical_data_path = os.path.join(data_dir, "gpu_data.csv")
