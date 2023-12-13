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
 
def getOrCreateElementByName(eaPck,strName,absCls,strAlias,strDef,delAttr=False):
# Get element by name, or create if not existing
    
    try:
        eaEl = eaPck.Elements.GetByName(strName)
    except:    
        eaEl = None
    if eaEl != None:
        printTS('Existing Element "' + eaEl.Name + '"')
    else:    
        eaEl = eaPck.Elements.AddNew(strName, "Class" )
        printTS('Added Element "' + eaEl.Name + '"')
    eaEl.Stereotype = "FeatureType"
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

def createAttributesFromYAMLDictionary(eaRepo,eaPck,eaEl,dict):
#Create attributes from a list of properties in a YAML dictionary
    pos = eaEl.Attributes.Count + 1
    for key in dict :
        if key == 'properties':
            for jKey in dict[key]:
                if jKey == 'properties':
                    eaEl = createAttributesFromYAMLDictionary(eaRepo,eaPck, eaEl,dict[key][jKey])
        else:                    
            eaAttr = eaEl.Attributes.AddNew(key,"")
            eaAttr.Visibility = "Public"
            eaAttr.Pos = pos
            eaAttr.Update()
            pos += 1
            printTS('Added property:"' + eaAttr.Name + '"')

            ## Get type, definition etc    
            eaAttr = convertAttributeProperties(eaRepo,eaPck,eaEl,eaAttr,dict[key])

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
            elif strType == "object":
                # object. Create data type
                strName = eaAttr.Name[0].upper() + eaAttr.Name[1:] + "Type"
                try:
                    eaDTel = eaPck.Elements.GetByName(strName)
                except:    
                    eaDTel = None
                if eaDTel != None:
                    printTS('Existing data type "' + eaDTel.Name + '"')
                    #Delete all existing data type attributes
                    # for idx in range(eaDTel.Attributes.Count):
                    #     eaDTel.Attributes.DeleteAt(idx,False)
                    #     eaDTel.Attributes.Refresh()
                else:    
                    eaDTel = eaPck.Elements.AddNew(strName, "DataType") 
                    printTS("Create data type: " + eaDTel.Name)  
                eaDTel.Notes = eaAttr.Notes 
                eaDTel.Update()

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
        elif key == 'description':
            printTS('Definition: ' + yDict[key])    
            eaAttr.Notes = yDict[key]
        elif key == 'default':
            printTS('Default value: ' + str(yDict[key]))
            if (isinstance(yDict[key],list) or isinstance(yDict[key],dict)) and len(yDict[key]) != 0:
                eaAttr.Default = yDict[key][0]
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
            if eaEl.Name != eaPck.Name + "Defs":
                strName = eaEl.Name + strName
            try:
                eaDTel = eaPck.Elements.GetByName(strName)
            except:    
                eaDTel = None
            if eaDTel != None:
                printTS('Existing Enumeration "' + eaDTel.Name + '"')
                #Delete all existing enumeration values
                for idx in range(eaDTel.Attributes.Count):
                    eaDTel.Attributes.DeleteAt(idx,False)
                eaDTel.Attributes.Refresh()                
            else:    
                eaDTel = eaPck.Elements.AddNew(strName, "Enumeration") 
                printTS("Create enumeration: " + eaDTel.Name)  
            eaDTel.Notes = eaAttr.Notes 
            eaDTel.Update()
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
									
    eaAttr.Update()        
    return eaAttr
  


# --------- Test code ----------------





