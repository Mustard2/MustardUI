# SPDX-FileCopyrightText: 2016-2026, Thomas Larsson
#
# SPDX-License-Identifier: GPL-2.0-or-later

import bpy
from bpy.props import *
from .utils import *
from .layers import *
from .fkik import Updater

# ---------------------------------------------------------------------
#   Convert MHX actions from legacy to modern
# ---------------------------------------------------------------------

class MHX_OT_UpdateMhxBlender4(MhxOperator):
    bl_idname = "mhx.update_mhx_blender4"
    bl_label = "Update MHX To Blender 4"
    bl_options = {'UNDO'}

    def run(self, context):
        rig = context.object
        for coll in list(rig.data.collections):
            if not coll.name.startswith("Layer "):
                rig.data.collections.remove(coll)
        for idx,cname in MhxLayers.items():
            coll = rig.data.collections.get("Layer %d" % (idx+1))
            if coll:
                coll.name = cname
        for cname in MhxLayers.values():
            if cname not in rig.data.collections.keys():
                coll = rig.data.collections.new(cname)

# ---------------------------------------------------------------------
#   Convert MHX actions from legacy to modern
# ---------------------------------------------------------------------

class MHX_OT_ConvertMhxActions(MhxOperator):
    bl_idname = "mhx.convert_mhx_actions"
    bl_label = "Convert MHX Actions"
    bl_description = "Convert actions between legacy MHX (root/hips) and modern MHX (hip/pelvis)"
    bl_options = {'UNDO'}

    direction : EnumProperty(
        items = [
            ('MODERN', "Legacy => Modern", "Convert from legacy MHX (root/hips) to modern MHX (hip/pelvis)"),
            ('LEGACY', "Modern => Legacy", "Convert from modern MHX (hip/pelvis) to legacy MHX (root/hips)"),
        ],
        name = "Direction",
        default = 'MODERN'
    )

    def draw(self, context):
        self.layout.prop(self, "direction")


    def run(self, context):
        if self.direction == 'MODERN':
            replace = {
                '"root"' : '"hip"',
                '"hips"' : '"pelvis"',
            }
        else:
            replace = {
                '"hip"' : '"root"',
                '"pelvis"' : '"hips"',
            }
        for item in self.getSelectedItems():
            act = bpy.data.actions[item.name]
            fcurves = getActionFcurves(act)
            for fcu in fcurves:
                for old,new in replace.items():
                    if old in fcu.data_path:
                        fcu.data_path = fcu.data_path.replace(old, new)


    def invoke(self, context, event):
        self.selection.clear()
        for act in bpy.data.actions:
            item = self.selection.add()
            item.name = act.name
            item.text = act.name
            item.select = False
        return self.invokeDialog(context)

#-------------------------------------------------------------
#   Enable and disable layers
#-------------------------------------------------------------

def setRigLayer(rig, layer, value):
    if bpy.app.version < (4,0,0):
        rig.data.layers[layer] = value
    else:
        coll = rig.data.collections.get(layer)
        if coll:
            coll.is_visible = value


class MHX_OT_EnableAllLayers(MhxOperator):
    bl_idname = "mhx.enable_all_layers"
    bl_label = "Enable all layers"
    bl_options = {'UNDO'}

    def run(self, context):
        rig = context.object
        if bpy.app.version < (4,0,0):
            rig.data.layers = [(idx in MhxLayers.keys() and idx not in [L_HELP, L_HELP2, L_HIDDEN, L_DEF]) for idx in range(32)]
        else:
            for coll in rig.data.collections:
                if coll.name not in [L_HELP, L_HELP2, L_HIDDEN, L_DEF]:
                    coll.is_visible = True


class MHX_OT_DisableAllLayers(MhxOperator):
    bl_idname = "mhx.disable_all_layers"
    bl_label = "Disable all layers"
    bl_options = {'UNDO'}

    def run(self, context):
        rig = context.object
        if bpy.app.version < (4,0,0):
            layers = 32*[False]
            pb = context.active_pose_bone
            if pb:
                for n in range(32):
                    if pb.bone.layers[n]:
                        layers[n] = True
                        break
            else:
                layers[0] = True
            rig.data.layers = layers
        else:
            for coll in rig.data.collections:
                coll.is_visible = False

