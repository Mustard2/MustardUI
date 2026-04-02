# SPDX-FileCopyrightText: 2016-2026, Thomas Larsson
#
# SPDX-License-Identifier: GPL-2.0-or-later

import bpy
import time
from mathutils import Vector, Matrix, Euler, Quaternion
from bpy.props import *
from .utils import *
from .layers import *
from .fkik import Snapper, Basic, Updater, FootSnapper

class HasAction:
    @classmethod
    def poll(cls, context):
        rig = context.object
        return (rig.animation_data and rig.animation_data.action)

#-------------------------------------------------------------
#   Frame range
#-------------------------------------------------------------

class FrameRange(HidePropsOperator, Updater, HasAction):
    startFrame : IntProperty(
        name = "Start Frame",
        description = "Starting frame for the animation",
        default = 1)

    endFrame : IntProperty(
        name = "Last Frame",
        description = "Last frame for the animation",
        default = 250)

    def draw(self, context):
        self.layout.prop(self, "startFrame")
        self.layout.prop(self, "endFrame")


    def getActiveFrames(self):
        def getActiveFrames0(rig):
            active = {}
            fcurves = getRnaFcurves(rig)
            for fcu in fcurves:
                for kp in fcu.keyframe_points:
                    active[kp.co[0]] = True
            return active

        active = getActiveFrames0(self.rig)
        frames = list(active.keys())
        if not frames:
            return frames
        frames.sort()
        while frames[0] < self.startFrame:
            frames = frames[1:]
        frames.reverse()
        while frames[0] > self.endFrame:
            frames = frames[1:]
        frames.reverse()
        return frames


    def invoke(self, context, event):
        rig = context.object
        fcurves = getRnaFcurves(rig)
        if fcurves:
            tmin = tmax = 1
            for fcu in fcurves:
                times = [kp.co[0] for kp in fcu.keyframe_points]
                if times:
                    tmin = min(int(min(times)), tmin)
                    tmax = max(int(max(times)), tmax)
            self.startFrame = tmin
            self.endFrame = tmax
        else:
            self.startFrame = self.endFrame = context.scene.frame_current
        return HidePropsOperator.invoke(self, context, event)


    def setInterpolation(self):
        fcurves = getRnaFcurves(rig)
        for fcu in fcurves:
            for pt in fcu.keyframe_points:
                pt.interpolation = 'LINEAR'
            fcu.extrapolation = 'CONSTANT'

#-------------------------------------------------------------
#   Limbs bend positive
#-------------------------------------------------------------

class Bender(Basic):
    useElbows : BoolProperty(
        name="Elbows",
        description="Keep elbow bending positive",
        default=True)

    useKnees : BoolProperty(
        name="Knees",
        description="Keep knee bending positive",
        default=True)

    useBendPositive : BoolProperty(
        name="Bend Positive",
        description="Ensure that elbow and knee bending is positive",
        default=True)

    def draw(self, context):
        self.layout.prop(self, "useElbows")
        self.layout.prop(self, "useKnees")

    def limbsBendPositive(self, frames):
        limbs = {}
        if self.useElbows:
            pb = self.getBone("forearm.fk.L")
            self.minimizeFCurve(pb, "rotation", 0, frames)
            pb = self.getBone("forearm.fk.R")
            self.minimizeFCurve(pb, "rotation", 0, frames)
        if self.useKnees:
            pb = self.getBone("shin.fk.L")
            self.minimizeFCurve(pb, "rotation", 0, frames)
            pb = self.getBone("shin.fk.R")
            self.minimizeFCurve(pb, "rotation", 0, frames)


    def minimizeFCurve(self, pb, channel, idx, frames):
        if pb is None:
            return
        fcu = self.findBoneFCurve(pb, channel, idx)
        if fcu is None:
            return
        y0 = fcu.evaluate(0)
        t0 = frames[0]
        t1 = frames[-1]
        for kp in fcu.keyframe_points:
            t = kp.co[0]
            if t >= t0 and t <= t1:
                y = kp.co[1]
                if y < y0:
                    kp.co[1] = y0


class MHX_OT_LimbsBendPositive(FrameRange, Bender):
    bl_idname = "mhx.limbs_bend_positive"
    bl_label = "Bend Limbs Positive"
    bl_description = "Ensure that limbs' X rotation is positive."
    bl_options = {'UNDO'}

    def draw(self, context):
        Bender.draw(self, context)
        FrameRange.draw(self, context)

    def run(self, context):
        checkVisible(context.object)
        frames = range(self.startFrame, self.endFrame+1)
        self.limbsBendPositive(frames)
        print("Limbs bent positive")

#-------------------------------------------------------------
#   Remove unused F-curves
#-------------------------------------------------------------

class MHX_OT_RemoveUnusedFcurves(MhxOperator, HasAction):
    bl_idname = "mhx.remove_unused_fcurves"
    bl_label = "Remove Unused F-curves"
    bl_description = "Remove unused f-curves"
    bl_options = {'UNDO'}

    def run(self, context):
        def trivial(fcu, default):
            for kp in fcu.keyframe_points:
                if abs(kp.co[1] - default) > 1e-4:
                    return False
            return True

        rig = context.object
        checkVisible(rig)
        fcurves = getRnaFcurves(rig)
        for fcu in list(fcurves):
            if isPropRef(fcu.data_path):
                if trivial(fcu, 0.0):
                    fcurves.remove(fcu)
                continue
            channel = fcu.data_path.rsplit(".")[-1]
            if channel in ["location", "rotation_euler"]:
                if trivial(fcu, 0.0):
                    fcurves.remove(fcu)
            elif channel == "scale":
                if trivial(fcu, 1.0):
                    fcurves.remove(fcu)
            elif channel == "rotation_quaternion":
                if fcu.array_index == 0:
                    if trivial(fcu, 1.0):
                        fcurves.remove(fcu)
                elif trivial(fcu, 0.0):
                    fcurves.remove(fcu)

