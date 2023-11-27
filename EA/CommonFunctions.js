!INC Local Scripts.EAConstants-JavaScript
!INC OvertureMaps.Parameters


/*
 * Script Name: CommonFunctions
 * Author: Knut Jetlund
 * Purpose: Common functions for OvertureMaps schema conversion
 * Date: 20231123
 */
 
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

outputTabs();