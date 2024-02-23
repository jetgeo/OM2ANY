from Parameters import *
from EAConnect import *
import sys, os, re, yaml, json


# -------------------------------------------------------------------------------------
# Open EA Repository and find OM Model
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

# -------------------------------------------------------------------------------------
# Create a regular expression to match files with yaml extension
yaml_pattern = re.compile(r".+\.yaml$")
omMod.Packages.Refresh()

# -------------------------------------------------------------------------------------
# Walk through folders and files
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
          # Skip the main schema.yaml file (not relevant for the conversion)
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
            strAlias = ""
            lstReq = []
            #Start processing schema
            for i in yaml_dict:
                if i == 'title':
                    strAlias = yaml_dict[i]
                    printTS('Title: ' + strAlias)
                elif i == 'description':
                    strDef = yaml_dict[i]
                    printTS('Description: ' + strDef)
                elif i == 'required':
                   # List of which of the subsequent properties are required
                   printTS('Required properties: ' + str(yaml_dict[i]))
                   # Create a list of required properties 
                   lstReq = yaml_dict[i]
                elif i == '$defs':
			        # Definition statements
                    printTS('Global properties')
                    # Get or create Defs Class, delete all existing attributes 
                    for j in yaml_dict[i]:
                        if (j == 'propertyDefinitions') :
                            strName = eaPck.Name + "Defs"
                            if file != 'defs.yaml':
                                strAlias = ""
                            eaEl = getOrCreateElementByName(eaPck,strName,"Class", "featureType",True, strAlias,strDef,True)
                            # This is where the global properties are defined
                            printTS('Processing global properties')
                            eaEl = createAttributesFromYAMLDictionary(eaRepo,eaPck,eaEl,yaml_dict[i][j])
                        elif j == 'propertyContainers':
                            printTS('Processing property containers')
                            for pC in yaml_dict[i][j]:
                                strName = pC[0].upper() + pC[1:]
                                strAlias = ""
                                strDef = ""
                                lstReq = []
                                for p in yaml_dict[i][j][pC]:
                                    if p == 'title':
                                        strAlias = yaml_dict[i][j][pC][p]
                                        printTS('Title: ' + strAlias)
                                    elif p == 'description':
                                        strDef = yaml_dict[i][j][pC][p]
                                        printTS('Description: ' + strDef)
                                    elif p == 'required':
                                        # List of which of the subsequent properties are required
                                        printTS('Required properties: ' + str(yaml_dict[i][j][pC][p]))
                                        # Create a list of required properties 
                                        lstReq = yaml_dict[i][j][pC][p]
                                    elif p == 'properties':
                                        eaEl = getOrCreateElementByName(eaPck,strName,"DataType", "",False,strAlias,strDef,True)
                                        eaEl = createAttributesFromYAMLDictionary(eaRepo,eaPck,eaEl,yaml_dict[i][j][pC][p],lstReq)
                                    elif p == 'items':  
                                        # Content is an array 
                                        printTS('Container with array only: ' + strName)
                                        eaEl = getOrCreateElementByName(eaPck,strName,"DataType", "",False,strAlias,strDef,True)
                                        # Create data type for the array item
                                        strItemDT = strName.replace("Container", "Type")
                                        strDef = ""
                                        lstReq = []
                                        delAttr = True 
                                        for pi in yaml_dict[i][j][pC][p]: 
                                            if pi == 'description':
                                                strDef = yaml_dict[i][j][pC][p][pi]
                                                printTS('Item description: ' + strDef)
                                            elif pi == 'required':
                                                # List of which of the subsequent properties are required
                                                printTS('Required item properties: ' + str(yaml_dict[i][j][pC][p][pi]))
                                                # Create a list of required properties 
                                                lstReq = yaml_dict[i][j][pC][pi]
                                            elif pi == 'properties' or pi == 'allOf':
                                                eaDTEl = getOrCreateElementByName(eaPck,strItemDT,"DataType", "",False,strAlias,strDef,delAttr)
                                                if delAttr:
                                                    # Create property type for the array item
                                                    strAName = pC.replace("Container", "Item") 
                                                    eaAttr = eaEl.Attributes.AddNew(strAName,"")
                                                    eaAttr.Visibility = "Public"
                                                    # Default cardinality 1..*. May be overruled by minItems and maxItems
                                                    eaAttr.LowerBound = "1"
                                                    eaAttr.UpperBound = "*"
                                                    eaAttr.Type = strItemDT
                                                    eaAttr.ClassifierID = eaDTEl.ElementID
                                                    eaAttr.Update()
                                                    printTS('Added item property:"' + eaAttr.Name + '"')
                                                    delAttr = False #Delete attributes only for the first of properties or anyOf
                                                # Add property types for the array item data type
                                                if pi == 'allOf':
                                                    lb = 1 #Lower bound = 1
                                                else:
                                                    lb = 0    
                                                eaEl = createAttributesFromYAMLDictionary(eaRepo,eaPck,eaDTEl,yaml_dict[i][j][pC][p][pi],lstReq,lb)

                elif i == 'properties':
                    printTS('Feature class properties') 
                    # Get or create Thematic Class, delete all existing attributes 	
                    # Uppercase first character in name    
                    strName = file_name[0].upper() + file_name[1:]
                    eaEl = getOrCreateElementByName(eaPck,strName,"Class", "featureType",False,strAlias,strDef,True)
                    # process properties 
                    eaEl = createAttributesFromYAMLDictionary(eaRepo, eaPck, eaEl,yaml_dict[i],lstReq)
                # TODO: Handling allOff (e.g. Segment.AccessContainer), oneOf (e.g. Segment.modesContainer and AccessContainer)...
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