#-------------------------------------------------------------
#
#-------------------------------------------------------------

class LimitEnforcer:
    def run(self, context):
        checkVisible(self.rig)
        self.initSettings(context)
        frames = self.getActiveFrames()
        for pb in self.rig.pose.bones:
            if pb.rotation_mode != 'QUATERNION':
                cns = self.getLimitRotConstraint(pb)
                if cns:
                    for idx in range(3):
                        char = chr(ord("x")+idx)
                        if getattr(cns, "use_limit_%s" % char):
                            ymin = getattr(cns, "min_%s" % char)
                            ymax = getattr(cns, "max_%s" % char)
                            self.constrainFCurve(pb, "rotation_euler", idx, ymin, ymax, frames)
                for idx in range(3):
                    if pb.lock_rotation[idx]:
                        self.constrainFCurve(pb, "rotation_euler", idx, 0.0, 0.0, frames)
            for idx in range(3):
                if pb.lock_location[idx]:
                    self.constrainFCurve(pb, "location", idx, 0.0, 0.0, frames)
                if pb.lock_scale[idx]:
                    self.constrainFCurve(pb, "scale", idx, 1.0, 1.0, frames)
        extraLocks = {
            "toe.fk.L" : (1, 2),
            "toe.fk.R" : (1, 2),
        }
        for bname, locks in extraLocks.items():
            pb = self.getBone(bname)
            for idx in locks:
                self.constrainFCurve(pb, "rotation_euler", idx, 0.0, 0.0, frames)
        self.setInterpolation()
        print("Limits enforced")


    def getLimitRotConstraint(self, pb):
        for cns in pb.constraints:
            if cns.type == 'LIMIT_ROTATION':
                return cns
        return None


class MHX_OT_EnforceLimits(LimitEnforcer, HideOperator, Basic):
    bl_idname = "mhx.enforce_limits"
    bl_label = "Enforce Limits"
    bl_description = "Keep all channels within limits"
    bl_options = {'UNDO'}

    def initSettings(self, context):
        scn = context.scene
        self.auto = scn.tool_settings.use_keyframe_insert_auto
        self.frame = scn.frame_current

    def getActiveFrames(self):
        return None

    def constrainFCurve(self, pb, channel, idx, ymin, ymax, frames):
        vec = getattr(pb, channel)
        vec[idx] = min(ymax, max(ymin, vec[idx]))
        if self.auto or isKeyed(self.rig, pb, channel):
            pb.keyframe_insert(channel, frame=self.frame, group=pb.name)

    def setInterpolation(self):
        pass


class MHX_OT_ClearIkTwistBones(HideOperator, Basic):
    bl_idname = "mhx.clear_ik_twist_bones"
    bl_label = "Clear IK Twist Bones"
    bl_description = "Clear IK twist bones"
    bl_options = {'UNDO'}

    def run(self, context):
        checkVisible(self.rig)
        self.initSettings(context)
        for suffix in ["L", "R"]:
            for bname in ["upper_arm", "forearm", "thigh", "shin"]:
                twname = "%s.ik.twist.%s" % (bname, suffix)
                pb = self.rig.pose.bones.get(twname)
                if pb:
                    if pb.rotation_mode != 'QUATERNION':
                        for idx in range(3):
                            self.setValue(pb, "rotation_euler", idx, 0.0)
                    for idx in range(3):
                        self.setValue(pb, "location", idx, 0.0)
                        self.setValue(pb, "scale", idx, 1.0)


    def initSettings(self, context):
        scn = context.scene
        self.auto = scn.tool_settings.use_keyframe_insert_auto
        self.frame = scn.frame_current


    def setValue(self, pb, channel, idx, x):
        setattr(pb, channel, (x,x,x))
        if self.auto or isKeyed(self.rig, pb, channel):
            pb.keyframe_insert(channel, frame=self.frame, group=pb.name)



class MHX_OT_EnforceAllLimits(LimitEnforcer, FrameRange, Basic):
    bl_idname = "mhx.enforce_all_limits"
    bl_label = "Enforce All Limits"
    bl_description = "Keep all channels within limits for active action"
    bl_options = {'UNDO'}

    def draw(self, context):
        FrameRange.draw(self, context)

    def initSettings(self, context):
        pass

    def constrainFCurve(self, pb, channel, idx, ymin, ymax, frames):
        fcu = self.findBoneFCurve(pb, channel, idx)
        if fcu is None:
            vec = getattr(pb, channel)
            y = vec[idx]
            if y < ymin:
                vec[idx] = ymin
            elif y > ymax:
                vec[idx] = ymax
        else:
            t0 = frames[0]
            t1 = frames[-1]
            for kp in fcu.keyframe_points:
                t = kp.co[0]
                if t >= t0 and t <= t1:
                    y = kp.co[1]
                    if y < ymin:
                        kp.co[1] = ymin
                    elif y > ymax:
                        kp.co[1] = ymax

#-------------------------------------------------------------
#   Transfer FK - IK
#-------------------------------------------------------------

