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
for eaPck in omMod.Packages:
    #Delete all existing elements
    printTS('Deleting all elements in package ' + eaPck.Name)
    for idx in range(eaPck.Elements.Count):
        eaPck.Elements.DeleteAt(idx,False)
    eaPck.Elements.Refresh()


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
        #Set to first position

    for file in files:
        # Get the full path of the file
        file_path = os.path.join(folder, file)
        # Check if the file matches the yaml pattern
        if yaml_pattern.match(file_path):
          printTS('File: '+ file_path)
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
                        if (j == 'propertyDefinitions') or  (j == 'typeDefinitions') :
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
                                printTS('Name: ' + strName)
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
                                    elif p == 'oneOf':
                                        eaEl = getOrCreateElementByName(eaPck,strName,"DataType", "",False,strAlias,strDef,True)
                                        # Create attribute"
                                        strAName = pC.replace("Container", "") 
                                        eaAttr = eaEl.Attributes.AddNew(strAName,"")
                                        eaAttr.Visibility = "Public"
                                        # Default cardinality 0..1. May be overruled by minItems and maxItems and list of required properties
                                        eaAttr.LowerBound = "0"
                                        eaAttr.UpperBound = "1"
                                        eaAttr.Update()
                                        printTS('Added property:"' + eaAttr.Name + '"')
                                        # Run "oneOf" process as for any other property
                                        eaAttr = convertAttributeProperties(eaRepo,eaPck,eaEl,eaAttr,yaml_dict[i][j][pC])
                                        # Process the dictionary (different structure )
                                        # oneOfDict = yaml_dict[i][j][pC][p]
                                    elif p == 'items':  
                                        # Content is an array. Needs special treatment...
                                        printTS('Container with array only: ' + strName)
                                        eaEl = getOrCreateElementByName(eaPck,strName,"DataType", "",False,strAlias,strDef,True)
                                        strItemDT = strName.replace("Container", "Type")
                                        strDef = ""
                                        strOCL = ""
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
                                                lstReq = yaml_dict[i][j][pC][p][pi]
                                            elif pi == 'anyOf':
                                                # Create constraint in the data type for the array
                                                strOCL = 'inv:' #'context ' + eaEl.Name + ' inv:'
                                                for req in yaml_dict[i][j][pC][p][pi]:
                                                    if type(req) == dict:
                                                        for reqP in req:
                                                            if reqP == 'required':
                                                                for reqI in req[reqP]:
                                                                    strOCL += ' self.' + str(reqI) + '->notEmpty()' 
                                                    strOCL += ' or'            
                                                strOCL = strOCL.rstrip(' or')
                                            elif pi == 'properties' or pi == 'allOf' or pi == 'oneOf':
                                                if delAttr:
                                                    # Create property type for the array item
                                                    strAName = pC.replace("Container", "") 
                                                    eaAttr = eaEl.Attributes.AddNew(strAName,"")
                                                    eaAttr.Visibility = "Public"
                                                    eaAttr.UpperBound = "*"
                                                    eaAttr.Update()
                                                    printTS('Added item property:"' + eaAttr.Name + '"')
                                                if pi == 'allOf':
                                                    lb = 1 #Lower bound = 1
                                                else:
                                                    lb = 0    
                                                if pi == 'properties' or pi == 'allOf':
                                                    eaDTEl = getOrCreateElementByName(eaPck,strItemDT,"DataType", "",False,strAlias,strDef,delAttr)
                                                    if delAttr:
                                                        eaAttr.Type = strItemDT
                                                        eaAttr.ClassifierID = eaDTEl.ElementID
                                                        eaAttr.Update()
                                                        if strOCL != "":
                                                            eaConstraint = eaDTEl.Constraints.AddNew(strOCL,'OCL')
                                                            eaConstraint.Update()
                                                    # Add attributes for the data type
                                                    eaEl = createAttributesFromYAMLDictionary(eaRepo,eaPck,eaDTEl,yaml_dict[i][j][pC][p][pi],lstReq,lb)
                                                elif pi == 'oneOf':
                                                    # Run "oneOf" process as for any other property
                                                    eaAttr = convertAttributeProperties(eaRepo,eaPck,eaEl,eaAttr,yaml_dict[i][j][pC][p])
                                                delAttr = False #Delete attributes only for the first of properties or anyOf                                                # TODO: oneOf -> one level higher. Important to have the oneOf statement


                elif i == 'properties':
                    printTS('Feature class properties') 
                    # Get or create Thematic Class, delete all existing attributes 	
                    # Uppercase first character in name    
                    strName = file_name[0].upper() + file_name[1:]
                    eaEl = getOrCreateElementByName(eaPck,strName,"Class", "featureType",False,strAlias,strDef,True)
                    # process properties 
                    eaEl = createAttributesFromYAMLDictionary(eaRepo, eaPck, eaEl,yaml_dict[i],lstReq)
                # TODO: Handling oneOf (e.g. Segment.modesContainer and AccessContainer)...
            eaPck.Elements.Refresh()
            #printTS("")


