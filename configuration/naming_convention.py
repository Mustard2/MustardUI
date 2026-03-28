import bpy


def get_naming_convention_prefix(collection_name):
    return f"{collection_name} - "


# Object: Remove the Naming Convention part from the name
def strip_naming_convention(string, collection_name, naming_convention):
    return string[len(get_naming_convention_prefix(collection_name)):] if naming_convention else string


# Collection: Remove the Naming Convention part from the name
def strip_naming_convention_collection(string, collection_name, naming_convention):
    return string[len(collection_name + " "):] if naming_convention else string

