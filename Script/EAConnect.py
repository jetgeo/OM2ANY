import win32com.client as win32
from datetime import datetime
from Parameters import *

def printTS(message):
    # Print a message with a timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Print the message with the timestamp
    print(timestamp, " ", message)

def openEAapp():
    #Open EA 
    printTS('Hi EA - are you there? ')
    eaApp = win32.gencache.EnsureDispatch('EA.App')
    printTS('I am here')
    return eaApp

def openEArepo(eaApp,repo_path):
    #Open the EA Repository
    eaRepo = eaApp.Repository
    printTS('Hi EA - Please open this repository: ' + repo_path )
    # Open the repository
    try: 
        eaRepo.SuppressSecurityDialog = True
        eaRepo.OpenFile2(repo_path,"","")
        printTS("OK! Repository " + repo_path + " is ready!")
        return eaRepo
    except Exception as e:
        printTS(e)

def closeEA(eaRepo):
    # Close the repository and exit EA
    eaRepo.CloseFile()
    eaRepo.Exit()   
    printTS('Repository closed!')
 
def getOrCreateElementByName(eaPck,strName,elType, stType, absCls,strAlias,strDef,delAttr=False):
# Get element by name, or create if not existing
    
    try:
        eaEl = eaPck.Elements.GetByName(strName)
    except:    
        eaEl = None
    if eaEl != None:
        printTS('Existing Element "' + eaEl.Name + '"')
    else:    
        eaEl = eaPck.Elements.AddNew(strName, elType )
        printTS('Added Element "' + eaEl.Name + '"')
    eaEl.Stereotype = stType
    eaEl.Abstract = absCls
    eaEl.Alias = strAlias
    eaEl.Notes = strDef
    eaEl.Update()
    eaPck.Elements.Refresh()

    if delAttr:
        #Delete all existing attributes
        for idx in range(eaEl.Attributes.Count):
            eaEl.Attributes.DeleteAt(idx,False)
        eaEl.Attributes.Refresh()

    return eaEl

def createAttributesFromYAMLDictionary(eaRepo,eaPck,eaEl,yDict):
#Create attributes from a list of properties in a YAML dictionary
    pos = eaEl.Attributes.Count + 1
    for key in yDict :
        if key == 'properties':
            for jKey in yDict[key]:
                if jKey == 'properties':
                    eaEl = createAttributesFromYAMLDictionary(eaRepo,eaPck, eaEl,yDict[key][jKey])
        else:                    
            eaAttr = eaEl.Attributes.AddNew(key,"")
            eaAttr.Visibility = "Public"
            eaAttr.Pos = pos
            eaAttr.Update()
            pos += 1
            printTS('Added property:"' + eaAttr.Name + '"')

            ## Get type, definition etc    
            eaAttr = convertAttributeProperties(eaRepo,eaPck,eaEl,eaAttr,yDict[key])

            eaEl.Attributes.Refresh()
    return eaEl

