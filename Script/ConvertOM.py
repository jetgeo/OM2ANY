from Parameters import *
from EAConnect import *
import sys, os, re, yaml, json


# Open EA Reopsitory and find OM Model
eaApp = openEAapp()
eaRepo = openEArepo(eaApp,repo_path)
for eaMod in eaRepo.Models:
    printTS('Model: ' + eaMod.Name)
    if eaMod.Name == modelName:
        omMod = eaMod

try:
    printTS('Overture Maps model found with PackageGUID ' + omMod.PackageGUID )
except Exception as e:
    printTS('OvertureMaps model not found!')
    closeEA()
    sys.exit()

printTS('Number of existing packages: ' + str(omMod.Packages.Count))

# Create a regular expression to match files with yaml extension
yaml_pattern = re.compile(r".+\.yaml$")
omMod.Packages.Refresh()

for folder, subfolders, files in os.walk(schemaFolder):
    # Get or create packages from folder names ("Common" for the root folder)
    if os.path.relpath(folder, schemaFolder) == ".":
        strName = 'Common'
    else:
        strName = os.path.basename(folder)
        strName = strName[0].upper() + strName[1:]
    
    try:
        eaPck = omMod.Packages.GetByName(strName)
    except:
        eaPck = None   
    if eaPck != None:
        printTS('Existing package "' + strName + '"')
    else:
        eaPck = omMod.Packages.AddNew(strName,"")
        eaPck.Update()
        omMod.Packages.Refresh()
        printTS('Added package "' + strName + '"')
    # Keep the "Common" package for later use
    if strName == "Common":
        omCommonPck = eaPck

    for file in files:
        # Get the full path of the file
        file_path = os.path.join(folder, file)
        # Check if the file matches the yaml pattern
        if yaml_pattern.match(file_path):
          #printTS('File: '+ file_path)
          # Get the file name without extension
          file_name = os.path.splitext(file)[0]
          if (file_name == 'schema'):
            continue

          # Open the yaml file and load it as a python dictionary
          with open(file_path, "r",encoding='utf-8') as yaml_file:
            try:
                yaml_dict = yaml.safe_load(yaml_file)
            except Exception as e:
                printTS("Error in conversion of " + file_path + " to dictionary: " + str(e))
                closeEA()
                sys.exit()

            #Uppercase first character in name    
            strName = file_name[0].upper() + file_name[1:]

            #Start processing schema
            for i in yaml_dict:
                if i == 'title':
                    strAlias = yaml_dict[i]
                    printTS('Schema title: ' + strAlias)
                elif i == 'description':
                    strDef = yaml_dict[i]
                    printTS('Schema description: ' + strDef)
                elif i == '$defs':
			        # Definition statements
                    printTS('Global properties')
                    # Get or create Defs Class, delete all existing attributes 
                    strName = eaPck.Name + "Defs"
                    eaEl = getOrCreateElementByName(eaPck,strName,True,strAlias,strDef,True)
                    for j in yaml_dict[i]:
                        if (j == 'propertyDefinitions') or (j == 'propertyContainers'):
                            # This is where the global properties are defined
                            printTS('Processing ' + j)
                            eaEl = createAttributesFromYAMLDictionary(eaRepo,eaPck,eaEl,yaml_dict[i][j])
                elif i == 'properties':
                    printTS('Feature class properties') 
                    # Get or create Thematic Class, delete all existing attributes 	
                    # Uppercase first character in name    
                    strName = file_name[0].upper() + file_name[1:]
                    eaEl = getOrCreateElementByName(eaPck,strName,False,strAlias,strDef,True)
                    # process properties 
                    eaEl = createAttributesFromYAMLDictionary(eaRepo, eaPck, eaEl,yaml_dict[i])

            eaPck.Elements.Refresh()
            #printTS("")


    # -------------------- Diagram -------------------------------------------
    try:
        eDgr = eaPck.Diagrams.GetByName(eaPck.Name)
    except:
        eDgr = None
    if eDgr != None:
        printTS('Found diagram "' + eDgr.Name + '"')
    else:
        eDgr = eaPck.Diagrams.AddNew(eaPck.Name,"")
        eDgr.Update()
        eaPck.Diagrams.Refresh()
        printTS('Created diagram "' + eDgr.Name + '"')
    for eaEl in eaPck.Elements:
        inDiagram = False
        for eDgrObj in eDgr.DiagramObjects:
            if eDgrObj.ElementID == eaEl.ElementID:
                inDiagram = True
        if not inDiagram:  
            eDgrObj = eDgr.DiagramObjects.AddNew("","")
            eDgrObj.ElementID = eaEl.ElementID
            eDgrObj.Update()
            printTS('Added diagramobject "' + eaEl.Name + '"')
        else:
            printTS('Diagramobject already in diagram: "' + eaEl.Name + '"')
    eDgr.Update()

    ePIF = eaRepo.GetProjectInterface()
    ePIF.LayoutDiagramEx(eDgr.DiagramGUID, 4, 4, 20, 20, True)
    eaRepo.CloseDiagram(eDgr.DiagramID)

    printTS("------------- DONE ------------------")


closeEA(eaRepo)