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
    # On error: Remove "C:\Users\JETKNU\AppData\Local\Temp\gen_py"
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
        #Delete all existing constraints
        for idx in range(eaEl.Constraints.Count):
            eaEl.Constraints.DeleteAt(idx,False)
        eaEl.Constraints.Refresh()


    return eaEl


def createAttributesFromYAMLDictionary(eaRepo,eaPck,eaEl,yDict,reqProps=[],lb=0):
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
                elif jKey == 'properties':
                    eaEl = createAttributesFromYAMLDictionary(eaRepo,eaPck, eaEl,yDict[key][jKey],lstReq)
                elif jKey == 'allOf':
                    eaEl = createAttributesFromYAMLDictionary(eaRepo,eaPck, eaEl,yDict[key][jKey],lstReq,1)

        else:
            if type(key) == dict:
                printTS(str(key) + ' is a dictionary')
                # create attribute name from ref
                strName = ''
                cp = False
                for eKey in key:
                    if eKey == '$ref':
                        strName = key[eKey].split("/")[-1].replace("Container", "")
                    elif eKey == 'title' and key[eKey] == "Conditional Properties":
                        printTS("Conditional Properties")
                        cp = True
                    elif cp and eKey == 'if':
                        #TODO: Loop and create constraint
                        printTS("If statement: " )    
                        printTS(key[eKey])

                    elif cp and eKey == 'then':
                        # Loop and create conditional properties 
                        printTS("then statement") 
                        for pKey in key[eKey]:
                            if pKey == 'properties':
                                eaEl = createAttributesFromYAMLDictionary(eaRepo,eaPck, eaEl,key[eKey][pKey],[])
            else:
                strName = key
            if strName != '':         
                eaAttr = eaEl.Attributes.AddNew(strName,"")
                eaAttr.Visibility = "Public"
                eaAttr.Pos = eaEl.Attributes.Count + 1 #pos
                # Default cardinality 0..1. May be overruled by minItems and maxItems and list of required properties
                if key in reqProps:
                    eaAttr.LowerBound = "1"
                else:        
                    eaAttr.LowerBound = lb
                eaAttr.UpperBound = "1"
                eaAttr.Update()
                pos += 1
                printTS('Added property:"' + eaAttr.Name + '"')

                ## Get type, definition etc    
                if type(key) == dict:
                    eaAttr = convertAttributeProperties(eaRepo,eaPck,eaEl,eaAttr,key)       
                else:
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

def convertAttributeProperties(eaRepo,eaPck,eaEl,eaAttr,yDict,delAttr=True):
# Convert attribute type, definition etc.  
    lstReq = [] 
    strType = ''
    for key in yDict:
        if key == 'type':
            strType = yDict[key]
            printTS('Property type: ' + strType)
            eaAttr.Type = strType
            if strType != "object" and strType != "array":
                eaAttr = convert2ISOtypes(eaRepo,eaAttr,strType)
            elif strType == "object":
                # object. Create (or get) data type
                strName = eaAttr.Name[0].upper() + eaAttr.Name[1:] + "Type"
                # Speciality for restrictions (two different types - for rad and for lane)
                if strName == 'RestrictionsType':
                    if strName.endswith('Type'):
                        strName = eaEl.Name[:-4] + strName
                    else:
                        strName = eaEl.Name + strName
                eaDTel = getOrCreateElementByName(eaPck,strName,"DataType", "",False,"",eaAttr.Notes,delAttr)
                eaPck.Elements.Refresh()
                eaAttr.Type = eaDTel.Name
                eaAttr.ClassifierID = eaDTel.ClassifierID
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
            # In case eaDTel not referenced. Create (or get) data type
            strName = eaAttr.Name[0].upper() + eaAttr.Name[1:] + "Type"
            # Speciality for restrictions (two different types - for rad and for lane)
            if strName == 'RestrictionsType':
                if strName.endswith('Type'):
                    strName = eaEl.Name[:-4] + strName
                else:
                    strName = eaEl.Name + strName
            eaDTel = getOrCreateElementByName(eaPck,strName,"DataType", "",False,"",eaAttr.Notes,False)
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
            if strRef.endswith('.json'):
                strRef = strRef.removesuffix('.json')
            elif not strRef.endswith('Container'):
                strRef += "Type"
            strRef = strRef[0].upper() + strRef[1:]
            printTS('Attributeref: ' + strRef)
            eaAttr.Type = strRef      
        elif key == 'items':
            # items in an array
            eaAttr = convertAttributeProperties(eaRepo,eaPck,eaEl,eaAttr,yDict[key])
        elif key == 'prefixItems' and not 'items' in yDict:
            # prefixItems is an array, where each item is a schema that corresponds to each index of the document's array. 
            # That is, an array where the first element validates the first element of the input array, 
            # the second element validates the second element of the input array, etc.
            # The array has only one occurence, as the multiplicity is within the array
            # NOTE: Skips this if there's also an item occurency in the schema. To avoid trouble with NamesType.common....
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
        elif key == 'allOf':
            # allOf for the value type of the property type or allOf attributes for a object type
            printTS(key + ' statement' )
            if strType == 'object' and (len(yDict[key]) > 1 or 'properties' in yDict):
                # add properties for the object data type
                eaDTel = createAttributesFromYAMLDictionary(eaRepo,eaPck, eaDTel,yDict[key],lstReq,1)
            else:
                # Set data type
                for eKey in yDict[key]:
                    eaAttr = convertAttributeProperties(eaRepo,eaPck,eaEl,eaAttr,eKey)
                eaAttr.LowerBound = 1    
            #
        elif key == 'oneOf':
            # oneOf for the value type of the property type --> selection of value types
            printTS(key + ' statement' )
            lstTypes = []
            dA=True 
            dtaCount = 0
            strName = eaAttr.Name[0].upper() + eaAttr.Name[1:] + "Type"
            for eKey in yDict[key]:
                eaAttr = convertAttributeProperties(eaRepo,eaPck,eaEl,eaAttr,eKey,dA) 
                if eaAttr.Type == strName:
                    # Data type created for one option
                    dtaCount += 1
                    dA=False
                if eaAttr.Type not in lstTypes:
                    lstTypes.append(eaAttr.Type)
            if dtaCount > 1:
                # More than one option added to the data type. Set lower bound = 0 and add constaint
                printTS('More than one option!')
                strOCL = 'inv:'
                eaDTel = eaPck.Elements.GetByName(strName)
                for eaDTAttr in eaDTel.Attributes:
                    eaDTAttr.LowerBound = 0
                    eaDTAttr.Update()
                    strOCL += ' self.' + eaDTAttr.Name + '->notEmpty() or' 
                strOCL = strOCL.rstrip(' or')
                eaConstraint = eaDTel.Constraints.AddNew(strOCL,'OCL')
                eaConstraint.Update()
            if len(lstTypes) > 1:
                # Different types for each alternative. No type + constraint
                printTS(lstTypes)
                strOCL = 'inv:' #'context ' + eaEl.Name + ' inv:'
                for alt in lstTypes:
                    strOCL += ' self.' + eaAttr.Name + '.oclIsTypeOf(' + alt + ') or'
                strOCL = strOCL.rstrip(' or')

                eaConstraint = eaEl.Constraints.AddNew(strOCL,'OCL')
                eaConstraint.Update()
                
                eaAttr.Type = ''

    eaAttr.Update()        
    return eaAttr


# --------- Test code ----------------





