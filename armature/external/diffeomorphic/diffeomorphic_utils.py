# SPDX-FileCopyrightText: 2016-2026, Thomas Larsson
#
# SPDX-License-Identifier: GPL-2.0-or-later

import bpy
from math import pi

D = pi/180

#-------------------------------------------------------------
#   Blender 5
#-------------------------------------------------------------

if bpy.app.version < (5,0,0):
    def P2B(pb):
        return pb.bone
else:
    def P2B(pb):
        return pb

#-------------------------------------------------------------
#   Action slots
#-------------------------------------------------------------

if bpy.app.version < (4,4,0):

    def getActionBag(act, id_type='OBJECT'):
        return act

    def getActionFcurves(act, id_type='OBJECT'):
        if act:
            return act.fcurves
        else:
            return []

    def getRnaFcurves(rna, id_type='OBJECT'):
        if rna.animation_data and rna.animation_data.action:
            return rna.animation_data.action.fcurves
        else:
            return []

    def setNewAction(rna, aname):
        if rna.animation_data is None:
            rna.animation_data_create()
        act = bpy.data.actions.new(name=aname)
        rna.animation_data.action = act
        return act

else:

    def getActionBag(act, id_type='OBJECT'):
        if act and act.layers:
            strip = act.layers[0].strips[0]
            for slot in act.slots:
                if slot.target_id_type == id_type:
                    return strip.channelbag(slot, ensure=True)

    def getActionFcurves(act, id_type='OBJECT'):
        bag = getActionBag(act, id_type)
        if bag:
            return bag.fcurves
        else:
            return []

    def getRnaFcurves(rna):
        if rna.animation_data and rna.animation_data.action:
            return getActionFcurves(rna.animation_data.action, rna.id_type)
        else:
            return []

    def setNewAction(rna, aname):
        if rna.animation_data is None:
            rna.animation_data_create()
        act = bpy.data.actions.new(name=aname)
        rna.animation_data.action = act
        if rna.id_type == 'OBJECT':
            path = "location"
        elif rna.id_type == 'KEY':
            path = 'key_blocks[0].value'
        rna.keyframe_insert(path)
        rna.keyframe_delete(path)
        return act

#-------------------------------------------------------------
#   Blender 4
#-------------------------------------------------------------

def setRigLayer(rig, layer, value):
    if bpy.app.version < (4,0,0):
        rig.data.layers[layer] = value
    else:
        coll = rig.data.collections.get(layer)
        if coll:
            coll.is_visible = value

#-------------------------------------------------------------
#   Utility functions
#-------------------------------------------------------------

def propRef(prop):
    return '["%s"]' % prop

def isPropRef(prop):
    return (prop[0:2] == '["' and prop[-2:] == '"]')

def baseRef(prop):
    if isPropRef(prop):
        return prop[2:-2]
    else:
        return prop

def isKeyed(rig, pb, channel):
    fcurves = getRnaFcurves(rig)
    if fcurves and pb:
        path = ('pose.bones["%s"].%s' % (pb.name, channel))
        for fcu in fcurves:
            if fcu.data_path == path:
                return True
    return False


def isDrvBone(string):
    return (string[-3:] == "Drv" or string[-5:] == "(drv)")

#-------------------------------------------------------------
#   Progress
#-------------------------------------------------------------

def startProgress(string):
    print(string + " (0%)")
    wm = bpy.context.window_manager
    wm.progress_begin(0, 100)

def endProgress(string):
    print(string + " (100%)")
    wm = bpy.context.window_manager
    wm.progress_end()

def showProgress(n, frame, nFrames, step=20):
    pct = (100.0*n)/nFrames
    if n % step == 0:
        print("%d (%.1f " % (int(frame), pct) + "%)")
    wm = bpy.context.window_manager
    wm.progress_update(int(pct))

#-------------------------------------------------------------
#   Error handling
#-------------------------------------------------------------

def clearErrorMessage():
    global theMessage, theErrorLines
    theMessage = ""
    theErrorLines = []

clearErrorMessage()

def getErrorMessage():
    """getErrorMessage()

    Returns:
    The error message from previous operator invokation if it raised
    an error, or the empty string if the operator exited without errors.
    """
    global theMessage
    return theMessage


def getSilentMode():
    global theSilentMode
    return theSilentMode

def setSilentMode(value):
    """setSilentMode(value)

    In silent mode, operators fail silently if they encounters an error.
    This is useful for scripting.

    value: True turns silent mode on, False turns it off.
    """
    global theSilentMode
    theSilentMode = value

setSilentMode(False)