class Transferer:
    useLeftArm : BoolProperty(
        name="Left",
        description="Include left arm in FK/IK snapping",
        default=False)

    useRightArm : BoolProperty(
        name="Right",
        description="Include right arm in FK/IK snapping",
        default=False)

    useLeftLeg : BoolProperty(
        name="Left",
        description="Include left arm in FK/IK snapping",
        default=True)

    useRightLeg : BoolProperty(
        name="Right",
        description="Include right arm in FK/IK snapping",
        default=True)

    useSpine : BoolProperty(
        name = "Include Spine",
        description = "Include spine in FK/IK snapping",
        default = False)

    def draw(self, context):
        row = self.layout.row()
        row.label(text="Include Arm")
        row.prop(self, "useLeftArm")
        row.prop(self, "useRightArm")
        row = self.layout.row()
        row.label(text="Include Leg")
        row.prop(self, "useLeftLeg")
        row.prop(self, "useRightLeg")
        self.layout.prop(self, "useSpine")


    def setMhxIk(self, value):
        ikLayers = []
        fkLayers = []
        if self.useLeftArm:
            self.rig["MhaArmIk_L"] = value
            ikLayers.append(L_LARMIK)
            fkLayers.append(L_LARMFK)
        if self.useRightArm:
            self.rig["MhaArmIk_R"] = value
            ikLayers.append(L_RARMIK)
            fkLayers.append(L_RARMFK)
        if self.useLeftLeg:
            self.rig["MhaLegIk_L"] = value
            ikLayers.append(L_LLEGIK)
            fkLayers.append(L_LLEGFK)
        if self.useRightLeg:
            self.rig["MhaLegIk_R"] = value
            ikLayers.append(L_RLEGIK)
            fkLayers.append(L_RLEGFK)
        if self.useSpine:
            self.rig["MhaSpineIk"] = value
        if value:
            onLayers = ikLayers
            offLayers = fkLayers
        else:
            onLayers = fkLayers
            offLayers = ikLayers
        if bpy.app.version < (4,0,0):
            for n in onLayers:
                self.state[n] = self.rig.data.layers[n] = True
            for n in offLayers:
                self.state[n] = self.rig.data.layers[n] = False
        else:
            for layer in onLayers:
                self.state[layer] = True
                self.rig.data.collections[layer].is_visible = True
            for layer in offLayers:
                self.state[layer] = False
                self.rig.data.collections[layer].is_visible = False

#------------------------------------------------------------------------
#   Transfer to links
#------------------------------------------------------------------------

class MHX_OT_TransferToLinks(Snapper, FrameRange):
    bl_idname = "mhx.transfer_to_links"
    bl_label = "Transfer To Links"
    bl_description = "Transfer animation to link bones"
    bl_options = {'UNDO'}

    useSpine : BoolProperty(
        name="Include Spine",
        description="Include spine in snapping",
        default=True)

    useFingers : BoolProperty(
        name="Include Fingers",
        description="Include fingers in snapping",
        default=False)

    useTongue : BoolProperty(
        name="Include Tongue",
        description="Include tongue in snapping",
        default=False)

    def draw(self, context):
        self.layout.prop(self, "useSpine")
        self.layout.prop(self, "useFingers")
        self.layout.prop(self, "useTongue")
        FrameRange.draw(self, context)

    def run(self, context):
        checkVisible(context.object)
        startProgress("Transfer to FK")
        time1 = time.perf_counter()
        self.transferToLinks(context)
        time2 = time.perf_counter()
        displayMessage("Transfer to FK completed\nin %1f seconds" % (time2-time1))


    def transferToLinks(self, context):
        props = []
        infos = []
        if self.useSpine:
            if self.rig.get("MhaSpineControl"):
                infos.append(self.getSpineInfo())
                props.append("MhaSpineControl")
            if self.rig.get("MhaNeckControl"):
                infos.append(self.getNeckHeadInfo())
                props.append("MhaNeckControl")
        if self.useFingers:
            if self.rig.get("MhaFingerControl_L"):
                infos.append(self.getFingerInfo("L"))
                props.append("MhaFingerControl_L")
            if self.rig.get("MhaFingerControl_R"):
                infos.append(self.getFingerInfo("R"))
                props.append("MhaFingerControl_R")
        if self.useTongue:
            if self.rig.get("MhaTongueControl"):
                infos.append(self.getTongueInfo(self.rig))
                props.append("MhaTongueControl")

        scn = context.scene
        self.auto = True
        frames = range(self.startFrame, self.endFrame+1)
        nFrames = len(frames)
        fkboness = []
        pbonesss = []
        matsss = {}
        for n,frame in enumerate(frames):
            self.setFrame(scn, frame)
            matsss[n] = []
            for info in infos:
                fkbones, pboness, matss = self.getBonesMatrices(info)
                if n == 0:
                    fkboness.append(fkbones)
                    pbonesss.append(pboness)
                matsss[n].append(matss)
            self.updatePose()
        for prop in props:
            self.rig[prop] = False
        for n,frame in enumerate(frames):
            self.setFrame(scn, frame)
            for info,fkbones in zip(infos, fkboness):
                self.clearFkIkBones(info, fkbones)
            for pboness,matss in zip(pbonesss, matsss[n]):
                self.setLinkBones(pboness, matss)

#------------------------------------------------------------------------
#   Transfer to FK
#------------------------------------------------------------------------

