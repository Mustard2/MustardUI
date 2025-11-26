import bpy
from ..model_selection.active_object import *
from .. import __package__ as base_package
import os
import re

face_rig_current_version = 2

fctrl_bones = ['face_Controls_XYZ', 'r_Mouth_Corner', 'l_Mouth_Corner', 'Mouth_Press_Top', 'Lips_Funnel_R', 'r_Dimple',
               'l_Dimple', 'r_Mouth_Down', 'r_Mouth_Up', 'Mouth', 'l_Mouth_Down', 'l_Mouth_Up', 'r_Squint', 'r_Eyelid',
               'r_Blink', 'l_Squint', 'l_Eyelid', 'l_Blink', 'Eyes', 'r_Nose', 'l_Nose', 'Jaw', 'Jaw_In', 'Jaw_Out',
               'Mouth_Close', 'r_Cheek', 'l_Cheek', 'r_Puff', 'l_Puff', 'r_Brow_Down', 'r_Brow_Up', 'l_Brow_Down',
               'l_Brow_Up', 'Nostrils_Dilate', 'Mouth_Press_Bottom', 'Lips_Funnel_L', 'Mouth_Shrug_Upper',
               'Mouth_Shrug_Lower', 'r_Eye', 'l_Eye', 'r_Eyebrow_Outer', 'l_Eyebrow_Outer', 'l_Eyebrow_Inner',
               'r_Eyebrow_Inner', 'r_Eyebrow_Squeeze', 'l_Eyebrow_Squeeze']

