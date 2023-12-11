!INC Local Scripts.EAConstants-JavaScript
!INC OvertureMaps.Parameters
!INC OvertureMaps.CommonFunctions

/*
 * Script Name: CommonSchema
 * Author: Knut Jetlund
 * Purpose: Convert Overture Maps common properties to UML
 * Date: 20231122
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
	
	//Create AttributeCatalogue 	
	acEl = els.AddNew(clsName, "Class" );
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
	f = fso.OpenTextFile(defFileJSON, 1);
	fStr = f.ReadAll();
	//Repository.WriteOutput("Script", new Date().toLocaleTimeString() + " " + fStr, 0);

	
	// Converting JSON-encoded string to JS object
	var jsonObject = JSON.parse(fStr);

	// Accessing individual value from JS object
	for (var j in jsonObject)
	{
		if (j == 'title')
		{	
			Repository.WriteOutput("Script", new Date().toLocaleTimeString() + " Schema title: " + jsonObject[j], 0);
			pck.Alias = jsonObject[j];
			pck.Update();
		}	else if (j == 'description') 
		{
			Repository.WriteOutput("Script", new Date().toLocaleTimeString() + " Schema description: " + jsonObject[j], 0);
			pck.Notes = jsonObject[j];
			pck.Update();
		} 
		else if (j =='$defs' )
		{
			// Definition statements
			for (var k in jsonObject[j])
			{
				if (k == 'propertyDefinitions')
				//Property defintions
				{
					for (var l in jsonObject[j][k])
					{
						Repository.WriteOutput("Script", new Date().toLocaleTimeString() + " Property definition: " + l, 0);
						attr = acEl.Attributes.AddNew(l,"");
						attr.Visibility = "Public";
						attr.Update();

						for (var m in jsonObject[j][k][l])
						{
							if(typeof jsonObject[j][k][l][m] != 'object')
							{
								//Convert attributes from simple declarations
								Repository.WriteOutput("Script", new Date().toLocaleTimeString() + " Property definition property: " + m + ": " + jsonObject[j][k][l][m], 0);
								var strP = jsonObject[j][k][l][m];
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
									for (var n in jsonObject[j][k][l][m])
									{
										Repository.WriteOutput("Script", new Date().toLocaleTimeString() + " Enumeration value: " + jsonObject[j][k][l][m][n], 0);	
										dtAttr = dtEl.Attributes.AddNew(jsonObject[j][k][l][m][n],"");
										dtAttr.Update();
										dtEl.Attributes.Refresh();
									}		
								}									
								else if (m == "items")	
								{
									//For arrays: Add data type from "item"
									//TODO: What if more than one "item"?
									for (var n in jsonObject[j][k][l][m])
									{
										attr = getAttributeTypeFromRef(attr, jsonObject[j][k][l][m][n])
									}		
								}	
								else if (m == "properties")
								{	
									//Add attributes for the data type from additional indent 
									els.Refresh();
									dtEl = Repository.GetElementByID(attr.ClassifierID);
									for (var n in jsonObject[j][k][l][m])
									{
										Repository.WriteOutput("Script", new Date().toLocaleTimeString() + " Datatype property definition: " + n, 0);
										dtAttr = dtEl.Attributes.AddNew(n,"");
										dtAttr.Update();
										dtEl.Attributes.Refresh()
										
										for (var o in jsonObject[j][k][l][m][n])
										{	
											var strO = jsonObject[j][k][l][m][n][o]
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
												for (var p in jsonObject[j][k][l][m][n][o])
												{
													dtAttr = getAttributeTypeFromRef(dtAttr, jsonObject[j][k][l][m][n][o][p])
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
									aCon.Notes = '"oneOf":'+ JSON.stringify(jsonObject[j][k][l][m]);
									aCon.Update();
									Repository.WriteOutput("Script", new Date().toLocaleTimeString() + " One of constraint: " + aCon.Notes, 0);	
								}
							}	
						}	
						attr.Update();
					}

				}					
			}				
		}
	}
	
	Repository.WriteOutput("Script", new Date().toLocaleTimeString() + " Fixing types and classifier IDs...", 0);	
	
	//	Loop for all data types and enumerations: 
	//	Find attributes in element with the objectname as type. Define ClassifierID from ElementId
	
	pck.Elements.Refresh();
	
	for ( var i = 0 ; i < pck.Elements.Count ; i++ )
	{
		dtEl = pck.Elements.GetAt(i);
		if (dtEl.Type == "Enumeration" || dtEl.Type == "DataType")
		{	
			for ( var j = 0 ; j < pck.Elements.Count ; j++ )
			{
				el = pck.Elements.GetAt(j)
				for ( var k = 0 ; k < el.Attributes.Count ; k++ )
				{
					attr = el.Attributes.GetAt(k)
					if (attr.Type == dtEl.Name)
					{
						attr.ClassifierID = dtEl.ElementID;
						attr.Update();
					}				
				}
				el.Attributes.Refresh();
			}	
		}
	}
		
	// 	Loop for all attributes in all classes and data types:
	//	Fix Type for attributes without GUID: Ref linearPos. 
	// If there exists another attribute in AttributeCatalogue with the Type name, without type --> use the same Type as that one. 
	for ( var i = 0 ; i < pck.Elements.Count ; i++ )
	{
		el = pck.Elements.GetAt(i);
		var eln = el.Name;
		if (el.Type == "Class" || el.Type == "DataType")
		{	
			for ( var j = 0 ; j < el.Attributes.Count ; j++ )
			{
				attr = el.Attributes.GetAt(j)
				var strType = attr.Type
				if (attr.ClassifierID == 0 && attr.Type != "")
				{
					strType = strType[0].toLowerCase() + strType.slice(1,-4);
					attrs.Refresh();
					for ( var k = 0 ; k < attrs.Count ; k++ )
					{
						var dtAttr as EA.Attribute
						dtAttr = attrs.GetAt(k);
						if (dtAttr.Name == strType)
						{
							attr.Type = dtAttr.Type;
							attr.ClassifierID = dtAttr.ClassifierID;
							attr.Update();
						}				
					}
				}				
			}
		}	
	}
	// Find or create diagram
	var eDgr as EA.Diagram = null;
	for ( var i = 0 ; i < pck.Diagrams.Count ; i++ )
	{
		eDgr = pck.Diagrams.GetAt(i);
		Repository.WriteOutput("Script", new Date().toLocaleTimeString() + " Diagram: " + eDgr.Name, 0);
		if (eDgr.Name == "Common")
		{
			i = pck.Diagrams.Count;
		}
	}
	if (eDgr == null)
	{
		eDgr = pck.Diagrams.AddNew("Common","");
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

main(true,acName,true, defFileJSON);