# ---------------------------------------------------------------------------------------------------------------------
# Cleanup for the complete model

# Find all uses of data types and enumerations, and set correct type name and ClassifierID
printTS('Use of enumerations and datatypes everywhere...')
for eaDTpck in omMod.Packages:
    for eaDTel in eaDTpck.Elements:
        if eaDTel.Type == "Enumeration" or eaDTel.Type == "DataType":
            # Enumeration or DataType found, searching for use
            printTS(eaDTel.Type + ": " + eaDTel.Name)
            for eaPck in omMod.Packages:
                for eaEl in eaPck.Elements:
                    for eaAttr in eaEl.Attributes:
                        if eaAttr.Type == eaDTel.Name:
                            eaAttr.Type = eaDTel.Name
                            eaAttr.ClassifierID = eaDTel.ElementID
                            eaAttr.Update()
                            printTS('Attribute: "' + eaEl.Name + '.' + eaAttr.Name + ' (' + eaAttr.Type + ')')
                    eaEl.Attributes.Refresh()        


# Fix attribute type and ClassifierID for attributes that are still missing ClassifierID due to wrong use of "Type"
# If there exists another attribute in a Defs class with the Type name, without "Type" --> use the same Type as that one. 
printTS('Fix missing ClassifierIDs...')
for eaPck in omMod.Packages:
    for eaEl in eaPck.Elements:
        if eaEl.Type == "Class" or eaEl.Type == "DataType":
            # Class or DataType found, controlling attributes
            # printTS(eaEl.Type + ": " + eaEl.Name)
            for eaAttr in eaEl.Attributes:
                if eaAttr.ClassifierID == 0 and eaAttr.Type != "" and eaAttr.Type[-4:] == "Type":
                    printTS('Attribute: "' + eaEl.Name + '.' + eaAttr.Name + ' (' + eaAttr.Type + ')')
                    strType = eaAttr.Type[0].lower() + eaAttr.Type[1:-4]
                    for eaDTpck in omMod.Packages:
                        for eaDTel in eaDTpck.Elements:
                            if eaDTel.Name[-4:] == "Defs":
                                for eaDTattr in eaDTel.Attributes:
                                    if eaDTattr.Name ==strType:
                                        printTS('Referenced attribute found: "' + eaDTel.Name + '.' + eaDTattr.Name + ' (' + eaDTattr.Type + ')')
                                        # Copy type and Classifier
                                        eaAttr.Type = eaDTattr.Type
                                        eaAttr.ClassifierID = eaDTattr.ClassifierID
                                        # Copy cardinality if default
                                        if eaAttr.LowerBound == "0":
                                            eaAttr.LowerBound = eaDTattr.LowerBound
                                        if eaAttr.UpperBound == "1":
                                            eaAttr.UpperBound = eaDTattr.UpperBound
                                        # Copy definition if not set    
                                        if eaAttr.Notes == "":
                                            eaAttr.Notes = eaDTattr.Notes
                                        eaAttr.Update()
            eaEl.Attributes.Refresh()  



printTS("------------- DONE ------------------")


# closeEA(eaRepo)