# Bone, Shape Key, Direction, Factor, MaxDirection, OverrideNumber
data = [
    ("Lips_Funnel_L", ["facs_bs_MouthFunnelLowerLeft"], ["Z_DOWN", "Y_UP"], 100, 0.01),
    ("Lips_Funnel_L", ["facs_bs_MouthFunnelUpperLeft"], ["Z_UP", "Y_UP"], 100, 0.01),
    ("Lips_Funnel_R", ["facs_bs_MouthFunnelLowerRight"], ["Z_DOWN", "Y_UP"], 100, 0.01),
    ("Lips_Funnel_R", ["facs_bs_MouthFunnelUpperRight"], ["Z_UP", "Y_UP"], 100, 0.01),
    ("Lips_Funnel_R", ["facs_bs_MouthFunnelUpperRight"], ["Z_UP"], 100, 0.01),
    ("l_Dimple", ["facs_bs_MouthDimpleLeft"], ["X_UP"], 100, 0.01),
    ("r_Dimple", ["facs_bs_MouthDimpleRight"], ["X_UP"], 100, 0.01),
    ("l_Mouth_Up", ["facs_bs_MouthUpperUpLeft"], ["Z_UP"], 100, 0.01),
    ("r_Mouth_Up", ["facs_bs_MouthUpperUpRight"], ["Z_UP"], 100, 0.01),
    ("l_Mouth_Down", ["facs_bs_MouthLowerDownLeft"], ["Z_DOWN"], 100, 0.01),
    ("r_Mouth_Down", ["facs_bs_MouthLowerDownRight"], ["Z_DOWN"], 100, 0.01),
    ("l_Blink", ["facs_bs_EyeBlinkLeft"], ["Z_DOWN"], 100, 0.01),  # Bones needed
    ("r_Blink", ["facs_bs_EyeBlinkRight"], ["Z_DOWN"], 100, 0.01),  # Bones needed
    ("l_Eyelid", ["facs_ctrl_EyeWideLeft"], ["Z_UP"], 100, 0.01),
    ("r_Eyelid", ["facs_ctrl_EyeWideRight"], ["Z_UP"], 100, 0.01),
    ("l_Squint", ["facs_bs_EyeSquintLeft"], ["Z_UP"], 100, 0.01),
    ("r_Squint", ["facs_bs_EyeSquintRight"], ["Z_UP"], 100, 0.01),
    ("l_Eyebrow_Inner", ["facs_bs_BrowInnerUpLeft"], ["Z_UP"], 100, 0.01),
    ("r_Eyebrow_Inner", ["facs_bs_BrowInnerUpRight"], ["Z_UP"], 100, 0.01),
    ("l_Brow_Down", ["facs_BrowDownLeft"], ["Z_DOWN"], 100, 0.01),
    ("r_Brow_Down", ["facs_BrowDownRight"], ["Z_DOWN"], 100, 0.01),
    ("l_Eyebrow_Outer", ["facs_BrowOuterUpLeft"], ["Z_UP"], 100, 0.01),
    ("r_Eyebrow_Outer", ["facs_BrowOuterUpRight"], ["Z_UP"], 100, 0.01),
    ("l_Eyebrow_Squeeze", ["facs_bs_BrowSqueezeLeft"], ["Y_DOWN"], 200, 0.01),
    ("r_Eyebrow_Squeeze", ["facs_bs_BrowSqueezeRight"], ["Y_DOWN"], 200, 0.01),
    ("Mouth_Shrug_Upper", ["facs_bs_MouthShrugUpperLeft", "facs_bs_MouthShrugUpperRight"], ["Z_UP"], 100, 0.01),
    ("Mouth_Shrug_Lower", ["facs_bs_MouthShrugLowerLeft", "facs_bs_MouthShrugLowerRight"], ["Z_UP"], 100, 0.01),
    ("l_Cheek", ["facs_bs_CheekSquintLeft"], ["Z_UP"], 100, 0.01),
    ("r_Cheek", ["facs_bs_CheekSquintRight"], ["Z_UP"], 100, 0.01),
    ("l_Nose", ["facs_bs_NoseSneerLeft", "facs_bs_NoseSneerUpperLeft"], ["Z_UP"], 100, 0.01),
    ("r_Nose", ["facs_bs_NoseSneerRight", "facs_bs_NoseSneerUpperRight"], ["Z_UP"], 100, 0.01),
    ("Nostrils_Dilate", ["facs_bs_NasalFlareLeft", "facs_bs_NasalFlareRight"], ["X_DOWN"], 100, 0.01),
    ("l_Mouth_Corner", ["facs_bs_MouthFrownLeft"], ["Z_DOWN"], 100, 0.01),
    ("r_Mouth_Corner", ["facs_bs_MouthFrownRight"], ["Z_DOWN"], 100, 0.01),
    ("l_Mouth_Corner", ["facs_bs_MouthSmileLeft"], ["Z_UP"], 100, 0.01, 1),
    ("r_Mouth_Corner", ["facs_bs_MouthSmileRight"], ["Z_UP"], 100, 0.01, 1),
    ("l_Mouth_Corner", ["facs_bs_MouthSmileWidenLeft"], ["Y_DOWN"], 100, 0.01, 2),
    ("r_Mouth_Corner", ["facs_bs_MouthSmileWidenRight"], ["Y_DOWN"], 100, 0.01, 2),
    ("l_Mouth_Corner", ["facs_bs_MouthCompressLowerLeft", "facs_bs_MouthCompressUpperLeft"], ["Y_UP"], 100, 0.01, 4),
    ("r_Mouth_Corner", ["facs_bs_MouthCompressLowerRight", "facs_bs_MouthCompressUpperRight"], ["Y_UP"], 100, 0.01, 4),
    ("l_Puff", ["facs_bs_CheekPuffLeft"], ["Y_DOWN"], 100, 0.01),
    ("r_Puff", ["facs_bs_CheekPuffRight"], ["Y_DOWN"], 100, 0.01),
    ("Mouth_Press_Top", ["facs_bs_MouthPressUpperLeft"], ["Y_UP"], 100, 0.01),
    ("Mouth_Press_Top", ["facs_bs_MouthPressUpperRight"], ["Y_DOWN"], 100, 0.01, 2),
    ("Mouth_Press_Top", ["facs_bs_MouthRollUpperLeft", "facs_bs_MouthRollUpperRight"], ["Z_DOWN"], 100, 0.01, 3),
    ("Mouth_Press_Bottom", ["facs_bs_MouthPressLowerLeft"], ["Y_UP"], 100, 0.01),
    ("Mouth_Press_Bottom", ["facs_bs_MouthPressLowerRight"], ["Y_DOWN"], 100, 0.01, 2),
    ("Mouth_Press_Bottom", ["facs_bs_MouthRollLowerLeft", "facs_bs_MouthRollLowerRight"], ["Z_UP"], 100, 0.01, 3),
    ("Jaw", ["facs_bs_JawOpen"], ["Z_DOWN"], 100, 0.01),
    ("Jaw", ["facs_bs_JawLeft", "facs_bs_JawClenchLeft"], ["Y_UP"], 100, 0.01),
    ("Jaw", ["facs_bs_JawRight", "facs_bs_JawClenchRight"], ["Y_DOWN"], 100, 0.01),
    ("Jaw_In", ["facs_bs_JawRecess"], ["X_UP"], 100, 0.01),
    ("Jaw_Out", ["facs_bs_JawForward"], ["X_DOWN"], 100, 0.01),
    ("Mouth", ["facs_bs_MouthLeft"], ["Y_UP"], 100, 0.01),
    ("Mouth", ["facs_bs_MouthRight"], ["Y_DOWN"], 100, 0.01, 2),
    ("Mouth", ["facs_bs_MouthUp-Down"], ["Z_UP"], 100, 0.01, 3),
    ("Mouth", ["facs_bs_MouthPurseLowerLeft", "facs_bs_MouthPurseLowerRight", "facs_bs_MouthPurseUpperLeft",
               "facs_bs_MouthPurseUpperRight"], ["SCALE_DOWN"], 4, 0.01, 4),
    ("Mouth_Close", ["facs_bs_MouthCloseLowerLeft", "facs_bs_MouthCloseLowerRight", "facs_bs_MouthCloseUpperLeft",
                     "facs_bs_MouthCloseUpperRight"], ["Z_UP"], 100, 0.01)
]