class MHX_OT_TransferToFk(Transferer, FootSnapper, FrameRange, Bender):
    bl_idname = "mhx.transfer_to_fk"
    bl_label = "Transfer IK => FK"
    bl_description = "Transfer IK animation to FK bones"
    bl_options = {'UNDO'}

    def draw(self, context):
        Transferer.draw(self, context)
        FrameRange.draw(self, context)

    def run(self, context):
        checkVisible(context.object)
        startProgress("Transfer to FK")
        time1 = time.perf_counter()
        self.transferMhxToFk(context)
        time2 = time.perf_counter()
        displayMessage("Transfer to FK completed\nin %1f seconds" % (time2-time1))


    def transferMhxToFk(self, context):
        lArmSnapIk,lArmCnsIk = self.getSnapBones("ArmIK", "L")
        lArmSnapFk,lArmCnsFk = self.getSnapBones("ArmFK", "L")
        rArmSnapIk,rArmCnsIk = self.getSnapBones("ArmIK", "R")
        rArmSnapFk,rArmCnsFk = self.getSnapBones("ArmFK", "R")
        lLegSnapIk,lLegCnsIk = self.getSnapBones("LegIK", "L")
        lLegSnapFk,lLegCnsFk = self.getSnapBones("LegFK", "L")
        rLegSnapIk,rLegCnsIk = self.getSnapBones("LegIK", "R")
        rLegSnapFk,rLegCnsFk = self.getSnapBones("LegFK", "R")

        scn = context.scene
        self.auto = True
        self.setMhxIk(1.0)
        lLegIkToAnkle = self.rig.get("MhaLegIkToAnkle_L")
        rLegIkToAnkle = self.rig.get("MhaLegIkToAnkle_R")
        if self.useSpine:
            back = self.rig.pose.bones.get("back")
            revback = self.rig.pose.bones.get("REV-ik_back")
        else:
            back = revback = None
        frames = range(self.startFrame, self.endFrame+1)
        nFrames = len(frames)
        for n,frame in enumerate(frames):
            showProgress(n, frame, nFrames)
            self.setFrame(scn, frame)
            if self.useLeftArm:
                self.snapFkArm(lArmSnapFk, lArmSnapIk)
            if self.useRightArm:
                self.snapFkArm(rArmSnapFk, rArmSnapIk)
            if self.useLeftLeg:
                self.snapFkLeg(lLegSnapFk, lLegSnapIk, lLegIkToAnkle)
            if self.useRightLeg:
                self.snapFkLeg(rLegSnapFk, rLegSnapIk, rLegIkToAnkle)
            if back and revback:
                self.snapReverse(back, revback)
        self.setMhxIk(0.0)

#------------------------------------------------------------------------
#   Transfer to IK
#------------------------------------------------------------------------

class MHX_OT_TransferToIk(Transferer, FootSnapper, FrameRange):
    bl_idname = "mhx.transfer_to_ik"
    bl_label = "Transfer FK => IK"
    bl_description = "Transfer FK animation to IK bones"
    bl_options = {'UNDO'}

    useApproximate : BoolProperty(
        name = "Approximate Snapping",
        description = "Approximate snapping which does not involve the IK twist bones",
        default = True)

    def draw(self, context):
        Transferer.draw(self, context)
        FootSnapper.draw(self, context)
        self.layout.prop(self, "useApproximate")
        FrameRange.draw(self, context)

    def run(self, context):
        checkVisible(context.object)
        startProgress("Transfer to IK")
        time1 = time.perf_counter()
        self.transferMhxToIk(context)
        time2 = time.perf_counter()
        displayMessage("Transfer to IK completed\nin %1f seconds" % (time2-time1))


    def transferMhxToIk(self, context):
        lArmSnapIk,lArmCnsIk = self.getSnapBones("ArmIK", "L")
        lArmSnapFk,lArmCnsFk = self.getSnapBones("ArmFK", "L")
        rArmSnapIk,rArmCnsIk = self.getSnapBones("ArmIK", "R")
        rArmSnapFk,rArmCnsFk = self.getSnapBones("ArmFK", "R")
        lLegSnapIk,lLegCnsIk = self.getSnapBones("LegIK", "L")
        lLegSnapFk,lLegCnsFk = self.getSnapBones("LegFK", "L")
        rLegSnapIk,rLegCnsIk = self.getSnapBones("LegIK", "R")
        rLegSnapFk,rLegCnsFk = self.getSnapBones("LegFK", "R")

        scn = context.scene
        self.auto = True
        self.setMhxIk(0.0)
        lLegIkToAnkle = self.rig.get("MhaLegIkToAnkle_L")
        rLegIkToAnkle = self.rig.get("MhaLegIkToAnkle_R")
        if self.useSpine:
            back = self.rig.pose.bones.get("ik_back")
            revback = self.rig.pose.bones.get("REV-back")
        else:
            back = revback = None
        if self.useApproximate:
            self.removeIkTwistFcurves()
        frames = range(self.startFrame, self.endFrame+1)
        nFrames = len(frames)
        for n,frame in enumerate(frames):
            showProgress(n, frame, nFrames)
            self.setFrame(scn, frame)
            if self.useLeftArm:
                self.snapIkArm(lArmSnapFk, lArmSnapIk)
            if self.useRightArm:
                self.snapIkArm(rArmSnapFk, rArmSnapIk)
            if self.useLeftLeg:
                self.snapIkLeg(lLegSnapFk, lLegSnapIk, lLegIkToAnkle)
            if self.useRightLeg:
                self.snapIkLeg(rLegSnapFk, rLegSnapIk, rLegIkToAnkle)
            if back and revback:
                self.snapReverse(back, revback)
        self.setMhxIk(1.0)


    def removeIkTwistFcurves(self):
        fcurves = getRnaFcurves(self.rig)
        for fcu in list(fcurves):
            words = fcu.data_path.split('"')
            if (words[0] == "pose.bones[" and
                ".ik.twist." in words[1]):
                fcurves.remove(fcu)
        for pb in self.rig.pose.bones:
            if ".ik.twist." in pb.name:
                pb.location = pb.rotation_euler = (0,0,0)

