import yaml
import json

mainFolder = "C:\\Data\\GitHub\\OvertureMaps\\schema\\schema"
defFile = mainFolder + "\\defs.yaml"

with open(defFile, 'r') as file:
  compiledFile = yaml.safe_load(file)
  #print(compiledFile)  
  print('Property definitions:')
  for i in compiledFile['$defs']['propertyDefinitions']:   
    print(i)
  
  print('')
  print('Property Containers:')
  for i in compiledFile['$defs']['propertyContainers']:   
    print(i)  

# Serializing json
json_object = json.dumps(compiledFile, indent=4)

 # Writing to json
with open(defFile[:-4] + 'json', "w") as outfile:
    outfile.write(json_object)   
    