def convertAttributeProperties(eaRepo,eaPck,eaEl,eaAttr,yDict):
# Convert attribute type, definition etc.   
    for key in yDict:
        if key == 'type':
            guidDT = "0"
            printTS('Property type: ' + yDict[key])
            strType = yDict[key]
            if strType == "string":
                eaAttr.Type = "CharacterString"
                guidDT = guidCharacterString
            elif strType == "integer":
                eaAttr.Type = "Integer"
                guidDT = guidInteger
            elif strType == "number":
                eaAttr.Type = "Real"
                guidDT = guidReal
            elif strType == "boolean":
                eaAttr.Type = "Boolean"
                guidDT = guidBoolean
            elif strType == "object":
                # object. Create (or get) data type
                strName = eaAttr.Name[0].upper() + eaAttr.Name[1:] + "Type"
                eaDTel = getOrCreateElementByName(eaPck,strName,"DataType", "",False,"",eaAttr.Notes,True)
                eaPck.Elements.Refresh()
                eaAttr.Type = eaDTel.Name
                eaAttr.ClassifierID = eaDTel.ClassifierID

                # TODO: Add data type attributes... if 'properties
            elif strType == "array":
                # array: 	Set datatype array first, then change from item value (last part if id + Type)
                # Works for types that are object, not for linearPos, which is fixed at the end
                eaAttr.Type = "Array"
            else:
                eaAttr.Type = strType
            # Lookup type element from GUID, add reference
            if guidDT != "0":
                eaDTel = eaRepo.GetElementByGuid(guidDT)
                eaAttr.ClassifierID = eaDTel.ElementID
        elif key == 'properties':
             eaDTel = createAttributesFromYAMLDictionary(eaRepo,eaPck, eaDTel,yDict[key])       
        elif key == 'description':
            printTS('Definition: ' + yDict[key])    
            eaAttr.Notes = yDict[key]
        elif key == 'default':
            printTS('Default value: ' + str(yDict[key]))
            if (isinstance(yDict[key],list) or isinstance(yDict[key],dict)) and len(yDict[key]) != 0:
                try:
                    eaAttr.Default = yDict[key][0]
                except:
                    for nKey in yDict[key]:
                        eaAttr.Default = yDict[key][nKey][0]
            elif not isinstance(yDict[key],list) and not isinstance(yDict[key],dict):    
                eaAttr.Default = yDict[key] 
        elif key == 'minItems':
            printTS('Minimum items: ' + str(yDict[key]))    
            eaAttr.LowerBound = yDict[key] 
            eaAttr.UpperBound = "*"
        elif key == 'maxItems':
            printTS('Maximum items: ' + str(yDict[key]))    
            eaAttr.UpperBound = yDict[key] 
        elif key == 'uniqueItems' and yDict[key] == 'true':
            printTS('Unique items')    
            eaAttr.AllowDuplicates = False
        elif key == 'enum':
            # Enumeration - Create enumeration with values
            strName = eaAttr.Name[0].upper() + eaAttr.Name[1:] + "Type"
            # Add class name as prefix to enum name, to avoid duplicate subtype enums etc
            if eaEl.Name != eaPck.Name + "Defs":
                strName = eaEl.Name + strName
            eaDTel = getOrCreateElementByName(eaPck,strName,"Enumeration", "",False,"",eaAttr.Notes,True)
            eaPck.Elements.Refresh()
            eaAttr.Type = eaDTel.Name
            eaAttr.ClassifierID = eaDTel.ClassifierID
			# Enumeration values
            for eKey in yDict[key]:
                if (isinstance(yDict[key],list) or isinstance(yDict[key],dict)) and len(yDict[key]) != 0:
                    eaDTattr = eaDTel.Attributes.AddNew([eKey][0],"")
                elif not isinstance(yDict[key],list) and not isinstance(yDict[key],dict):    
                    eaDTattr = eaDTel.Attributes.AddNew([eKey],"")
                eaDTattr.Update()
                printTS("Enumeration value: " + eaDTattr.Name)	
                eaDTel.Attributes.Refresh()
        elif key == '$ref':
            strRef = yDict[key].split("/")[-1] + "Type"
            strRef = strRef[0].upper() + strRef[1:]
            printTS('Attributeref: ' + strRef)
            eaAttr.Type = strRef      
        elif key == 'items':
            for eKey in yDict[key]:
                if eKey == "$ref":
                    strRef = yDict[key][eKey].split("/")[-1] + "Type"
                    strRef = strRef[0].upper() + strRef[1:]
                    printTS('Attributeref: ' + strRef)
                    eaAttr.Type = strRef
            #     eaDTattr.Update()

            #     eaDTel.Attributes.Refresh()           


    eaAttr.Update()        
    return eaAttr
  
def getAttributeTypeFromRef(theAttribute, theRef):



    return theAttribute

# --------- Test code ----------------





