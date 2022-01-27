# Copyright (c) 2016-2021, Thomas Larsson
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# The views and conclusions contained in the software and documentation are those
# of the authors and should not be interpreted as representing official policies,
# either expressed or implied, of the FreeBSD Project.

# ---------------------------------------------------------------------------
#
# The purpose of this file is to make facial drivers work even if the
# import-daz add-on is not available. A typical situation might be if you send
# the blend file to an external rendering service.
#
# 1. Disable the import-daz add-on and press Save User Settings.
# 2. Open this file (runtime_stripped_28x.py) in a text editor window.
# 3. Enable the Register checkbox.
# 4. Run the script (Run Script)
# 5. Save the blend file.
# 6. Reload the blend file.
#
# Alternative method:
#
# 1. Put this file in a place where Blender 2.79 looks for add-ons.
# 2. Disable the import-daz add-on and press Save User Settings.
# 3. Enable this add-on and Save User Settings.
# 4. Load the blend file.
#
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
#
# This file is for Blender 2.80 and higher.
#
# ---------------------------------------------------------------------------

bl_info = {
    "name": "DAZ Importer Stripped Runtime System",
    "author": "Thomas Larsson",
    "version": (1,1,0),
    "blender": (2,80,0),
    "location": "",
    "description": "Stripped RTS that defines function used by drivers.",
    "warning": "",
    "wiki_url": "http://diffeomorphic.blogspot.se/p/daz-importer-version-14.html",
    "tracker_url": "https://bitbucket.org/Diffeomorphic/import-daz/issues?status=new&status=open",
    "category": "Runtime"}

import bpy
from bpy.app.handlers import persistent
from bpy.props import *


class DazMorphGroup(bpy.types.PropertyGroup):
    prop : StringProperty()
    factor : FloatProperty()
    factor2 : FloatProperty()
    index : IntProperty()
    default : FloatProperty()
    simple : BoolProperty(default=True)

    def __repr__(self):
        return "<MorphGroup %d %s %f %f>" % (self.index, self.prop, self.factor, self.default)

    def eval(self, rig):
        if self.simple:
            return self.factor*(rig[self.name]-self.default)
        else:
            value = rig[self.name]-self.default
            return (self.factor*(value > 0) + self.factor2*(value < 0))*value

    def display(self):
        return ("MG %d %-25s %6s %10.6f %10.6f %10.2f" % (self.index, self.name, self.simple, self.factor, self.factor2, self.default))

    def init(self, prop, idx, default, factor, factor2):
        self.name = prop
        self.index = idx
        self.factor = factor
        self.default = default
        if factor2 is None:
            self.factor2 = 0
            self.simple = True
        else:
            self.factor2 = factor2
            self.simple = False

    def __lt__(self,other):
        if self.name == other.name:
            return (self.index < other.index)
        else:
            return (self.name < other.name)

#-------------------------------------------------------------
#   Old style evalMorphs, for backward compatibility
#-------------------------------------------------------------

def evalMorphs(pb, idx, key):
    rig = pb.id_data
    props = pb.DazLocProps if key == "Loc" else pb.DazRotProps if key == "Rot" else pb.DazScaleProps
    return sum([pg.factor*(rig[pg.prop]-pg.default) for pg in props if pg.index == idx])

#-------------------------------------------------------------
#   New style evalMorphs
#-------------------------------------------------------------

def evalMorphs2(pb, idx, key):
    rig = pb.id_data
    pgs = pb.DazLocProps if key == "Loc" else pb.DazRotProps if key == "Rot" else pb.DazScaleProps
    return sum([pg.eval(rig) for pg in pgs if pg.index == idx])

#-------------------------------------------------------------
#   Separate Loc, Rot, Sca
#-------------------------------------------------------------

def evalMorphsLoc(pb, idx):
    rig = pb.id_data
    return sum([pg.eval(rig) for pg in pb.DazLocProps if pg.index == idx])

def evalMorphsRot(pb, idx):
    rig = pb.id_data
    return sum([pg.eval(rig) for pg in pb.DazRotProps if pg.index == idx])

def evalMorphsSca(pb, idx):
    rig = pb.id_data
    return sum([pg.eval(rig) for pg in pb.DazScaleProps if pg.index == idx])

#-------------------------------------------------------------
#   Separate Loc, Rot, Sca and separate components
#-------------------------------------------------------------

def evalMorphsLoc0(pb):
    rig = pb.id_data
    return sum([pg.eval(rig) for pg in pb.DazLocProps0])

def evalMorphsLoc1(pb):
    rig = pb.id_data
    return sum([pg.eval(rig) for pg in pb.DazLocProps1])

def evalMorphsLoc2(pb):
    rig = pb.id_data
    return sum([pg.eval(rig) for pg in pb.DazLocProps2])