#-------------------------------------------------------------
#   Update MHX
#-------------------------------------------------------------

class MHX_OT_UpdateMhx(MhxOperator):
    bl_idname = "mhx.update_mhx"
    bl_label = "Update MHX"
    bl_options = {'UNDO'}

    def run(self, context):
        def fixFcurve(fcu, rig):
            for var in list(fcu.driver.variables):
                trg = var.targets[0]
                prop = baseRef(trg.data_path)
                if trg.id == rig.data and prop[0:3] == "Mha" and prop in rig.data.keys():
                    value = getValue(prop, rig.data[prop])
                    if hasattr(rig, prop):
                        setattr(rig, prop, value)
                        nvar = fcu.driver.variables.new()
                        varname = var.name
                        ntrg = nvar.targets[0]
                        ntrg.id_type == 'OBJECT'
                        ntrg.id = rig
                        ntrg.data_path = propRef(prop)
                        fcu.driver.variables.remove(var)
                        nvar.name = varname
                    else:
                        rig[prop] = value
                elif trg.id == rig and prop[0:3] == "Mha" and hasattr(rig, prop):
                    value = getValue(prop, getattr(rig, prop))
                    if hasattr(rig, prop):
                        for trg in var.targets:
                            trg.data_path = propRef(prop)
                    else:
                        rig[prop] = value

        def getValue(key, value):
            if key.startswith("MhaElbowParent") and isinstance(value, int):
                return {0: 'HAND', 1: 'SHOULDER', 2: 'MASTER'}[value]
            elif key.startswith("MhaKneeParent") and isinstance(value, int):
                return {0: 'FOOT', 1: 'HIP', 2: 'MASTER'}[value]
            elif isinstance(value, bool):
                return bool(value)
            else:
                return value


        def updateCollections(rig):
            if "Layer 1" not in rig.data.collections.keys():
                for cname in MhxLayers.values():
                    if cname not in rig.data.collections.keys():
                        rig.data.collections.new(cname)
                return
            for coll in list(rig.data.collections):
                if not coll.name.startswith("Layer "):
                    rig.data.collections.remove(coll)
            for idx,cname in MhxLayers.items():
                coll = rig.data.collections.get("Layer %d" % (idx+1))
                if coll:
                    coll.name = cname
                else:
                    rig.data.collections.new(cname)

        rig = context.object
        for key in list(rig.data.keys()):
            if key[0:3] == "Mha":
                value = getValue(key, rig.data[key])
                if hasattr(rig, key):
                    setattr(rig, key, value)
                else:
                    rig[key] = value
        if rig.animation_data:
            for fcu in rig.animation_data.drivers:
                fixFcurve(fcu, rig)
        if rig.data.animation_data:
            for fcu in rig.data.animation_data.drivers:
                fixFcurve(fcu, rig)
        for key in list(rig.data.keys()):
            if key[0:3] == "Mha" and hasattr(rig, key):
                del rig.data[key]

        def addStretchDrivers():
            for suffix in ["L", "R"]:
                useStretch = False
                for bname,prop in [
                    ("shin", "MhaLegStretch"),
                    ("shin.bend", "MhaLegStretch"),
                    ("shin.twist", "MhaLegStretch"),
                    ("forearm.bend", "MhaArmStretch"),
                    ("forearm.twist", "MhaArmStretch"),
                ]:
                    pb = rig.pose.bones.get("%s.%s" % (bname, suffix))
                    prop2 = "%s_%s" % (prop, suffix)
                    if pb:
                        cns = getConstraint(pb, 'STRETCH_TO')
                        if cns:
                            cns.driver_remove("influence")
                            addDriver(cns, "influence", rig, propRef(prop2), "x")
                for bname,prop in [
                    ("foot.fk", "MhaLegStretch"),
                    ("hand.fk", "MhaArmStretch"),
                ]:
                    pb = rig.pose.bones["%s.%s" % (bname, suffix)]
                    prop2 = "%s_%s" % (prop, suffix)
                    cns = getConstraint(pb, 'COPY_LOCATION')
                    if cns:
                        cns.driver_remove("influence")
                        addDriver(cns, "influence", rig, propRef(prop2), "1-x")
                    else:
                        cns = copyLocation(pb, pb.parent, rig, prop2, "1-x")
                        cns.head_tail = 1.0

        addStretchDrivers()
        setMode('EDIT')
        for suffix in ["L", "R"]:
            for bname,conn in [
                ("hand", False),
                ("hand.fk", False),
                ("foot", False),
                ("foot.fk", False),
                ("toe", True),
                ("toe.fk", True),
            ]:
                eb = rig.data.edit_bones.get("%s.%s" % (bname, suffix))
                if eb:
                    eb.use_connect = conn

        setMode('OBJECT')
        if bpy.app.version >= (4,0,0):
            updateCollections(rig)
        rig.data["MhaFeatures"] = rig.data.get("MhaFeatures") | F_IDPROPS