#------------------------------------------------------------------------
#   Clear animation
#------------------------------------------------------------------------

class MHX_OT_ClearAnimation(FrameRange):
    bl_idname = "mhx.clear_animation"
    bl_label = "Clear Animation"
    bl_description = "Clear Animation For FK or IK Bones"
    bl_options = {'UNDO'}

    clearLeftArmFK : BoolProperty(
        name = "Left FK",
        description = "Clear Left Arm FK animation",
        default = False)

    clearRightArmFK : BoolProperty(
        name = "Right FK",
        description = "Clear Right Arm FK animation",
        default = False)

    clearLeftArmIK : BoolProperty(
        name = "Left IK",
        description = "Clear Left Arm IK animation",
        default = False)

    clearRightArmIK : BoolProperty(
        name = "Right IK",
        description = "Clear Right Arm IK animation",
        default = False)

    clearLeftLegFK : BoolProperty(
        name = "Left FK",
        description = "Clear Left Leg FK animation",
        default = False)

    clearRightLegFK : BoolProperty(
        name = "Right FK",
        description = "Clear Right Leg FK animation",
        default = False)

    clearLeftLegIK : BoolProperty(
        name = "Left IK",
        description = "Clear Left Leg IK animation",
        default = False)

    clearRightLegIK : BoolProperty(
        name = "Right IK",
        description = "Clear Right Leg IK animation",
        default = False)

    clearSpineFK : BoolProperty(
        name = "Clear FK Spine",
        description = "Clear Spine FK animation",
        default = False)

    clearSpineIK : BoolProperty(
        name = "Clear IK Spine",
        description = "Clear Spine IK animation",
        default = False)

    useEntireAnimation : BoolProperty(
        name = "Entire Animation",
        description = "Remove entire animation rather than a frame range",
        default = True)

    def draw(self, context):
        row = self.layout.row()
        row.label(text = "Clear Arm FK")
        row.prop(self, "clearLeftArmFK")
        row.prop(self, "clearRightArmFK")
        row = self.layout.row()
        row.label(text = "Clear Arm IK")
        row.prop(self, "clearLeftArmIK")
        row.prop(self, "clearRightArmIK")
        row = self.layout.row()
        row.label(text = "Clear Leg FK")
        row.prop(self, "clearLeftLegFK")
        row.prop(self, "clearRightLegFK")
        row = self.layout.row()
        row.label(text = "Clear Leg IK")
        row.prop(self, "clearLeftLegIK")
        row.prop(self, "clearRightLegIK")
        self.layout.prop(self, "clearSpineFK")
        self.layout.prop(self, "clearSpineIK")
        self.layout.prop(self, "useEntireAnimation")
        if not self.useEntireAnimation:
            FrameRange.draw(self, context)

    def run(self, context):
        def getSnapBones(key, suffix):
            bnames = SnapBones[key]
            return ["%s.%s" % (bname, suffix) for bname in bnames]

        def getFcurves(fcurves):
            bnames = []
            if self.clearLeftArmFK:
                bnames += getSnapBones("ArmFK", "L")
            if self.clearRightArmFK:
                bnames += getSnapBones("ArmFK", "R")
            if self.clearLeftArmIK:
                bnames += getSnapBones("ArmIK", "L")
            if self.clearRightArmIK:
                bnames += getSnapBones("ArmIK", "R")
            if self.clearLeftLegFK:
                bnames += getSnapBones("LegFK", "L")
            if self.clearRightLegFK:
                bnames += getSnapBones("LegFK", "R")
            if self.clearLeftLegIK:
                bnames += getSnapBones("LegIK", "L")
            if self.clearRightLegIK:
                bnames += getSnapBones("LegIK", "R")
            if self.clearSpineFK:
                bnames += ["back"]
            if self.clearSpineIK:
                bnames += ["ik_back"]
            fcus = []
            for fcu in fcurves:
                words = fcu.data_path.split('"')
                if (words[0] == "pose.bones[" and
                    words[1] in bnames):
                    fcus.append(fcu)
            return fcus

        from .fkik import SnapBones
        startProgress("Clear animation")
        fcus = None
        rig = context.object
        checkVisible(rig)
        fcurves = getRnaFcurves(rig)
        fcus = getFcurves(fcurves)
        if self.useEntireAnimation:
            for fcu in fcus:
                fcurves.remove(fcu)
        else:
            for fcu in fcus:
                fcu.keyframe_points.sort()
                kps = [(kp.co[0],kp) for kp in fcu.keyframe_points if kp.co[0] >= self.startFrame and kp.co[0] <= self.endFrame]
                kps.reverse()
                for x,kp in kps:
                    fcu.keyframe_points.remove(kp, fast=True)
        if fcus:
            msg = "Animation cleared"
        else:
            msg = "No F-curves found"
        displayMessage(msg)

#-------------------------------------------------------------
#   Feet operations
#-------------------------------------------------------------

