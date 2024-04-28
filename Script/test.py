# Example usage
string = "ref:../defs.yaml#/$defs/propertyDefinitions/id"
string = "ref:../defs.yaml#/$defs/propertyContainers/overtureFeaturePropertiesContainer"
string = "ref:./defs.yaml#/$defs/typeDefinitions/perspective"


# Check if the string starts with "../defs.yaml"
if string.startswith("ref:../defs.yaml"):
    print("The string starts with '../defs.yaml'.")
else:
    print("The string does not start with '../defs.yaml'.")