def getConstraint(pb, ctype):
    for cns in pb.constraints:
        if cns.type == ctype:
            return cns
    return None

#-------------------------------------------------------------
#   Utilities from import_daz, to avoid addon interdependence
#-------------------------------------------------------------

def addDriver(rna, channel, rig, prop, expr, index=-1):
    fcu = rna.driver_add(channel, index)
    fcu.driver.type = 'SCRIPTED'
    if isinstance(prop, str):
        fcu.driver.expression = expr
        addDriverVar(fcu, "x", prop, rig)
    else:
        prop1,prop2 = prop
        fcu.driver.expression = expr
        addDriverVar(fcu, "x1", prop1, rig)
        addDriverVar(fcu, "x2", prop2, rig)


def addDriverVar(fcu, vname, path, rna, vartype='SINGLE_PROP'):
    var = fcu.driver.variables.get(vname)
    if var is None:
        var = fcu.driver.variables.new()
    var.name = vname
    var.type = vartype
    trg = var.targets[0]
    trg.id_type = getIdType(rna)
    trg.id = rna
    trg.data_path = path
    return trg


def getIdType(rna):
    if isinstance(rna, bpy.types.Armature):
        return 'ARMATURE'
    elif isinstance(rna, bpy.types.Object):
        return 'OBJECT'
    elif isinstance(rna, bpy.types.Mesh):
        return 'MESH'
    elif isinstance(rna, bpy.types.Key):
        return 'KEY'
    else:
        raise RuntimeError("BUG addDriverVar", rna)


def copyLocation(bone, target, rig, prop=None, expr="x", space='WORLD'):
    cns = bone.constraints.new('COPY_LOCATION')
    cns.name = "Copy Location %s" % target.name
    cns.target = rig
    cns.subtarget = target.name
    if prop is not None:
        addDriver(cns, "influence", rig, propRef(prop), expr)
    cns.owner_space = space
    cns.target_space = space
    return cns

#-------------------------------------------------------------
#   Unhinge
#-------------------------------------------------------------

class MHX_OT_Unhinge(MhxOperator, Updater):
    bl_idname = "mhx.unhinge"
    bl_label = "Unhinge"
    bl_description = "Remove hinges"
    bl_options = {'UNDO'}

    limb : StringProperty()
    suffix : StringProperty()

    Bones = {
        "Arm" : ["upper_arm.fk", "upper_arm.ik"],
        "Leg" : ["thigh.fk", "thigh.ik"]
    }

    Sockets = {
        "Arm" : ["armSocket", "arm_parent"],
        "Leg" : ["legSocket", "leg_parent"]
    }

    def run(self, context):
        from mathutils import Matrix
        rig = context.object
        prop = "Mha%sHinge_%s" % (self.limb, self.suffix)
        mats = []
        for bname in self.Bones[self.limb]:
            pb = rig.pose.bones.get("%s.%s" % (bname, self.suffix))
            mats.append((pb, pb.matrix.copy()))
        rig[prop] = 0.0
        self.updatePose()
        for bname in self.Sockets[self.limb]:
            pb = rig.pose.bones.get("%s.%s" % (bname, self.suffix))
            pb.matrix_basis = Matrix()
        self.updatePose()
        for pb,mat in mats:
            pb.matrix = mat
            self.updatePose()

#----------------------------------------------------------
#
#----------------------------------------------------------

classes = [
    MHX_OT_EnableAllLayers,
    MHX_OT_DisableAllLayers,
    MHX_OT_ConvertMhxActions,
    MHX_OT_UpdateMhxBlender4,
    MHX_OT_UpdateMhx,
    MHX_OT_Unhinge,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