def find_direction(dir):
    direction = ""
    if not "SCALE" in dir:
        if "X_" in dir:
            direction = "LOC_X"
        elif "Y_" in dir:
            direction = "LOC_Y"
        elif "Z_" in dir:
            direction = "LOC_Z"
    else:
        direction = "SCALE_AVG"

    sign = ""
    if "_DOWN" in dir:
        sign = "+"
    elif "_UP" in dir:
        sign = "-"

    return (direction, sign)


def compute_fixes(driver, var_out, armature, bone, sk, fac):
    expression = ""
    if (bone == "Mouth_Close" and ("facs_bs_MouthCloseLowerLeft" in sk or "facs_bs_MouthCloseLowerRight" in sk or
                                   "facs_bs_MouthCloseUpperLeft" in sk or "facs_bs_MouthCloseUpperRight" in sk)):
        # Create a new variable for the driver
        var = driver.variables.new()
        var.name = f"fcd_fix"  # Name for the variable
        var.type = 'TRANSFORMS'

        # Set the target object and property for the variable
        var.targets[0].id = armature  # Target object (armature)
        var.targets[0].bone_target = "Jaw"  # Target bone
        var.targets[0].transform_type = "LOC_Z"  # Transformation type (e.g., LOC_X, LOC_Y, LOC_Z)
        var.targets[0].transform_space = "LOCAL_SPACE"  # Local space for bone transform

        expression = f"+{str(fac)}*min(-{var_out.name},{var.name})"
    elif bone == "Mouth_Press_Top" and "facs_bs_MouthRollUpperLeft" in sk:
        # Create a new variable for the driver
        var = driver.variables.new()
        var.name = f"fcd_fix"  # Name for the variable
        var.type = 'TRANSFORMS'

        # Set the target object and property for the variable
        var.targets[0].id = armature  # Target object (armature)
        var.targets[0].bone_target = bone  # Target bone
        var.targets[0].transform_type = "LOC_Y"  # Transformation type (e.g., LOC_X, LOC_Y, LOC_Z)
        var.targets[0].transform_space = "LOCAL_SPACE"  # Local space for bone transform

        expression = f"-{str(fac)}*100*{var_out.name}*{var.name}+50*{var_out.name}"
    elif bone == "Mouth_Press_Top" and "facs_bs_MouthRollUpperRight" in sk:
        # Create a new variable for the driver
        var = driver.variables.new()
        var.name = f"fcd_fix"  # Name for the variable
        var.type = 'TRANSFORMS'

        # Set the target object and property for the variable
        var.targets[0].id = armature  # Target object (armature)
        var.targets[0].bone_target = bone  # Target bone
        var.targets[0].transform_type = "LOC_Y"  # Transformation type (e.g., LOC_X, LOC_Y, LOC_Z)
        var.targets[0].transform_space = "LOCAL_SPACE"  # Local space for bone transaform

        expression = f"+{str(fac)}*100*{var_out.name}*{var.name}+50*{var_out.name}"
    elif bone == "Mouth_Press_Bottom" and "facs_bs_MouthRollLowerLeft" in sk:
        # Create a new variable for the driver
        var = driver.variables.new()
        var.name = f"fcd_fix"  # Name for the variable
        var.type = 'TRANSFORMS'

        # Set the target object and property for the variable
        var.targets[0].id = armature  # Target object (armature)
        var.targets[0].bone_target = bone  # Target bone
        var.targets[0].transform_type = "LOC_Y"  # Transformation type (e.g., LOC_X, LOC_Y, LOC_Z)
        var.targets[0].transform_space = "LOCAL_SPACE"  # Local space for bone transform

        expression = f"+{str(fac)}*100*{var_out.name}*{var.name}-100*{var_out.name}"
    elif bone == "Mouth_Press_Bottom" and "facs_bs_MouthRollLowerRight" in sk:
        # Create a new variable for the driver
        var = driver.variables.new()
        var.name = f"fcd_fix"  # Name for the variable
        var.type = 'TRANSFORMS'

        # Set the target object and property for the variable
        var.targets[0].id = armature  # Target object (armature)
        var.targets[0].bone_target = bone  # Target bone
        var.targets[0].transform_type = "LOC_Y"  # Transformation type (e.g., LOC_X, LOC_Y, LOC_Z)
        var.targets[0].transform_space = "LOCAL_SPACE"  # Local space for bone transform

        expression = f"-{str(fac)}*100*{var_out.name}*{var.name}-100*{var_out.name}"

    return expression