# ---------------------------------------------------------------------------------------------------------------------
# Cleanup for the complete model
# Common package in first position
omCommonPck.TreePos = 0
omCommonPck.Update()
eaRepo.RefreshModelView (omMod.PackageID)
omMod.Packages.Refresh()


# "Def" elements in the first position within each package
for eaPck in omMod.Packages:
    for eaEl in eaPck.Elements:
        if eaEl.Name.endswith('Defs') and eaEl.Stereotype.upper() == 'FEATURETYPE':
            eaEl.TreePos = 0
        elif eaEl.Stereotype.upper() == 'FEATURETYPE':
            eaEl.TreePos = 1    
        eaEl.Update()
    eaRepo.RefreshModelView (eaPck.PackageID)
    eaPck.Elements.Refresh()

eaRepo.RefreshModelView (eaMod.PackageID)
for eaPck in omMod.Packages:
    printTS(str(eaPck.TreePos) + ": " + eaPck.Name)
    for eaEl in eaPck.Elements:
        if eaEl.Stereotype.upper() == 'FEATURETYPE':
            printTS(str(eaEl.TreePos) + ": " + eaEl.Name)


# Find all uses of data types and enumerations, and set correct type name and ClassifierID
printTS('Use of enumerations and datatypes everywhere...')
for eaDTpck in omMod.Packages:
    for eaDTel in eaDTpck.Elements:
        if eaDTel.Type == "Enumeration" or eaDTel.Type == "DataType":
            # Enumeration or DataType found, searching for use
            printTS(eaDTel.Type + ": " + eaDTel.Name)
            for eaPck in omMod.Packages:
                for eaEl in eaPck.Elements:
                    #For enumerations: Check if it is used in a constraint, with "Type" instead of "Enum"
                    for eaConstraint in eaEl.Constraints:
                        if eaDTel.Type == "Enumeration" and eaDTel.Name[0:-4] in eaConstraint.Name:
                            eaConstraint.Name = eaConstraint.Name.replace(eaDTel.Name[0:-4] + 'Type', eaDTel.Name[0:-4] + 'Enum')
                            eaConstraint.Update()

                    #Check if the type name matches the element name (minus the four last characters, that can be 'Type' og 'Enum')
                    for eaAttr in eaEl.Attributes:
                        if eaAttr.Type[0:-4] == eaDTel.Name[0:-4]:
                            eaAttr.Type = eaDTel.Name
                            eaAttr.ClassifierID = eaDTel.ElementID
                            eaAttr.Update()
                            printTS('Attribute: "' + eaEl.Name + '.' + eaAttr.Name + ' (' + eaAttr.Type + ')')
                            # Copy definition if not set    
                            if eaAttr.Notes == "":
                                eaAttr.Notes = eaDTel.Notes
                            eaAttr.Update()
                            eaEl.Attributes.Refresh()    
