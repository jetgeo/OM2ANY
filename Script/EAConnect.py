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
    printTS('Element definition "' + eaEl.Notes + '"')
    eaEl.Update()
    eaPck.Elements.Refresh()

    if delAttr:
        #Delete all existing attributes
        for idx in range(eaEl.Attributes.Count):
            eaEl.Attributes.DeleteAt(idx,False)
        eaEl.Attributes.Refresh()

    return eaEl


def createAttributesFromYAMLDictionary(eaRepo,eaPck,eaEl,yDict,reqProps=[]):
#Create attributes from a list of properties in a YAML dictionary
    lstReq = reqProps
    pos = eaEl.Attributes.Count + 1
    for key in yDict :
        if key == 'properties':
            # properties under the property type
            for jKey in yDict[key]:
                if jKey == 'required':
                   # List of which of the subsequent properties are required
                   printTS('Required properties: ' + str(yDict[key][jKey]))
                   # Create a list of required properties 
                   lstReq = yDict[key][jKey]
                if jKey == 'properties':
                    eaEl = createAttributesFromYAMLDictionary(eaRepo,eaPck, eaEl,yDict[key][jKey],lstReq)
        else:                    
            # the level is the actual property level
            eaAttr = eaEl.Attributes.AddNew(key,"")
            eaAttr.Visibility = "Public"
            eaAttr.Pos = pos
            # Default cardinality 0..1. May be overruled by minItems and maxItems and list of required properties
            if key in reqProps:
                eaAttr.LowerBound = "1"
            else:        
                eaAttr.LowerBound = "0"
            eaAttr.UpperBound = "1"
            eaAttr.Update()
            pos += 1
            printTS('Added property:"' + eaAttr.Name + '"')

            ## Get type, definition etc    
            eaAttr = convertAttributeProperties(eaRepo,eaPck,eaEl,eaAttr,yDict[key])

            eaEl.Attributes.Refresh()
    return eaEl

def convert2ISOtypes(eaRepo,eaAttr,strType):
#Convert from YAML types to primitive ISO/TC 211 UML types
    guidDT = "0"
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
    # Lookup type element from GUID, add reference
    if guidDT != "0":
        eaDTel = eaRepo.GetElementByGuid(guidDT)
        eaAttr.ClassifierID = eaDTel.ElementID  
    eaAttr.Update()
    return eaAttr     

def convertAttributeProperties(eaRepo,eaPck,eaEl,eaAttr,yDict):
# Convert attribute type, definition etc.  
    lstReq = [] 
    for key in yDict:
        if key == 'type':
            strType = yDict[key]
            printTS('Property type: ' + strType)
            eaAttr.Type = strType
            eaAttr = convert2ISOtypes(eaRepo,eaAttr,strType)

            if strType == "object":
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
                # Default cardinality 0..* for arrays. May be overruled by minItems and maxItems
                eaAttr.LowerBound = "0"
                eaAttr.UpperBound = "*"
        elif key == 'required':
                # List of whith subsequent properties are required
                printTS('Required properties: ' + str(yDict[key]))
                # Create a list of required properties
                lstReq = yDict[key]
        elif key == 'properties':
             eaDTel = createAttributesFromYAMLDictionary(eaRepo,eaPck, eaDTel,yDict[key],lstReq)       
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
            if eaAttr.Type == "Boolean" and eaAttr.Default == "0":
                eaAttr.Default = "false"    
        elif key == 'minItems':
            printTS('Minimum items: ' + str(yDict[key]))    
            eaAttr.LowerBound = yDict[key] 
        elif key == 'maxItems':
            printTS('Maximum items: ' + str(yDict[key]))    
            eaAttr.UpperBound = yDict[key] 
        elif key == 'uniqueItems' and yDict[key] == 'true':
            printTS('Unique items')    
            eaAttr.AllowDuplicates = False
        elif key == 'enum':
            # Enumeration - Create enumeration with values
            strName = eaAttr.Name[0].upper() + eaAttr.Name[1:] + "Enum"
            # Add class name as prefix to enum name, to avoid duplicate subtype enums etc
            # Not for the datatype SpeedType either...
            if eaEl.Name != eaPck.Name + "Defs" and eaEl.Name != 'SpeedType':
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
            strRef = yDict[key].split("/")[-1]
            if not strRef.endswith('Container'):
                strRef += "Type"
            strRef = strRef[0].upper() + strRef[1:]
            printTS('Attributeref: ' + strRef)
            eaAttr.Type = strRef      
        elif key == 'items':
            # items in an array
            for eKey in yDict[key]:
                if eKey == "$ref":
                    # Reference to another property type
                    strRef = yDict[key][eKey].split("/")[-1]
                    if not strRef.endswith('Container'):
                        strRef += "Type"
                    strRef = strRef[0].upper() + strRef[1:]
                    printTS('Attributeref: ' + strRef)
                    eaAttr.Type = strRef
                elif eKey == "type":
                    # Primitive type
                    strType = yDict[key][eKey]
                    printTS('Item property type: ' + strType)
                    eaAttr = convert2ISOtypes(eaRepo,eaAttr,strType)
        elif key == 'prefixItems':
            # prefixItems is an array, where each item is a schema that corresponds to each index of the document's array. 
            # That is, an array where the first element validates the first element of the input array, 
            # the second element validates the second element of the input array, etc.
            # The array has only one occurence, as the multiplicity is within the array
            eaAttr.LowerBound = 0
            eaAttr.UpperBound = 1 
            # Create data type with properties for the array
            strName = eaAttr.Name[0].upper() + eaAttr.Name[1:] + "Type"
            eaDTel = getOrCreateElementByName(eaPck,strName,"DataType", "",False,"",eaAttr.Notes,True)
            # refer the attribute to the data type
            eaAttr.Type = eaDTel.Name
            eaAttr.ClassifierID = eaDTel.ClassifierID            
            
            # Special treatment to get propertys of the speedType
            if eaAttr.Name == "speed":            
                nameDict = {'0':'speedValue', '1':'speedUnit'}
                speedDict = {}
                for index, pDict in enumerate(yDict[key]):
                    strIndex = str(index)
                    pDict.update({'minItems':'1'})
                    #printTS(str(nameDict[strIndex]))
                    speedDict.update({nameDict[strIndex]:pDict })
                eaDTel = createAttributesFromYAMLDictionary(eaRepo,eaPck,eaDTel,speedDict)

            #     eaDTattr.Update()

            #     eaDTel.Attributes.Refresh()           

    eaAttr.Update()        
    return eaAttr
  
def getAttributeTypeFromRef(theAttribute, theRef):



    return theAttribute

# --------- Test code ----------------