class Footer(Basic):

    useLeft : BoolProperty(
        name="Left",
        description="Keep left foot above floor",
        default=True)

    useRight : BoolProperty(
        name="Right",
        description="Keep right foot above floor",
        default=True)

    useHips : BoolProperty(
        name="Hips",
        description="Also adjust character COM when keeping feet above floor",
        default=True)

    useMarkers : BoolProperty(
        name = "Markers",
        description = "Use markers to determine foot location",
        default = True)

    def draw(self, context):
        self.layout.prop(self, "useLeft")
        self.layout.prop(self, "useRight")
        self.layout.prop(self, "useHips")
        self.layout.prop(self, "useMarkers")


    def getMarkers(self, suffix):
        try:
            mBall = self.getBone("ball.marker.%s" % suffix)
            mToe = self.getBone("toe.marker.%s" % suffix)
            mHeel = self.getBone("heel.marker.%s" % suffix)
            return mBall,mToe,mHeel
        except KeyError:
            return None


    def getPlane(self, context):
        self.plane = None
        for ob in context.view_layer.objects:
            if ob.select_get() and ob.type == 'MESH' and ob.visible_get():
                self.plane = ob
                return


    def getPlaneInfo(self):
        if self.plane is None:
            ez = Vector((0,0,1))
            origin = Vector((0,0,0))
            rot = Matrix()
        else:
            mat = self.plane.matrix_world.to_3x3().normalized()
            ez = mat.col[2]
            origin = self.plane.location
            rot = mat.to_4x4()
        return ez,origin,rot


    def addOffset(self, pb, offset, ez):
        gmat = pb.matrix.copy()
        x,y,z = offset*ez
        gmat.col[3] += Vector((x,y,z,0))
        pmat = self.getPoseMatrix(gmat, pb)
        self.insertLocation(pb, pmat)

#-------------------------------------------------------------
#   Offset toes
#-------------------------------------------------------------

class MHX_OT_ConstrainFeet(MhxOperator):
    bl_idname = "mhx.constrain_feet"
    bl_label = "Constrain Feet"
    bl_description = "Add aggressive constraints to the feet"
    bl_options = {'UNDO'}

    def run(self, context):
        locks = {
            "toe.fk" : [1, 2],
            "foot.fk" : [1],
            "foot.rev" : [1, 2],
        }
        limits = {
            "toe.fk" : { "max_x" : 0, "min_y" : 0, "max_y" : 0, "min_z" : 0, "max_z" : 0 }
        }

        rig = context.object
        checkVisible(rig)
        for suffix in ["L", "R"]:
            for bname,lock in locks.items():
                pb = rig.pose.bones["%s.%s" % (bname, suffix)]
                for idx in lock:
                    pb.lock_rotation[idx] = True
            for bname,limit in limits.items():
                pb = rig.pose.bones["%s.%s" % (bname, suffix)]
                for cns in pb.constraints:
                    if cns.type == 'LIMIT_ROTATION':
                        for attr,val in limit.items():
                            setattr(cns, attr, val)

#-------------------------------------------------------------
#   Utilities
#-------------------------------------------------------------


def getOffset(point, ez, origin):
    vec = Vector(point[:3]) - origin
    offset = -ez.dot(vec)
    return offset


def getHeadOffset(pb, ez, origin):
    head = pb.matrix.col[3]
    return getOffset(head, ez, origin)


def getTailOffset(pb, ez, origin):
    head = pb.matrix.col[3]
    y = pb.matrix.col[1]
    tail = head + y*pb.length
    return getOffset(tail, ez, origin)

#-------------------------------------------------------------
#   Floor
#-------------------------------------------------------------

class MHX_OT_ShiftBoneFCurves(FrameRange, Basic):
    bl_idname = "mhx.shift_animation"
    bl_label = "Shift Animation"
    bl_description = "Shift the animation globally for selected boens"
    bl_options = {'UNDO'}

    def run(self, context):
        checkVisible(self.rig)
        fcurves = getRnaFcurves(self.rig)
        startProgress("Shift animation")
        self.auto = True
        scn = context.scene
        frames = [scn.frame_current] + self.getActiveFrames()
        nFrames = len(frames)
        basemats, useLoc = self.getBaseMatrices(fcurves, frames, False)

        deltaMat = {}
        orders = {}
        locks = {}
        for bname,bmats in basemats.items():
            pb = self.rig.pose.bones[bname]
            bmat = bmats[0]
            deltaMat[pb.name] = pb.matrix_basis @ bmat.inverted()

        for n,frame in enumerate(frames):
            self.setFrame(scn, frame)
            showProgress(n, frame, nFrames)
            for bname,bmats in basemats.items():
                pb = self.rig.pose.bones[bname]
                mat = deltaMat[pb.name] @ bmats[n]
                if useLoc[bname]:
                    self.insertLocation(pb, mat)
                self.insertRotation(pb, mat)

        displayMessage("Animation shifted")


    def getBaseMatrices(self, fcurves, frames, useAll):
        fstruct = { "location" : {}, "rotation_euler" : {}, "rotation_quaternion" : {} }
        nidxs = { "location" : 3, "rotation_euler" : 3, "rotation_quaternion" : 4 }
        for fcu in fcurves:
            words = fcu.data_path.split('"')
            if words[0] != "pose.bones[":
                continue
            bname = words[1]
            channel = words[2].rsplit(".")[-1]
            if (channel in fstruct.keys() and
                bname in self.rig.pose.bones.keys()):
                pb = self.rig.pose.bones[bname]
            else:
                continue
            if P2B(pb).select:
                if bname not in fstruct[channel].keys():
                    fstruct[channel][bname] = nidxs[channel]*[None]
                fstruct[channel][bname][fcu.array_index] = fcu

        basemats = {}
        useLoc = {}
        for bname,fcus in fstruct["rotation_euler"].items():
            useLoc[bname] = False
            order = self.rig.pose.bones[bname].rotation_mode
            fcu0,fcu1,fcu2 = fcus
            rmats = basemats[bname] = []
            for frame in frames:
                euler = Euler((self.getValue(fcu0, frame, 0),self.getValue(fcu1, frame, 0), self.getValue(fcu2, frame, 0)), order)
                rmats.append(euler.to_matrix().to_4x4())

        for bname,fcus in fstruct["rotation_quaternion"].items():
            useLoc[bname] = False
            fcu0,fcu1,fcu2,fcu3 = fcus
            rmats = basemats[bname] = []
            for frame in frames:
                quat = Quaternion((self.getValue(fcu0, frame, 1), self.getValue(fcu1, frame, 0), self.getValue(fcu2, frame, 0), self.getValue(fcu3, frame, 0)))
                rmats.append(quat.to_matrix().to_4x4())

        for bname,fcus in fstruct["location"].items():
            useLoc[bname] = True
            fcu0,fcu1,fcu2 = fcus
            tmats = []
            for frame in frames:
                loc = (self.getValue(fcu0, frame, 0),self.getValue(fcu1, frame, 0), self.getValue(fcu2, frame, 0))
                tmats.append(Matrix.Translation(loc))
            if bname in basemats.keys():
                rmats = basemats[bname]
                mats = []
                for tmat,rmat in zip(tmats, rmats):
                    mats.append( tmat @ rmat )
                basemats[bname] = mats
            else:
                basemats[bname] = tmats

        return basemats, useLoc


    def getValue(self, fcu, frame, default):
        return (fcu.evaluate(frame) if fcu else default)

