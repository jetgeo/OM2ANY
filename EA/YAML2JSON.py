import yaml
import json

mainFolder = "C:\\Users\\reise\\Documents\\GitHub\\OvertureMaps\\schema\\schema"
# defFile = mainFolder + "\\defs.yaml"
defFile = mainFolder + "\\transportation\\segment.yaml"

with open(defFile, 'r') as file:
  compiledFile = yaml.safe_load(file)
  
# Serializing json
json_object = json.dumps(compiledFile, indent=4)

 # Writing to json
with open(defFile[:-4] + 'json', "w") as outfile:
    outfile.write(json_object)   
    