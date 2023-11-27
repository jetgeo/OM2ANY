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
	Repository.WriteOutput("Script", new Date().toLocaleTimeString() + " Attribute count: " + attrs.Count, 0);
	//Delete all existing attributes
	for ( var i = 0 ; i < attrs.Count ; i++ )
	{
		attrs.DeleteAt( i, false );
	}
	attrs.Refresh
	
	
	// Reading OM YAML schema file
	Repository.WriteOutput("Script", new Date().toLocaleTimeString() + " Main folder: " + mainFolder, 0);
	Repository.WriteOutput("Script", new Date().toLocaleTimeString() + " Reading file: " + defFile, 0);
	var fso = new COMObject( "Scripting.FileSystemObject" );
	f = fso.OpenTextFile(defFile, 1);
	var pDef = false
	var spanType = ""
	var pCont = false
	
	// Read line by line from the file 
	while (!f.AtEndOfStream)
    {
		var r = f.ReadLine();
		var rArray = r.split(":");
		if (rArray[0]=="title")
		{
			Repository.WriteOutput("Script", new Date().toLocaleTimeString() + " Title: " + rArray[1], 0);
			pck.Alias = rArray[1];
			pck.Update();
		}	else if (rArray[0]=="description") 
		{
			Repository.WriteOutput("Script", new Date().toLocaleTimeString() + " Description: " + rArray[1], 0);
			pck.Notes = rArray[1];
			pck.Update();
		} else if (rArray[0]=="  propertyDefinitions" )
		{	
			pDef = true
			pCont = false
			Repository.WriteOutput("Script", new Date().toLocaleTimeString() + " Start of propertyDefinitions sequence", 0);
		} else if (rArray[0]=="  propertyContainers" )
		{	
			pCont = true
			pDef = false
			Repository.WriteOutput("Script", new Date().toLocaleTimeString() + " Start of propertyContainters sequence", 0);
		} 	else if (pDef)
		{
			//propertyDefinitions to attributes
			//check for 4 whitespaces --> attribute name
			var attrTag as EA.AttributeTag
			var attr as EA.Attribute;
			var dtAttr as EA.Attribute
			if (/^\s{4}\S/.test(rArray[0]))
			{
				Repository.WriteOutput("Script", new Date().toLocaleTimeString() + " attribute name: " + rArray[0], 0);	
				attr = acEl.Attributes.AddNew(rArray[0].trim(),"");
				attr.Visibility = "Public";
				attr.Update();
			}
			//check for 6 whitespaces --> attribute details
			else if (/^\s{6}\S/.test(rArray[0]))
			{
				//Reset spantype parameter
				spanType = "";
				
				//Datatype conversion from type
				var strP = rArray[0].trim()
				if (strP == "type")
				{
					Repository.WriteOutput("Script", new Date().toLocaleTimeString() + " Type: '" + rArray[1].trim() + "'", 0);	
					var guidDT = "0"		
					if (rArray[1].trim() == "string")
					{
						attr.Type = "CharacterString";
						guidDT = guidCharacterString;
					}   else if (rArray[1].trim() == "integer")
					{
						attr.Type = "Integer";
						guidDT = guidInteger;
					}	else if (rArray[1].trim() == "number")
					{
						attr.Type = "Real";
						guidDT = guidReal;
					}	else
					{
						attr.Type = rArray[1];
					}						
					//Lookup type element from GUID, add reference
					if (guidDT != 0)
					{
						dtEl = Repository.GetElementByGuid(guidDT);
						attr.ClassifierID = dtEl.ElementID;
					}	
					//TODO: Handling other data types: 
					//array: Multiplicity, datatype from item. Set datatype array first, then change from item value (last part if id + Type?)
					//		+ multiplicity from minitems & maxitems
					//		Works for types that are object, not for linearPos...
					//object. Create own feature type (or data type?)
					//		Find attributes with the objectname as type. Define ClassifierID
					
					//TODO: oneOf, i.e. language. Union?
					
					
				}					
				
				//Definition from description
				else if (strP == "description" || strP == '"$comment"')
				{
					Repository.WriteOutput("Script", new Date().toLocaleTimeString() + strP + ": " + rArray[1], 0);	
					if (strP == '"$comment"')
					{
						attr.Notes = attr.Notes + " .Comment:" ;
					}	
					if (rArray[1].trim() == ">-")
					{	
						//Definitions or comments spanning several lines (Starts with >-)
						spanType = "Definition";
					} 	else
					{	
						spanType = "";
						attr.Notes = attr.Notes + " " + rArray[1].trim();	
					}	
					
				}					
				//Initial value from default
				else if (strP == "default")
				{
					Repository.WriteOutput("Script", new Date().toLocaleTimeString() + " Default value: " + rArray[1], 0);	
					attr.Default = rArray[1].trim();
				}					
				
				//TODO: Tagged vale for format. Not working. Temporarly adding to definition.
				else if (strP == "format")
				{
					Repository.WriteOutput("Script", new Date().toLocaleTimeString() + " Format: " + rArray[1], 0);	
					attrTag = attr.TaggedValues.AddNew("format","");
					attrTag.Update;
					//Tagged value not working (?), adding to definition
					attr.Notes = attr.Notes + "\n. Format: " + rArray[1].trim();
				}					
				
				//TODO: Tagged value for pattern. Not working. Temporarly adding to definition.
				else if (strP == "pattern")
				{
					Repository.WriteOutput("Script", new Date().toLocaleTimeString() + " Pattern: " + rArray[1], 0);	
					attrTag = attr.TaggedValues.AddNew("pattern","");
					attrTag.Update;
					//Tagged value not working (?), adding to definition
					attr.Notes = attr.Notes + "\n. Pattern: " + rArray[1].trim();
				}					
				
				//TODO: Tagged value for comment. Temporarly added to definiton
								
				//TODO: enums
				else if (strP == "enum")
				{
					dtEl = els.AddNew(attr.Name[0].toUpperCase() + attr.Name.slice(1) + "Code", "Enumeration");
					dtEl.Update();
					Repository.WriteOutput("Script", new Date().toLocaleTimeString() + " Create enumeration: " + dtEl.Name, 0);	
					els.Refresh();
					attr.Type = dtEl.Name;
					attr.ClassifierID = dtEl.ElementID;
					spanType = "Enum"; 
				}				
				
				
				//TODO: minItems, maxItems, uniqueItems
				attr.TaggedValues.Refresh
				attr.Update();
			}	
			
			//check for 8 whitespaces --> definition, enum etc spanning several lines
			else if (/^\s{8}\S/.test(rArray[0]))
			{
				if (spanType == "Definition")
				{
					attr.Notes = attr.Notes + " " + r.trim();
					attr.Update();
				}	else if (spanType == "Enum")
				{
					dtAttr = dtEl.Attributes.AddNew(r.slice(10),"");
					dtAttr.Update();
					Repository.WriteOutput("Script", new Date().toLocaleTimeString() + " Add code to enumeration: " + dtAttr.Name, 0);	
					dtEl.Attributes.Refresh();
				}				
				
			}
			acEl.Attributes.Refresh();
		
		}
		//propertyContainers to data types
		
		
    }
	
	
	Repository.WriteOutput("Script", new Date().toLocaleTimeString() + " Finished, check logs!", 0);
}

main();