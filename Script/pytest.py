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
            matching_items = [item for item in lstNames if item.startswith(eaEl.Name) and item != eaEl.Name]
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
                        printTS(strName)                        
                        printTS(matching_item_parts)
                    elif strName.startswith('Use'):
                        printTS('LandUse - need to fix somehow...')    
                    else:
                        printTS(eaEl.Name + strName + ' is unique without prefix, removing prefix!')    
                        eaDTel = eaPck.Elements.GetByName(eaEl.Name + strName)
                        eaDTel.Name = strName
                        eaDTel.Update()