#-------------------------------------------------------------
#   Floor FK foot
#-------------------------------------------------------------

class MHX_OT_FloorFkFoot(Footer, FrameRange):
    bl_idname = "mhx.floor_fk_feet"
    bl_label = "Keep FK Feet Above Floor"
    bl_description = "Keep FK Feet Above Zero Plane"
    bl_options = {'UNDO'}

    def draw(self, context):
        Footer.draw(self, context)
        FrameRange.draw(self, context)

    def run(self, context):
        startProgress("Keep feet above floor")
        self.auto = True
        scn = context.scene
        self.rig = context.object
        checkVisible(self.rig)
        self.getPlane(context)
        frames = range(self.startFrame, self.endFrame+1)
        self.floorFkFoot(scn, frames)
        displayMessage("FK Feet kept above floor")


    def floorFkFoot(self, scn, frames):
        hip = self.getBone("hip")
        lFoot,lToe = self.getFkFeetBones("L")
        rFoot,rToe = self.getFkFeetBones("R")
        if self.useMarkers:
            lMarkers = self.getMarkers("L")
            rMarkers = self.getMarkers("R")
        else:
            lMarkers = rMarkers = None
        ez,origin,rot = self.getPlaneInfo()

        nFrames = len(frames)
        for n,frame in enumerate(frames):
            self.setFrame(scn, frame)
            offset = 0
            if self.useLeft:
                offset = self.getFkOffset(ez, origin, lFoot, lToe, lMarkers)
            if self.useRight:
                rOffset = self.getFkOffset(ez, origin, rFoot, rToe, rMarkers)
                if rOffset > offset:
                    offset = rOffset
            showProgress(n, frame, nFrames)
            if offset > 0:
                self.addOffset(hip, offset, ez)


    def getFkFeetBones(self, suffix):
        foot = self.getBone("foot.fk.%s" % suffix)
        toe = self.getBone("toe.fk.%s" % suffix)
        return foot,toe


    def getFkOffset(self, ez, origin, foot, toe, markers):
        if markers:
            mToe,mBall,mHeel = markers
            toeOffset = getHeadOffset(mToe, ez, origin)
            ballOffset = getHeadOffset(mBall, ez, origin)
            heelOffset = getHeadOffset(mHeel, ez, origin)
            return max([toeOffset, ballOffset, heelOffset])
        elif toe:
            toeOffset = getTailOffset(toe, ez, origin)
            ballOffset = getHeadOffset(toe, ez, origin)
            ball = toe.matrix.col[3]
            y = toe.matrix.col[1]
            heel = ball - y*foot.length
            heelOffset = getOffset(heel, ez, origin)
            return max([toeOffset, ballOffset, heelOffset])
        else:
            return 0

#-------------------------------------------------------------
#   Floor IK foot
#-------------------------------------------------------------

