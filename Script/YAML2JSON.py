# Convert all YAML files in a folder with subfolders to JSON

import yaml
import json
import os
import re
from Parameters import *

# mainFolder = "C:\\Data\\GitHub\\jetgeo\\OM2UML\\schema"

# Create a regular expression to match files with yaml extension
yaml_pattern = re.compile(r".+\.yaml$")

# Loop through the folder and its subfolders
for root, dirs, files in os.walk(schemaFolder):
    # Loop through the files in the current folder
    for file in files:
        # Get the full path of the file
        file_path = os.path.join(root, file)
        # Check if the file matches the yaml pattern
        if yaml_pattern.match(file_path):
          print(file_path)
          # Get the file name without extension
          file_name = os.path.splitext(file)[0]
          # Get the corresponding json file path
          json_file_path = os.path.join(root, file_name + ".json")
          # Check if the json file exists
          if os.path.exists(json_file_path):
              # Delete the json file
              os.remove(json_file_path)
              print("Deleted", json_file_path)
          # Open the yaml file and load it as a python dictionary
          with open(file_path, "r",encoding='utf-8') as yaml_file:
              try:
                yaml_dict = yaml.safe_load(yaml_file)
                # Convert the python dictionary to a json string
                json_str = json.dumps(yaml_dict)
                # Write the json string to the json file
                with open(json_file_path, "w") as json_file:
                    json_file.write(json_str)
                print("Converted", file_path, "to", json_file_path)
              except Exception as e:
                print("Error in conversion of ", file_path, "to", json_file_path, ": " + str(e))



    