class MhxError(Exception):
    def __init__(self, value):
        global theErrorLines, theMessage
        theMessage = value
        theErrorLines = (
            theMessage.split("\n")
            )
        print("*** MHX Error ***")
        for line in theErrorLines:
            print(line)

    def __str__(self):
        return repr(theMessage)


class MhxMessage(Exception):
    def __init__(self, value):
        global theErrorLines, theMessage
        theMessage = value
        theErrorLines = theMessage.split("\n")
        print(theMessage)


def displayMessage(msg):
    #raise MhxMessage(msg)
    print(msg)


class MhxPopup(bpy.types.Operator):
    def execute(self, context):
        return {'RUNNING_MODAL'}

    def invoke(self, context, event):
        wm = context.window_manager
        wm.progress_end()
        return wm.invoke_props_dialog(self)

    def draw(self, context):
        global theErrorLines
        for line in theErrorLines:
            self.layout.label(text=line)


class ErrorOperator(MhxPopup):
    bl_idname = "mhx.error"
    bl_label = "MHX Error"


class MessageOperator(MhxPopup):
    bl_idname = "mhx.message"
    bl_label = "MHX"


def checkVisible(rig):
    if not (rig and rig.visible_get()):
        raise MhxError("%s is not visible in viewport" % rig.name)


def setMode(mode, errmsg=None):
    try:
        bpy.ops.object.mode_set(mode=mode)
    except RuntimeError as err:
        if errmsg:
            err = errmsg
        raise MhxError(str(err))

#-------------------------------------------------------------
#   Execute
#-------------------------------------------------------------

class MhxOperator(bpy.types.Operator):
    def execute(self, context):
        clearErrorMessage()
        self.prequel(context)
        try:
            self.run(context)
        except MhxError:
            if getSilentMode():
                print(theMessage)
            else:
                bpy.ops.mhx.error('INVOKE_DEFAULT')
        except MhxMessage:
            if getSilentMode():
                print(theMessage)
            else:
                bpy.ops.mhx.message('INVOKE_DEFAULT')
        except KeyboardInterrupt:
            global theErrorLines
            theErrorLines = ["Keyboard interrupt"]
            bpy.ops.mhx.error('INVOKE_DEFAULT')
        finally:
            self.sequel(context)
        return{'FINISHED'}

    def prequel(self, context):
        return None

    def sequel(self, context):
        pass

    def run(self, context):
        pass



class MhxPropsOperator(MhxOperator):
    def invoke(self, context, event):
        clearErrorMessage()
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

#-------------------------------------------------------------
#   HideOperator class
#-------------------------------------------------------------

def getSelectedObjects(context):
    return [ob for ob in context.view_layer.objects
        if ob.select_get() and not (ob.hide_get() or ob.hide_viewport)]


class HideOperator(MhxOperator):

    def prequel(self, context):
        self.rig = context.object
        self.mode = self.rig.mode
        try:
            bpy.ops.object.mode_set(mode='OBJECT')
        except RuntimeError:
            pass
        scn = context.scene
        self.frame = scn.frame_current
        if bpy.app.version < (4,0,0):
            self.state = list(self.rig.data.layers)
            self.rig.data.layers = 32*[True]
        else:
            self.state = {}
            for coll in self.rig.data.collections:
                self.state[coll.name] = coll.is_visible
                coll.is_visible = True
        self.hideStatus = {}
        self.layerColls = []
        self.hideLayerColls(context.view_layer.layer_collection)


    def sequel(self, context):
        if bpy.app.version < (4,0,0):
            self.rig.data.layers = self.state
        else:
            for coll in self.rig.data.collections:
                coll.is_visible = self.state[coll.name]
        for layer in self.layerColls:
            layer.exclude = False
        for ob,select,hide,viewport,render in self.hideStatus.values():
            ob.hide_set(hide)
            ob.hide_viewport = viewport
            ob.hide_render = render
            ob.select_set(select)
        try:
            bpy.ops.object.mode_set(mode=self.mode)
        except RuntimeError:
            pass


    def hideLayerColls(self, layer):
        if layer.exclude:
            return True
        ok = True
        for ob in layer.collection.objects:
            if ob == self.rig:
                ok = False
            elif ob.name not in self.hideStatus.keys():
                self.hideStatus[ob.name] = (ob, ob.select_get(), ob.hide_get(), ob.hide_viewport, ob.hide_render)
                ob.hide_set(True)
                ob.hide_viewport = True
                ob.hide_render = True
        for child in layer.children:
            ok = (self.hideLayerColls(child) and ok)
        if ok:
            self.layerColls.append(layer)
            layer.exclude = True
        return ok


class HidePropsOperator(HideOperator):
    def invoke(self, context, event):
        clearErrorMessage()
        wm = context.window_manager
        return wm.invoke_props_dialog(self)