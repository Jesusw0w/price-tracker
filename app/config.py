import os
import json

# Directory list
project_dir = os.path.dirname(os.path.abspath(__file__)) 
app_dir =  os.path.join(project_dir,"app")
resources_dir = os.path.join(app_dir,"resources")
data_dir = os.path.join(app_dir,"data")
static_dir = os.path.join(data_dir,"static")
views_dir = os.path.join(app_dir,"views")

# Load json file
config_obj = json.load(os.path.join(static_dir,"config.json"))