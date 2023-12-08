!INC Local Scripts.EAConstants-JavaScript
!INC OvertureMaps.Parameters
!INC OvertureMaps.CommonFunctions

/*
 * Script Name: CommonSchema
 * Author: Knut Jetlund
 * Purpose: Convert Overture Maps themes schemas to UML
 * Date: 20231205
 */


function main(delElements, clsName, abs, fileName)
{
	outputTabs();
	Repository.WriteOutput("Script", new Date().toLocaleTimeString() + " Starting script...", 0);
	
	// Get the package to work on
	var pck as EA.Package;
	pck = getSelectedPackage();
	if (pck == null)
	{
		return
	}
	
	//Delete all existing elements in the package if parameter is set to true
	var els as EA.Collection;
	if (delElements)
	{
		els = deleteAllElements(pck);
	} else
	{
		els = pck.Elements
	}
		
	var el as EA.Element;
	var acEl as EA.Element = null;
	var dtEl as EA.Element = null;
	
	//Create FeatureTypr
	acEl = els.AddNew(clsName[0].toUpperCase() + clsName.slice(1), "Class" );
	acEl.Stereotype = "FeatureType";
	acEl.Abstract = abs;
	acEl.Update();
	els.Refresh();
	Repository.WriteOutput("Script", new Date().toLocaleTimeString() + " Class for global attributes: " + acEl.Name, 0);
		
	var attrs as EA.Collection
	attrs = acEl.Attributes
	var attr as EA.Attribute;
	var dtAttr as EA.Attribute;
	
	// Reading OM JSON file
	Repository.WriteOutput("Script", new Date().toLocaleTimeString() + " Main folder: " + mainFolder, 0);
	Repository.WriteOutput("Script", new Date().toLocaleTimeString() + " Reading file: " + fileName, 0);
	var fso = new COMObject( "Scripting.FileSystemObject" );
	f = fso.OpenTextFile(fileName, 1);
	fStr = f.ReadAll();
	//Repository.WriteOutput("Script", new Date().toLocaleTimeString() + " " + fStr, 0);

	
	// Converting JSON-encoded string to JS object
	var jsonObject = JSON.parse(fStr);
	
		// Accessing individual value from JS object
	for (var k in jsonObject)
	{
		if (k == 'title')
		{	
			Repository.WriteOutput("Script", new Date().toLocaleTimeString() + " Schema title: " + jsonObject[k], 0);
			acEl.Alias = jsonObject[k];
			acEl.Update();
		}	else if (k == 'description') 
		{
			Repository.WriteOutput("Script", new Date().toLocaleTimeString() + " Schema description: " + jsonObject[k], 0);
			acEl.Notes = jsonObject[k];
			acEl.Update();
		}  else if (k == "properties")
		{
			for (var l in jsonObject[k])
			{
				Repository.WriteOutput("Script", new Date().toLocaleTimeString() + " Property: " + l, 0);
				attr = acEl.Attributes.AddNew(l,"");
				attr.Visibility = "Public";
				attr.Update();

				for (var m in jsonObject[k][l])
				{
					if(typeof jsonObject[k][l][m] != 'object')
					{
						//Convert attributes from simple declarations
						Repository.WriteOutput("Script", new Date().toLocaleTimeString() + " Property definition property: " + m + ": " + jsonObject[k][l][m], 0);
						var strP = jsonObject[k][l][m];
						attr = convertAttribute(attr,els,m,strP);
					} else
					{
						//Object declarations, dive into deeper levels
						//Enumeration - Create enumeration with values
						if (m == "enum")
						{
							dtEl = els.AddNew(attr.Name[0].toUpperCase() + attr.Name.slice(1) + "Code", "Enumeration");
							dtEl.Update();
							Repository.WriteOutput("Script", new Date().toLocaleTimeString() + " Create enumeration: " + dtEl.Name, 0);	
							els.Refresh();
							attr.Type = dtEl.Name;
							attr.ClassifierID = dtEl.ElementID;
							
							//Enumeration values
							for (var n in jsonObject[k][l][m])
							{
								Repository.WriteOutput("Script", new Date().toLocaleTimeString() + " Enumeration value: " + jsonObject[k][l][m][n], 0);	
								dtAttr = dtEl.Attributes.AddNew(jsonObject[k][l][m][n],"");
								dtAttr.Update();
								dtEl.Attributes.Refresh();
							}		
						}									
						else if (m == "items")	
						{
							//For arrays: Add data type from "item"
							//TODO: What if more than one "item"?
							for (var n in jsonObject[k][l][m])
							{
								attr = getAttributeTypeFromRef(attr, jsonObject[k][l][m][n])
							}		
						}	
						else if (m == "properties")
						{	
							//Add attributes for the data type from additional indent 
							els.Refresh();
							dtEl = Repository.GetElementByID(attr.ClassifierID);
							for (var n in jsonObject[k][l][m])
							{
								Repository.WriteOutput("Script", new Date().toLocaleTimeString() + " Datatype property definition: " + n, 0);
								dtAttr = dtEl.Attributes.AddNew(n,"");
								dtAttr.Update();
								dtEl.Attributes.Refresh()
								
								for (var o in jsonObject[k][l][m][n])
								{	
									var strO = jsonObject[k][l][m][n][o]
									if (o == "type" || o == "description")
									// Convert to data type attributes	
									{
										dtAttr = convertAttribute(dtAttr,els,o,strO);
									}
									else if (o == "$ref") 
									{
										dtAttr = getAttributeTypeFromRef(dtAttr, strO)
									}												
									else if (o == "items")	
									{
										//For arrays: Add data type from "item"
										//TODO: What if more than one "item"?
										for (var p in jsonObject[k][l][m][n][o])
										{
											dtAttr = getAttributeTypeFromRef(dtAttr, jsonObject[k][l][m][n][o][p])
										}		
									}	
								}	
								dtAttr.Update();
								dtEl.Attributes.Refresh()
							}
						}
						else if (m == "oneOf")
						{	
							var aCon as EA.AttributeConstraint;
							aCon = attr.Constraints.AddNew("oneOf", "");
							aCon.Notes = '"oneOf":'+ JSON.stringify(jsonObject[k][l][m]);
							aCon.Update();
							Repository.WriteOutput("Script", new Date().toLocaleTimeString() + " One of constraint: " + aCon.Notes, 0);	
						}
					}	
				}	
				attr.Update();
			}
		}				
	}
	
	
	
	
	
	
	
	

	// Find or create diagram
	var eDgr as EA.Diagram = null;
	for ( var i = 0 ; i < pck.Diagrams.Count ; i++ )
	{
		eDgr = pck.Diagrams.GetAt(i);
		Repository.WriteOutput("Script", new Date().toLocaleTimeString() + " Diagram: " + eDgr.Name, 0);
		if (eDgr.Name == pck.Name)
		{
			i = pck.Diagrams.Count;
		}
	}
	if (eDgr == null)
	{
		eDgr = pck.Diagrams.AddNew(pck.Name,"");
		eDgr.Update();
	}
	// Add all elements 
	var eDgrObj as EA.DiagramObject
	for ( var i = 0 ; i < els.Count ; i++ )
	{
		el = els.GetAt(i);
		Repository.WriteOutput("Script", new Date().toLocaleTimeString() + " Adding diagramobject: " + el.Name, 0);
		eDgrObj = eDgr.DiagramObjects.AddNew("","");
		eDgrObj.ElementID = el.ElementID;
		eDgrObj.Update();
	}
	eDgr.Update();
	
	// AutoLayout
	var ePIF as EA.Project
	ePIF = Repository.GetProjectInterface();
	ePIF.LayoutDiagramEx(eDgr.DiagramGUID, 4, 4, 20, 20, true);
	Repository.CloseDiagram(eDgr.DiagramID);
		
	Repository.WriteOutput("Script", new Date().toLocaleTimeString() + " Finished, check logs!", 0);


}


var theme = "transportation";
var ft = "connector";
main(true,ft,false, mainFolder + "\\" + theme + "\\" + ft + ".json");
var ft = "segment";
main(false,ft,false, mainFolder + "\\" + theme + "\\" + ft + ".json");
