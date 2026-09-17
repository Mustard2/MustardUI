# Function to check if two strings can be considered one the mirror of the other
# It checks the left and the right separately (left refers to name1)
def check_mirror(name1, name2, left=True):
    if left:
        return (
            (name1.lower().endswith(".l") and name2.lower() == name1[:-2].lower() + ".r")
            or (name1.lower().startswith("l_") and name2.lower() == "r_" + name1[2:].lower())
            or (name1.lower().endswith("_l") and name2.lower() == name1[:-2].lower() + "_r")
            or (name1.lower().startswith("left") and name2.lower() == "right" + name1[4:].lower())
            or (name1.lower().endswith("left") and name2.lower() == name1[:-4].lower() + "right")
        )

    else:
        return (
            (name1.lower().endswith(".r") and name2.lower() == name1[:-2].lower() + ".l")
            or (name1.lower().startswith("r_") and name2.lower() == "l_" + name1[2:].lower())
            or (name1.lower().endswith("_r") and name2.lower() == name1[:-2].lower() + "_l")
            or (name1.lower().startswith("right") and name2.lower() == "left" + name1[5:].lower())
            or (name1.lower().endswith("right") and name2.lower() == name1[:-5].lower() + "left")
        )


# Lowercase names that check_mirror considers the mirror of name
def mirror_candidates(name, left=True):
    lower = name.lower()
    candidates = []

    if left:
        if lower.endswith(".l"):
            candidates.append(name[:-2].lower() + ".r")
        if lower.startswith("l_"):
            candidates.append("r_" + name[2:].lower())
        if lower.endswith("_l"):
            candidates.append(name[:-2].lower() + "_r")
        if lower.startswith("left"):
            candidates.append("right" + name[4:].lower())
        if lower.endswith("left"):
            candidates.append(name[:-4].lower() + "right")
    else:
        if lower.endswith(".r"):
            candidates.append(name[:-2].lower() + ".l")
        if lower.startswith("r_"):
            candidates.append("l_" + name[2:].lower())
        if lower.endswith("_r"):
            candidates.append(name[:-2].lower() + "_l")
        if lower.startswith("right"):
            candidates.append("left" + name[5:].lower())
        if lower.endswith("right"):
            candidates.append(name[:-5].lower() + "left")

    return candidates
