!INC Local Scripts.EAConstants-JavaScript
!INC OvertureMaps.Parameters


/*
 * Script Name: CommonFunctions
 * Author: Knut Jetlund
 * Purpose: Common functions for OvertureMaps schema conversion
 * Date: 20231123
 */
 
function getAttributeTypeFromRef(theAttribute, theRef)
{
	Repository.WriteOutput("Script", new Date().toLocaleTimeString() + " Type from reference: " + theRef, 0);	
	//split on "/", find last element, UpperCase first letter, add "Type"
	var slashPos = theRef.lastIndexOf("/");
	var strItem = theRef.slice(slashPos+1);
	theAttribute.Type = strItem[0].toUpperCase() + strItem.slice(1)  + "Type";
	return theAttribute;
}
 
function convertAttribute(theAttribute,theElements,theParameter,theString)
//Convert attribute type, definition etc. 
{
	if (theParameter == "type")
	{	
		Repository.WriteOutput("Script", new Date().toLocaleTimeString() + " Type: " + theString , 0);	
		var guidDT = "0"
		var theDtElement as EA.Element
		if (theString == "string")
		{
			theAttribute.Type = "CharacterString";
			guidDT = guidCharacterString;
		}   else if (theString == "integer")
		{
			theAttribute.Type = "Integer";
			guidDT = guidInteger;
		}	else if (theString == "number")
		{
			theAttribute.Type = "Real";
			guidDT = guidReal;
		} 	else if (theString == "object")				
		{
			//object. Create data type
			theDtElement = theElements.AddNew(theAttribute.Name[0].toUpperCase() + theAttribute.Name.slice(1)  + "Type", "DataType");
			theDtElement.Update();
			Repository.WriteOutput("Script", new Date().toLocaleTimeString() + " Create data type: " + theDtElement.Name, 0);	
			theElements.Refresh();
			theAttribute.Type = theDtElement.Name;
			theAttribute.ClassifierID = theDtElement.ElementID;
		} 	else if (theString == "array")	
		{
			//array: 	Set datatype array first, then change from item value (last part if id + Type)
			//			Works for types that are object, not for linearPos, which is fixed at the end
			theAttribute.Type = "Array";
				
		}	else
		{
			theAttribute.Type = theString;
		}	
		//Lookup type element from GUID, add reference
		if (guidDT != 0)
		{
			theDtElement = Repository.GetElementByGuid(guidDT);
			theAttribute.ClassifierID = theDtElement.ElementID;
		}
	}	
	//Definition from description
	else if (theParameter == "description")
	{
		Repository.WriteOutput("Script", new Date().toLocaleTimeString() + " Definition : " + theString, 0);	
		theAttribute.Notes = theString;	
	}	
	
	//Initial value from default
	else if (theParameter == "default")
	{
		Repository.WriteOutput("Script", new Date().toLocaleTimeString() + " Default value: " + theString, 0);	
		theAttribute.Default = theString;
	}					
	
	else if (theParameter == "minItems")
	{
		//For arrays: minItems
		theAttribute.LowerBound = theString;
		theAttribute.UpperBound = "*";
	}	
	else if (theParameter == "maxItems")
	{
		//For arrays: maxItems
		theAttribute.UpperBound = theString;
	}   
	else if (theParameter == "uniqueItems" || theString == "true")
	{
		theAttribute.AllowDuplicates = false;
	}
	else if (theParameter == "minimum")
	{
		//TODO: Handle value domain
	}	
	else if (theParameter == "maximum")
	{
		//TODO: Handle value domain
	}   

	theAttribute.Update();

	//TODO: Tagged vale for format
	//TODO: Tagged vale for pattern
	//TODO: Tagged vale for comment
	
	return theAttribute
}
 
function deleteAllElements(thePackage)
//Delete all existing elements in a package, return emtpy elements collection
{
	var el as EA.Element
	for ( var i = 0 ; i < thePackage.Elements.Count ; i++ )
	{
		el = thePackage.Elements.GetAt(i);
		Repository.WriteOutput("Script", new Date().toLocaleTimeString() + " Delete element: " + el.Name, 0);
		thePackage.Elements.DeleteAt(i, false);
	}
	thePackage.Elements.Refresh();
	return thePackage.Elements;
}
 
function getSelectedPackage() 
//Get the selected package, or break if not a package
{
	var contextObjectType = Repository.GetContextItemType();
	if ( contextObjectType == EA.ObjectType.otPackage )
	{
		var thePackage as EA.Package;
		thePackage = Repository.GetContextObject();
		Repository.WriteOutput("Script", new Date().toLocaleTimeString() + " Package: " + thePackage.Name, 0);
		return thePackage;
	}
	else
	{
		Session.Prompt( "This script requires a package to be selected.\n" + "Please select a package and try again.", System.PromptType.promptOK );
		return null;
	}
}
 
function outputTabs()
{
	// TODO: Show clean output tabs
	Repository.EnsureOutputVisible("Script"); 
	Repository.ClearOutput("Script");
	Repository.CreateOutputTab("Error");
	Repository.ClearOutput("Error");
	Repository.CreateOutputTab("Changes");
	Repository.ClearOutput("Changes");
}


//var eaP as EA.Package
//eaP = getSelectedPackage();