# Fix "ref" datatypes
printTS('Fix "ref" datatypes...')
for eaPck in omMod.Packages:
    for eaEl in eaPck.Elements:
        if eaEl.Type == "Class" or eaEl.Type == "DataType":
            # Class or DataType found, controlling attributes
            printTS(eaEl.Type + ": " + eaEl.Name)
            for eaAttr in eaEl.Attributes:
                if eaAttr.Type.startswith("ref:"):
                    strRef = eaAttr.Type
                    strType = strRef.split("/")[-1].removesuffix('.json')
                    eaAttr.Type = strType
                    if "propertyDefinitions" in strRef or "typeDefinitions" in strRef:
                        if strRef.startswith("ref:../defs.yaml"):
                            printTS('Common package propertyDefinition: ' + strType)  
                            try:
                                eaDTEl = omCommonPck.Elements.GetByName('CommonDefs')
                            except:    
                                eaDTEl = None                                
                        elif strRef.startswith("ref:./defs.yaml") or strRef.startswith("ref:#/$defs/"):
                            printTS('Local package (' + eaPck.Name + ') propertyDefinition: ' + strType) 
                            try:
                                eaDTEl = eaPck.Elements.GetByName(eaPck.Name + 'Defs')
                            except:    
                                eaDTEl = None  
                        if not eaDTEl == None:         
                            # Search for the attribute and copy Type, ClassifierID and notes                                                              
                            for eaDTAttr in eaDTEl.Attributes:
                                if eaDTAttr.Name == strType:
                                    eaAttr.ClassifierID = eaDTAttr.ClassifierID
                                    eaAttr.Type = eaDTAttr.Type 
                                    printTS('Found ' + eaDTAttr.Name)
                                    # Copy definition if not set    
                                    if eaAttr.Notes == "":
                                        eaAttr.Notes = eaDTAttr.Notes
                                    # Special treatment of linearlyReferencedRange to get the correct multiplicity
                                    if "linearlyReferencedRange" in strRef:
                                        eaAttr.LowerBound = eaDTAttr.LowerBound
                                        eaAttr.UpperBound = eaDTAttr.UpperBound
                        if eaAttr.ClassifierID == 0:
                            printTS('Referenced type not found!') 
                    elif "propertyContainers" in strRef or "shapeContainer" in strRef:
                        if strRef.startswith("ref:../defs.yaml"):                        
                            printTS('Common package propertyContainer: '+ strType) 
                            try:
                                eaDTEl = omCommonPck.Elements.GetByName(strType[0].upper() + strType[1:])
                            except:    
                                eaDTEl = None   
                        elif strRef.startswith("ref:./defs.yaml") or strRef.startswith("ref:#/$defs/"):
                            printTS('Local package (' + eaPck.Name + ') propertyContainer: ' + strType) 
                            try:
                                eaDTEl = eaPck.Elements.GetByName(strType[0].upper() + strType[1:])
                            except:    
                                eaDTEl = None                                 
                        if not eaDTEl == None:    
                            eaAttr.ClassifierID = eaDTEl.ElementID
                            printTS('Found ' + eaDTEl.Name)
                            # Copy definition if not set    
                            if eaAttr.Notes == "":
                                eaAttr.Notes = eaDTEl.Notes                                                    
                        if eaAttr.ClassifierID == 0:
                            printTS('Referenced type not found!') 
                    elif strRef.startswith("ref:https://geojson.org"):
                        printTS('GeoJSON type: ' + strType)
                    else:
                        printTS("other type: " + strType)
                    eaAttr.Update()


#TODO: Find out why the "when" attribute under lanes, prohibited_transitions, speedLimitsContainer,  accessContainer
# is not handled. 

# Fix attribute type and ClassifierID for attributes that are still missing ClassifierID due to wrong use of "Type"
# If there exists another attribute in a Defs class with the Type name, without "Type" --> use the same Type as that one. 
printTS('Fix missing data types and ClassifierIDs...')
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