class MHX_OT_FloorIkFoot(Footer, FrameRange):
    bl_idname = "mhx.floor_ik_feet"
    bl_label = "Keep IK Feet Above Floor"
    bl_description = "Keep IK Feet Above Zero Plane"
    bl_options = {'UNDO'}

    useGlue : BoolProperty(
        name = "Glue Feet",
        description = "Remove movement of IK effector on shifted frames",
        default = True)

    easeInOut : IntProperty(
        name = "Ease In/Out",
        description = "",
        min = 0, max = 5,
        default = 3)

    def draw(self, context):
        Footer.draw(self, context)
        self.layout.prop(self, "useGlue")
        self.layout.prop(self, "easeInOut")
        FrameRange.draw(self, context)


    def run(self, context):
        startProgress("Keep feet above floor")
        self.auto = True
        scn = context.scene
        self.rig = context.object
        checkVisible(self.rig)
        self.getPlane(context)
        frames = range(self.startFrame, self.endFrame+1)
        self.floorIkFoot(scn, frames)
        displayMessage("FK Feet kept above floor")


    def floorIkFoot(self, scn, frames):
        hip = self.rig.pose.bones["hip"]
        lleg = self.rig.pose.bones["foot.ik.L"]
        rleg = self.rig.pose.bones["foot.ik.R"]
        ez,origin,rot = self.getPlaneInfo()
        if self.useMarkers:
            lMarkers = self.getMarkers("L")
            rMarkers = self.getMarkers("R")
        else:
            lMarkers = rMarkers = None

        self.fillKeyFrames(lleg, frames, 3, 'location')
        self.fillKeyFrames(rleg, frames, 3, 'location')
        if self.useHips:
            self.fillKeyFrames(hip, frames, 3, 'location')

        nFrames = len(frames)
        left = []
        right = []
        for n,frame in enumerate(frames):
            self.setFrame(scn, frame)
            showProgress(n, frame, nFrames)
            if self.useLeft:
                lOffset = self.getIkOffset(ez, origin, lleg, lMarkers)
                if lOffset > 0:
                    self.addOffset(lleg, lOffset, ez)
                    left.append(frame)
            else:
                lOffset = 0
            if self.useRight:
                rOffset = self.getIkOffset(ez, origin, rleg, rMarkers)
                if rOffset > 0:
                    self.addOffset(rleg, rOffset, ez)
                    right.append(frame)
            else:
                rOffset = 0
            hOffset = min(lOffset,rOffset)
            if hOffset > 0 and self.useHips:
                self.addOffset(hip, hOffset, ez)

        if self.useGlue and left:
            self.glueFoot(lleg, left)
        if self.useGlue and right:
            self.glueFoot(rleg, right)


    def fillKeyFrames(self, pb, frames, nIndices, channel):
        for idx in range(nIndices):
            fcu = self.findBoneFCurve(pb, channel, idx)
            if fcu is None:
                return
            for frame in frames:
                y = fcu.evaluate(frame)
                fcu.keyframe_points.insert(frame, y, options={'FAST'})


    def getIkOffset(self, ez, origin, leg, markers):
        if markers:
            mToe,mBall,mHeel = markers
            toeOffset = getHeadOffset(mToe, ez, origin)
            ballOffset = getHeadOffset(mBall, ez, origin)
            heelOffset = getHeadOffset(mHeel, ez, origin)
            return max([toeOffset, ballOffset, heelOffset])
        elif True:
            headOffset = getHeadOffset(leg, ez, origin)
            tailOffset = getTailOffset(leg, ez, origin)
            return max([headOffset, tailOffset])
        else:
            foot = self.rig.pose.bones["foot.rev.%s" % suffix]
            toe = self.rig.pose.bones["toe.rev.%s" % suffix]
            toeOffset = getHeadOffset(toe, ez, origin)
            ballOffset = getTailOffset(toe, ez, origin)
            ball = foot.matrix.col[3]
            heel = ball + y*foot.length
            heelOffset = getOffset(heel, ez, origin)
            return max([toeOffset, ballOffset, heelOffset])


    def glueFoot(self, leg, frames):
        if len(frames) == 0:
            return
        fcus = self.findBoneFCurves(leg, "rotation")
        fcus += self.findBoneFCurves(leg, "location")
        groups = self.getGroups(frames)
        for frame0,frame1 in groups:
            for fcu in fcus:
                self.average(fcu, frame0, frame1)


    def getGroups(self, frames):
        groups = []
        frame0 = frame1 = frames[0]
        n1 = 1
        while frames:
            frame0 = frame1 = frames[0]
            for n,frame in enumerate(frames[1:]):
                n1 = n+1
                if frame == frame1+1:
                    frame1 = frame
                else:
                    break
            if frame1 != frame0:
                groups.append((frame0, frame1))
            frames = frames[n1:]
        return groups


    def average(self, fcu, frame0, frame1):
        kps = [kp for kp in fcu.keyframe_points
               if kp.co[0] >= frame0 and kp.co[0] <= frame1]
        yvals = [kp.co[1] for kp in kps]
        if len(yvals) == 0:
            return
        n = min(self.easeInOut, len(kps)-2)
        if len(kps) < 2*n:
            y0 = kps[0].co[1]
            y1 = kps[-1].co[1]
            for j in range(n):
                w = j/n
                kp = kps[j]
                kp.co[1] = w*y1 + (1-w)*y0
        else:
            y = sum(yvals)/len(yvals)
            for j in range(n):
                w = j/n
                kp = kps[j]
                kp.co[1] = w*y + (1-w)*kp.co[1]
                kp = kps[-1-j]
                kp.co[1] = w*y + (1-w)*kp.co[1]
            for kp in kps[n:-1-n]:
                kp.co[1] = y

#----------------------------------------------------------
#   Initialize
#----------------------------------------------------------

classes = [
    MHX_OT_RemoveUnusedFcurves,
    MHX_OT_ConstrainFeet,
    MHX_OT_EnforceLimits,
    MHX_OT_ClearIkTwistBones,
    MHX_OT_EnforceAllLimits,
    MHX_OT_LimbsBendPositive,
    MHX_OT_ShiftBoneFCurves,
    MHX_OT_TransferToLinks,
    MHX_OT_TransferToFk,
    MHX_OT_TransferToIk,
    MHX_OT_ClearAnimation,
    MHX_OT_FloorFkFoot,
    MHX_OT_FloorIkFoot,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)