def evalMorphsRot0(pb):
    rig = pb.id_data
    return sum([pg.eval(rig) for pg in pb.DazRotProps0])

def evalMorphsRot1(pb):
    rig = pb.id_data
    return sum([pg.eval(rig) for pg in pb.DazRotProps1])

def evalMorphsRot2(pb):
    rig = pb.id_data
    return sum([pg.eval(rig) for pg in pb.DazRotProps2])

def evalMorphsRot3(pb):
    rig = pb.id_data
    return sum([pg.eval(rig) for pg in pb.DazRotProps3])

def evalMorphsSca0(pb):
    rig = pb.id_data
    return sum([pg.eval(rig) for pg in pb.DazScaProps0])

def evalMorphsSca1(pb):
    rig = pb.id_data
    return sum([pg.eval(rig) for pg in pb.DazScaProps1])

def evalMorphsSca2(pb):
    rig = pb.id_data
    return sum([pg.eval(rig) for pg in pb.DazScaProps2])

#-------------------------------------------------------------
#   Initialize
#-------------------------------------------------------------

@persistent
def updateHandler(scn):
    global evalMorphs, evalMorphs2
    global evalMorphsLoc, evalMorphsLoc0, evalMorphsLoc1, evalMorphsLoc2
    global evalMorphsRot, evalMorphsRot0, evalMorphsRot1, evalMorphsRot2, evalMorphsRot3
    global evalMorphsSca, evalMorphsSca0, evalMorphsSca1, evalMorphsSca2
    bpy.app.driver_namespace["evalMorphs"] = evalMorphs
    bpy.app.driver_namespace["evalMorphs2"] = evalMorphs2
    bpy.app.driver_namespace["evalMorphsLoc"] = evalMorphsLoc
    bpy.app.driver_namespace["evalMorphsLoc0"] = evalMorphsLoc0
    bpy.app.driver_namespace["evalMorphsLoc1"] = evalMorphsLoc1
    bpy.app.driver_namespace["evalMorphsLoc2"] = evalMorphsLoc2
    bpy.app.driver_namespace["evalMorphsRot"] = evalMorphsRot
    bpy.app.driver_namespace["evalMorphsRot0"] = evalMorphsRot0
    bpy.app.driver_namespace["evalMorphsRot1"] = evalMorphsRot1
    bpy.app.driver_namespace["evalMorphsRot2"] = evalMorphsRot2
    bpy.app.driver_namespace["evalMorphsRot3"] = evalMorphsRot3
    bpy.app.driver_namespace["evalMorphsSca"] = evalMorphsSca
    bpy.app.driver_namespace["evalMorphsSca0"] = evalMorphsSca0
    bpy.app.driver_namespace["evalMorphsSca1"] = evalMorphsSca1
    bpy.app.driver_namespace["evalMorphsSca2"] = evalMorphsSca2


def register():
    bpy.utils.register_class(DazMorphGroup)

    bpy.types.PoseBone.DazLocProps = CollectionProperty(type = DazMorphGroup)
    bpy.types.PoseBone.DazLocProps0 = CollectionProperty(type = DazMorphGroup)
    bpy.types.PoseBone.DazLocProps1 = CollectionProperty(type = DazMorphGroup)
    bpy.types.PoseBone.DazLocProps2 = CollectionProperty(type = DazMorphGroup)
    bpy.types.PoseBone.DazRotProps = CollectionProperty(type = DazMorphGroup)
    bpy.types.PoseBone.DazRotProps0 = CollectionProperty(type = DazMorphGroup)
    bpy.types.PoseBone.DazRotProps1 = CollectionProperty(type = DazMorphGroup)
    bpy.types.PoseBone.DazRotProps2 = CollectionProperty(type = DazMorphGroup)
    bpy.types.PoseBone.DazRotProps3 = CollectionProperty(type = DazMorphGroup)
    bpy.types.PoseBone.DazScaleProps = CollectionProperty(type = DazMorphGroup)
    bpy.types.PoseBone.DazScaProps0 = CollectionProperty(type = DazMorphGroup)
    bpy.types.PoseBone.DazScaProps1 = CollectionProperty(type = DazMorphGroup)
    bpy.types.PoseBone.DazScaProps2 = CollectionProperty(type = DazMorphGroup)

    updateHandler(None)
    bpy.app.handlers.load_post.append(updateHandler)

    # Update drivers
    for ob in bpy.context.view_layer.objects:
        if ob.animation_data:
            for fcu in ob.animation_data.drivers:
                fcu.driver.expression = str(fcu.driver.expression)


def unregister():
    bpy.utils.unregister_class(DazMorphGroup)


if __name__ == "__main__":
    register()

