import bpy
import ast


def evaluate_rna(rna_path):
    # Ensure the path starts with 'bpy.'
    if not rna_path.startswith("bpy."):
        print("Invalid RNA path: must start with 'bpy.'")
        return None

    # Split the path into components
    base_name, rna_sub_path = rna_path.split('.', 1)

    # Start with the bpy module
    current_element = bpy

    # Regular expression to split the path into components, including dictionary keys
    import re
    path_parts = re.findall(r'\w+|\[.*?]', rna_sub_path)

    for i, part in enumerate(path_parts):
        if part.startswith("[") and part.endswith("]"):
            # Remove the square brackets and safely evaluate the key
            key = part[1:-1]
            key = ast.literal_eval(key)
            try:
                current_element = current_element[key]
            except (KeyError, TypeError, AttributeError):
                print(f"Key '{key}' not found in {current_element}.")
                return None
        else:
            # Attribute access
            if hasattr(current_element, part):
                current_element = getattr(current_element, part)
            else:
                print(f"Attribute '{part}' not found in {current_element}.")
                return None

    return current_element


def evaluate_path(rna, path):
    # Get the object before accessing the final attribute
    final_object = evaluate_rna(rna)

    if final_object is not None:
        # Access path attribute
        value = getattr(final_object, path, None)
    else:
        return None

    return value