#Remove attributes with data type "*Container" and copy all attributes from the Container Data Type
printTS('Fix Container types...')
for eaPck in omMod.Packages:
    for eaEl in eaPck.Elements:
        if eaEl.Type == "Class" or eaEl.Type == "DataType":
            pos = 0
            sorted_list = []
            for idx in range(eaEl.Attributes.Count):
                eaAttr = eaEl.Attributes.GetAt(idx)
                if not eaAttr.Type.endswith('Container'):
                   # Set position, taking into account the new attributes from the Container
                   pos += 1
                   eaAttr.Pos = pos
                   eaAttr.Update() 
                   printTS(str(eaAttr.Name) + ' New position: ' + str(pos))
                else:
                    printTS('Copy attributes from container type: ' + eaAttr.Type)
                    # get datatype element by ClassifierID
                    try:
                        eaDTel = eaRepo.GetElementByID(eaAttr.ClassifierID)
                        # copy all attributes from datatype, starting pos = eaAttr.pos
                        for eaDTAttr in eaDTel.Attributes:
                            pos += 1
                            newAttr = eaEl.Attributes.AddNew(eaDTAttr.Name,"")
                            newAttr.Type = eaDTAttr.Type
                            newAttr.ClassifierID = eaDTAttr.ClassifierID
                            newAttr.Notes = eaDTAttr.Notes
                            newAttr.LowerBound = eaDTAttr.LowerBound
                            newAttr.UpperBound = eaDTAttr.UpperBound
                            newAttr.Default = eaDTAttr.Default
                            newAttr.Pos = pos
                            newAttr.Update()
                            printTS(str(newAttr.Name) + ' Position: ' + str(pos))
                        for eaConstraint in eaDTel.Constraints:
                            # Copy constraints from the container
                            newConstraint = eaEl.Constraints.AddNew(eaConstraint.Name, 'OCL')
                            newConstraint.Update()
                        # Delete original attribute
                        eaEl.Attributes.DeleteAt(idx,False)     
                    except Exception as e:
                        printTS(f"An exception occurred: {type(e).__name__} - {e}")                  
            eaEl.Attributes.Refresh()

# Remove unecessary prefixes in Enumeration and Data type names
printTS('Remove unecessary prefixes...')
lstNames = []
#Build list of names
for eaPck in omMod.Packages:
    for eaEl in eaPck.Elements:  
        if eaEl.Type == 'Enumeration' or eaEl.Type == 'DataType':  
            lstNames.append(eaEl.Name)

#Find enumerations and datatypes that starts with the name of another class or datatype
lstPrefix = []        
for eaPck in omMod.Packages:
    for eaEl in eaPck.Elements:    
        if eaEl.Type == 'Class' or eaEl.Type == 'DataType':
            matching_items = [item for item in lstNames if item.startswith(eaEl.Name) and not item.startswith(eaEl.Name + "_") and item != eaEl.Name]
            if len(matching_items) > 0:
                #Found matching items. Check if they will be unique without the prefix
                printTS('')
                printTS('--- Items with prefix ' + str(eaEl.Name) + '---')
                printTS(matching_items)
                for strName in matching_items:
                    strName = strName.removeprefix(eaEl.Name)

                    # build list of items that ends with the same name
                    matching_item_parts = [subItem for subItem in lstNames if subItem.endswith(strName)]
                    if len(matching_item_parts) > 1:
                        printTS('Other elements that end with' + strName)                        
                        printTS(matching_item_parts)
                    elif strName.startswith('Use'):
                        #TODO: Fix LandUse...
                        printTS('LandUse - need to fix somehow...')    
                    else:
                        printTS(eaEl.Name + strName + ' is unique without prefix, removing prefix!')    
                        eaDTel = eaPck.Elements.GetByName(eaEl.Name + strName)
                        eaDTel.Name = strName
                        eaDTel.Update()

# -------------------- Diagram -------------------------------------------
printTS('Creating diagrams...')
for eaPck in omMod.Packages:
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
    
    #Remove all all elements and add again, for autosizing
    for idx in range(eDgr.DiagramObjects.Count):
        eDgr.DiagramObjects.DeleteAt(idx,False)
    eDgr.DiagramObjects.Refresh()        
    for eaEl in eaPck.Elements:
        eDgrObj = eDgr.DiagramObjects.AddNew("","")
        eDgrObj.ElementID = eaEl.ElementID
        # Make sure constraints are shown in all elements
        eDgrObj.ElementDisplayMode = 1
        eDgrObj.ShowConstraints = True
        eDgrObj.fontName = "Calibri"
        eDgrObj.Update()
        printTS('Added diagramobject "' + eaEl.Name + '"')

    eDgr.Update()
    ePIF = eaRepo.GetProjectInterface()
    ePIF.LayoutDiagramEx(eDgr.DiagramGUID, 4, 4, 20, 20, True)
    eaRepo.CloseDiagram(eDgr.DiagramID)

printTS("------------- DONE ------------------")


# closeEA(eaRepo)