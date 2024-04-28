from Parameters import *
from EAConnect import *
import sys, os, re, yaml, json

def recExport(p,lc):
    if lc <= maxLevels:
        ePIF = eaRepo.GetProjectInterface()
        printTS("Package: (level = " + str(lc) + "): " + p.Name)     
        for dgr in p.Diagrams:
            fName = mainFolder + "\\PNG\\" + dgr.Name + ".PNG"
            printTS("Exporting diagram " + dgr.Name)
            ePIF.LoadDiagram(ePIF.GUIDtoXML(dgr.DiagramGUID))
            ePIF.SaveDiagramImageToFile(fName)
            eaRepo.CloseDiagram(dgr.DiagramID)
        if lc < maxLevels:
            for subP in p.Packages:
                recExport(subP,lc+1)


maxLevels = 1

# -------------------------------------------------------------------------------------
# Open EA Repository and find OM Model
eaApp = openEAapp()
repo_path = mainFolder + '\\EA\\2024-03 OvertureMaps.qea'
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
    recExport(eaPck,0)

printTS("------------- DONE ------------------")


# closeEA(eaRepo)