class MustardUI_ToolsCreators_FaceController(bpy.types.Operator):
    """Add a Face Controller rig to the model.\nIf another controller is available on the model, the tool can not is disabled"""
    bl_idname = "mustardui.tools_creators_face_controller"
    bl_label = "Add Face Controller"
    bl_options = {"REGISTER", "UNDO"}

    head_bone: bpy.props.StringProperty(default="",
                                        name="Head Bone",
                                        description="Head bone to parent the face controller to")

    add_to_armature_panel: bpy.props.BoolProperty(default=True,
                                                  name="Add Collection to Armature Panel")

    @classmethod
    def poll(cls, context):

        res, arm = mustardui_active_object(context, config=1)
        if arm is None:
            return False

        rig_settings = arm.MustardUI_RigSettings
        model_armature = rig_settings.model_armature_object

        # Check if the face controller rig is already available
        for b in [x[0] for x in data]:
            if b in model_armature.pose.bones:
                return False

        return res

    def execute(self, context):

        res, arm = mustardui_active_object(context, config=1)
        rig_settings = arm.MustardUI_RigSettings
        model_armature = rig_settings.model_armature_object

        addon_prefs = context.preferences.addons[base_package].preferences

        script_file = os.path.realpath(__file__)
        directory = os.path.dirname(script_file)
        blend_file = directory + '/resources/face_controller.blend'
        collection_name = 'Face Controller'

        # Check if blend_file is set
        if not os.path.exists(blend_file):
            self.report({'ERROR'}, "MustardUI - An error occurred while appending the face controller rig.")
            return {'CANCELLED'}

        try:
            object_filepath = os.path.join(blend_file, "Collection", collection_name)

            bpy.ops.wm.append(
                filepath=object_filepath,
                directory=os.path.join(blend_file, "Collection"),
                filename=collection_name
            )
            appended_object = context.scene.objects[collection_name]
            if appended_object is None or appended_object.type != "ARMATURE":
                self.report({'ERROR'}, f"MustardUI - An error occurred while appending the face controller rig.")
                return {'FINISHED'}

            # Move the Armature
            head_bone = model_armature.pose.bones.get(self.head_bone)
            if head_bone is not None:
                neckhead_world_position = model_armature.matrix_world @ head_bone.head
                appended_object.location[2] = neckhead_world_position[2]

            # Join armatures
            bpy.context.view_layer.objects.active = model_armature
            appended_object.select_set(True)
            model_armature.select_set(True)

            bpy.ops.object.join()

            # Parent the face controller to the head bone
            bpy.context.view_layer.objects.active = model_armature
            bpy.ops.object.mode_set(mode='EDIT')
            head_bone = model_armature.data.edit_bones.get('head')
            face_controls_bone = model_armature.data.edit_bones.get('face_Controls_XYZ')

            if not head_bone or not face_controls_bone:
                self.report({'ERROR'}, "'head' or 'face_controls_XYZ' bone not found in the armature.")
                bpy.ops.object.mode_set(mode='OBJECT')  # Switch back to object mode if an error occurs
                return {'CANCELLED'}

            face_controls_bone.parent = head_bone
            bpy.ops.object.mode_set(mode='POSE')

            # Add Controller setup
            ctrl_added = 0
            for d in data:
                bone = d[0]
                sks = d[1]
                dirs = d[2]
                fac = d[3]

                num = 0 if len(d) < 6 else d[5]

                for sk in sks:

                    # Genesis 8 naming fix
                    if sk + "(fin)" not in model_armature.data.keys() and sk + "_div2(fin)" in model_armature.data.keys():
                        sk = sk + "_div2"
                    elif sk + "(fin)" not in model_armature.data.keys():
                        continue

                    for dir in dirs:

                        direction, sign = find_direction(dir)

                        # Check if there are any existing drivers for this shape key
                        driver = None
                        for dr in model_armature.data.animation_data.drivers:
                            if dr.data_path == f'["{sk}(fin)"]':
                                # We found the existing driver for this shape key, so use it
                                driver = dr.driver
                                break

                        if driver is None:
                            # No driver exists, so add one for the shape key's value property
                            driver = model_armature.data.driver_add(f'["{sk}(fin)"]').driver

                        # Remove any variables with "fcd" in the name
                        variables_to_remove = [var for var in driver.variables if
                                               f"fcd{str(num)}" in var.name or "fcd_fix" in var.name]
                        for var in variables_to_remove:
                            driver.variables.remove(var)

                        # Create a new variable for the driver
                        var = driver.variables.new()
                        var.name = f"fcd{num}"  # Name for the variable
                        var.type = 'TRANSFORMS'

                        # Set the target object and property for the variable
                        var.targets[0].id = model_armature  # Target object (armature)
                        var.targets[0].bone_target = bone  # Target bone
                        var.targets[0].transform_type = direction  # Transformation type (e.g., LOC_X, LOC_Y, LOC_Z)
                        var.targets[0].transform_space = "LOCAL_SPACE"  # Local space for bone transform

                        # Get the current driver expression
                        current_expression = driver.expression.strip()

                        fixed_expression = compute_fixes(driver, var, model_armature, bone, sk, fac)

                        term_to_add = f"{sign}{fac}*fcd{str(num)}" if "SCALE" not in direction else f"{sign}{fac}*(1-fcd{str(num)})"
                        if fixed_expression != "":
                            term_to_add = fixed_expression
                        if term_to_add not in current_expression:
                            # Append the term only if it doesn't already exist in the expression
                            if current_expression:
                                driver.expression = f"{current_expression}{term_to_add}"
                            else:
                                driver.expression = term_to_add

                        num += 1
                        ctrl_added += 1

            bpy.ops.object.mode_set(mode='OBJECT')

            if self.add_to_armature_panel:
                face_found = False
                for bcoll in arm.collections_all:
                    if bcoll.name == "Face Controllers":
                        bcoll_settings = bcoll.MustardUI_ArmatureBoneCollection
                        bcoll_settings.is_in_UI = True
                        bcoll_settings.icon = "USER"
                    elif bcoll.name == "Face":
                        face_found = True

                if face_found:
                    index_face = arm.collections.find("Face")
                    index = arm.collections.find("Face Controllers")

                    while index > index_face + 1:
                        arm.collections.move(index, index - 1)
                        index = arm.collections.find("Face Controllers")

            if addon_prefs.debug:
                self.report({'INFO'}, f"MustardUI - Controller successfully added to the model (controls added: " + str(
                    ctrl_added) + ").")
            else:
                self.report({'INFO'},
                            f"MustardUI - Controller successfully added to the model.")
            return {'FINISHED'}

        except Exception as e:
            self.report({'ERROR'}, f"MustardUI - Error appending object: {str(e)}")
            return {'CANCELLED'}

    def invoke(self, context, event):
        res, arm = mustardui_active_object(context, config=1)
        rig_settings = arm.MustardUI_RigSettings
        model_armature = rig_settings.model_armature_object

        head_bone = model_armature.pose.bones.get('head')
        if head_bone is not None:
            self.head_bone = 'head'
        else:
            self.head_bone = ''

        return context.window_manager.invoke_props_dialog(self, width=300)

    def draw(self, context):

        res, arm = mustardui_active_object(context, config=1)
        rig_settings = arm.MustardUI_RigSettings
        model_armature = rig_settings.model_armature_object

        layout = self.layout
        layout.prop_search(self, "head_bone", model_armature.pose, "bones")
        layout.prop(self, "add_to_armature_panel")


