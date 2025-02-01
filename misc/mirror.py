import bpy


# Function to check if two strings can be consiedered one the mirror of the other
# It checks the left and the right separately (left refers to name1)
def check_mirror(name1, name2, left=True):
    if left:
        return ((name1.lower().endswith(".l") and name2.lower() == name1[:-2].lower() + ".r")
                or (name1.lower().startswith("left") and name2.lower() == "right" + name1[4:].lower())
                or (name1.lower().endswith("left") and name2.lower() == name1[:-4].lower() + "right"))

    else:
        return ((name1.lower().endswith(".r") and name2.lower() == name1[:-2].lower() + ".l")
                or (name1.lower().startswith("right") and name2.lower() == "left" + name1[5:].lower())
                or (name1.lower().endswith("right") and name2.lower() == name1[:-5].lower() + "left"))
