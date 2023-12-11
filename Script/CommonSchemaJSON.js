!INC Local Scripts.EAConstants-JavaScript
!INC OvertureMaps.Parameters
!INC OvertureMaps.CommonFunctions

/*
 * Script Name: CommonSchema
 * Author: Knut Jetlund
 * Purpose: Convert Overture Maps common properties to UML
 * Date: 20231122
 */


 
function main()
{
	outputTabs;
	Repository.WriteOutput("Script", new Date().toLocaleTimeString() + " Starting script...", 0);
	
	// Store JSON data in a JS variable
	var json = '{"name": "Peter", "age": 22, "country": "United States"}';


	// Get the package to work on
	var contextObjectType = Repository.GetContextItemType();
	if ( contextObjectType == EA.ObjectType.otPackage )
	{
		var pck as EA.Package;
		pck = Repository.GetContextObject();
		Repository.WriteOutput("Script", new Date().toLocaleTimeString() + " Package: " + pck.Name, 0);
	}
	else
	{
		Session.Prompt( "This script requires a package to be selected.\n" + "Please select a package and try again.", System.PromptType.promptOK );
		return
	}
	
	//Delete all existing classes
	var els as EA.Collection;
	els = pck.Elements;
	var acEl as EA.Element;
		
	var el as EA.Element;
	for ( var i = 0 ; i < els.Count ; i++ )
	{
		el = els.GetAt(i);
		Repository.WriteOutput("Script", new Date().toLocaleTimeString() + " Delete element: " + el.Name, 0);
		els.DeleteAt(i, false);
	}
	els.Refresh
	acEl = null;
	var dtEl as EA.Element
	dtEl = null;
	//Create AttributeCatalogue 	
	acEl = els.AddNew(acName, "Class" );
	acEl.Stereotype = "FeatureType";
	acEl.Abstract = true;
	acEl.Update();
	els.Refresh();
	Repository.WriteOutput("Script", new Date().toLocaleTimeString() + " Class for global attributes: " + acEl.Name, 0);
	
	
	var attrs as EA.Collection
	attrs = acEl.Attributes
	var attr as EA.Attribute;
	var dtAttr as EA.Attribute;
	
	Repository.WriteOutput("Script", new Date().toLocaleTimeString() + " Attribute count: " + attrs.Count, 0);
	//TODO: Can this be removed now? Delete all existing attributes 
	//for ( var i = 0 ; i < attrs.Count ; i++ )
	//{
	//	attrs.DeleteAt( i, false );
	//}
	//attrs.Refresh
	
	// Reading OM JSON file
	Repository.WriteOutput("Script", new Date().toLocaleTimeString() + " Main folder: " + mainFolder, 0);
	Repository.WriteOutput("Script", new Date().toLocaleTimeString() + " Reading file: " + defFileJSON, 0);
	var fso = new COMObject( "Scripting.FileSystemObject" );
	f = fso.OpenTextFile(defFileJSON, 1);
	fStr = f.ReadAll();
	Repository.WriteOutput("Script", new Date().toLocaleTimeString() + " " + fStr, 0);

	
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
			// Definitions
			for (var k in jsonObject[j])
			{
				if (k == 'propertyDefinitions')
				//Property defintions
				{
					for (var l in jsonObject[j][k])
					{
						Repository.WriteOutput("Script", new Date().toLocaleTimeString() + "Property definition: " + l, 0);
						attr = acEl.Attributes.AddNew(l,"");
						attr.Visibility = "Public";
						attr.Update();

						for (var m in jsonObject[j][k][l])
						{
							if(typeof jsonObject[j][k][l][m] != 'object')
							{
								Repository.WriteOutput("Script", new Date().toLocaleTimeString() + "Property definition property: " + m + ": " + jsonObject[j][k][l][m], 0);
								var strP = jsonObject[j][k][l][m];
								
								if (m == "type")
								// Attribute type, convert to ISO 19103 types	
								{
									Repository.WriteOutput("Script", new Date().toLocaleTimeString() + " Type: " + strP , 0);	
									var guidDT = "0"		
									if (strP == "string")
									{
										attr.Type = "CharacterString";
										guidDT = guidCharacterString;
									}   else if (strP == "integer")
									{
										attr.Type = "Integer";
										guidDT = guidInteger;
									}	else if (strP == "number")
									{
										attr.Type = "Real";
										guidDT = guidReal;
									} 	else if (strP == "object")				
									{
										//object. Create data type
										dtEl = els.AddNew(attr.Name[0].toUpperCase() + attr.Name.slice(1)  + "Type", "DataType");
										dtEl.Update();
										Repository.WriteOutput("Script", new Date().toLocaleTimeString() + " Create data type: " + dtEl.Name, 0);	
										els.Refresh();
										attr.Type = dtEl.Name;
										attr.ClassifierID =dtEl.ElementID;
										
										//TODO: Add attributes for the data type. One additional indent level
										
									} 	else if (strP == "array")	
									{
										//array: 	Set datatype array first, then change from item value (last part if id + Type)
										//			Works for types that are object, not for linearPos, which is fixed at the end
										attr.Type = "Array";
											
									}	else
									{
										//TODO: oneOf, i.e. language. Union?
										attr.Type = strP;
									}	
									//Lookup type element from GUID, add reference
									if (guidDT != 0)
									{
										dtEl = Repository.GetElementByGuid(guidDT);
										attr.ClassifierID = dtEl.ElementID;
									}	
								}
								
								//Definition from description
								else if (m == "description")
								{
									Repository.WriteOutput("Script", new Date().toLocaleTimeString() + "Definition : " + strP, 0);	
									attr.Notes = strP;	
								}	
								
								//Initial value from default
								else if (m == "default")
								{
									Repository.WriteOutput("Script", new Date().toLocaleTimeString() + " Default value: " + strP, 0);	
									attr.Default = strP;
								}					
								
								else if (m == "minItems")
								{
									//For arrays: minItems
									attr.LowerBound = strP;
									attr.UpperBound = "*";
								}	
								else if (m == "maxItems")
								{
									//For arrays: maxItems
									attr.UpperBound = strP;
								}   
								else if (m == "uniqueItems" || strP == "true")
								{
									attr.AllowDuplicates = false;
									attr.Update();
								}

								//TODO: Tagged vale for format
								//TODO: Tagged vale for pattern
								//TODO: Tagged vale for comment
								
							} else
							{
								Repository.WriteOutput("Script", new Date().toLocaleTimeString() + " Object", 0);	
								//Enumerations
								if (m == "enum")
								{
									dtEl = els.AddNew(attr.Name[0].toUpperCase() + attr.Name.slice(1) + "Code", "Enumeration");
									dtEl.Update();
									Repository.WriteOutput("Script", new Date().toLocaleTimeString() + " Create enumeration: " + dtEl.Name, 0);	
									els.Refresh();
									attr.Type = dtEl.Name;
									attr.ClassifierID = dtEl.ElementID;
									
									//TODO: Enum values
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
									//TODO For arrays: Add data type from "item"
									for (var n in jsonObject[j][k][l][m])
									{
										Repository.WriteOutput("Script", new Date().toLocaleTimeString() + " Array item type: " + jsonObject[j][k][l][m][n], 0);	
										//split on "/", find last element, UpperCase first letter, add "Type"
										var p = jsonObject[j][k][l][m][n].lastIndexOf("/");
										var strItem = jsonObject[j][k][l][m][n].slice(p+1);
										attr.Type = strItem[0].toUpperCase() + strItem.slice(1)  + "Type";
									}		
								}	
								
							}	
						}	
						attr.Update();
					}

				}					
			}				
		}

	}

	
	//	Loop for all data types and enumerations: 
	//	Find attributes in AttributeCatalogue with the objectname as type. Define ClassifierID from ElementId
	attrs.Refresh();
	for ( var i = 0 ; i < els.Count ; i++ )
	{
		dtEl = els.GetAt(i);
		for ( var j = 0 ; j < attrs.Count ; j++ )
		{
			attr = attrs.GetAt(j)
			if (attr.Type == dtEl.Name)
			{
				attr.ClassifierID = dtEl.ElementID;
				attr.Update();
			}				
		}
		attrs.Refresh();
	}
	
	
	// 	Loop for all attributes in AttributeCatalogue:
	//	Fix Type for attributes without GUID: Ref linearPos. If there exists another attribute with the Type name, without type --> use sate Type as that one. 
	for ( var i = 0 ; i < attrs.Count ; i++ )
	{
		attr = attrs.GetAt(i)
		if (attr.ClassifierID == 0 && attr.Type != "")
		{
			var strType = attr.Type
			strType = strType[0].toLowerCase() + strType.slice(1,-4);
			for ( var j = 0 ; j < attrs.Count ; j++ )
			{
				var dtAttr as EA.Attribute
				dtAttr = attrs.GetAt(j);
				if (dtAttr.Name == strType)
				{
					attr.Type = dtAttr.Type;
					attr.ClassifierID = dtAttr.ClassifierID;
					attr.Update();
				}				
			}
		}				
	}
	attrs.Refresh();

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
	//Repository.CloseDiagram(eDgr.DiagramID);
	
	
	Repository.WriteOutput("Script", new Date().toLocaleTimeString() + " Finished, check logs!", 0);
}

main();