class MustardUI_ToolsCreators_FaceController_Remove(bpy.types.Operator):
    """Remove a Face Controller rig to the model"""
    bl_idname = "mustardui.tools_creators_face_controller_remove"
    bl_label = "Remove Face Controller"
    bl_options = {"REGISTER", "UNDO"}

    head_bone: bpy.props.StringProperty(default="",
                                        name="Head Bone",
                                        description="Head bone to parent the face controller to")

    @classmethod
    def poll(cls, context):

        res, arm = mustardui_active_object(context, config=1)
        if arm is None:
            return False

        rig_settings = arm.MustardUI_RigSettings
        model_armature = rig_settings.model_armature_object

        # Check if the face controller rig is already available
        # The "Squeeze" is a fix to allow old facial rigs to be removed (version 2)
        for b in [x[0] for x in data if "Squeeze" not in x[0]]:
            if b not in model_armature.pose.bones:
                return False

        return res

    def execute(self, context):

        res, arm = mustardui_active_object(context, config=1)
        rig_settings = arm.MustardUI_RigSettings
        model_armature = rig_settings.model_armature_object

        addon_prefs = context.preferences.addons[base_package].preferences

        # Clean drivers
        for dr in model_armature.data.animation_data.drivers:
            driver = dr.driver

            if driver is None:
                continue

            # Remove variables related to fcd or fcd_fix
            variables_to_remove = [var for var in driver.variables if
                                   "fcd" in var.name or "fcd_fix" in var.name]

            # Also remove variables related to bones in fctrl_bones list
            for var in driver.variables:
                if var.type != 'TRANSFORMS':
                    continue
                for target in var.targets:
                    if any(target.id == model_armature and bone == target.bone_target for bone in fctrl_bones):
                        if var not in variables_to_remove:
                            variables_to_remove.append(var)

            if not variables_to_remove:
                continue

            if addon_prefs.debug:
                print(f"MustardUI - Working on driver '{dr.data_path}'...")
                for v in [var.name for var in variables_to_remove]:
                    print(f"MustardUI - Variables '{v}' to be deleted from '{dr.data_path}'.")

            # Remove variables from current expression
            current_expression = driver.expression.strip()
            if addon_prefs.debug:
                print(f"MustardUI - Expression before removal: {current_expression}'.")
            for v in [var.name for var in variables_to_remove]:
                if 'fcd' in var.name:
                    pattern = rf'([+\-]?\s*\d*\.?\d*)\s?\*(?:\s*\d*\.?\d*\s?\*)*\s?(min\([^\)]+fcd[^\)]+[^\)]+fcd[^\)]+\)|\w*fcd\w*(\*\w*fcd\w*)*|\([^\)]+fcd[^\)]+\))'
                    current_expression = re.sub(pattern, lambda m: "" if m.group(0).strip() else "", current_expression)
                pattern = rf'([+\-]?\s*\d*\.?\d*)\s?\*\s?\(?\s?([a-zA-Z0-9_]+|{re.escape(v)}\d+)\s?\)?'
                current_expression = re.sub(pattern, lambda m: "" if m.group(0).strip() else "", current_expression)
            if addon_prefs.debug:
                print(f"MustardUI - Expression before removal: {current_expression.strip()}'.")
            driver.expression = current_expression.strip()

            # Remove variables
            for var in variables_to_remove:
                driver.variables.remove(var)

            # After removing variables, check if any variables remain
            if len(driver.variables) == 0:
                model_armature.data.animation_data.drivers.remove(driver)

        bpy.context.view_layer.objects.active = model_armature
        bpy.ops.object.mode_set(mode='EDIT')

        # Remove appended bones
        for bone_name in fctrl_bones:
            if bone_name in model_armature.data.edit_bones:
                bone = model_armature.data.edit_bones[bone_name]
                model_armature.data.edit_bones.remove(bone)
                if addon_prefs.debug:
                    print(f"MustardUI - Bone '{bone_name}' deleted'.")
            else:
                if addon_prefs.debug:
                    print(f"MustardUI - Bone '{bone_name}' not found'.")

        # Finally remove the Bone Collections
        for brm in ["Face Controllers", "Face Controllers Not Implemented"]:
            for bcoll in arm.collections_all:
                if bcoll.name == brm:
                    arm.collections.remove(bcoll)
                    break

        # Return to Object Mode
        bpy.ops.object.mode_set(mode='OBJECT')

        # Set the face rig version
        rig_settings.creator_tools_face_rig_version = face_rig_current_version

        self.report({'INFO'}, "MustardUI - Controller successfully removed from the model.")

        return {'FINISHED'}


def register():
    bpy.utils.register_class(MustardUI_ToolsCreators_FaceController)
    bpy.utils.register_class(MustardUI_ToolsCreators_FaceController_Remove)


def unregister():
    bpy.utils.unregister_class(MustardUI_ToolsCreators_FaceController_Remove)
    bpy.utils.unregister_class(MustardUI_ToolsCreators_FaceController)
