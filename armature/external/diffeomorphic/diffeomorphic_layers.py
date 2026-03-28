# SPDX-FileCopyrightText: 2016-2026, Thomas Larsson
#
# SPDX-License-Identifier: GPL-2.0-or-later

import bpy

if bpy.app.version < (4,0,0):
    L_MAIN =    0
    L_SPINE =   1

    L_LARMIK =  2
    L_LARMFK =  3
    L_LLEGIK =  4
    L_LLEGFK =  5
    L_LHAND =   6
    L_LFINGER = 7
    L_LARM2IK = 12
    L_LLEG2IK = 12
    L_LTOE =    13

    L_RARMIK =  18
    L_RARMFK =  19
    L_RLEGIK =  20
    L_RLEGFK =  21
    L_RHAND =   22
    L_RFINGER = 23
    L_RARM2IK = 28
    L_RLEG2IK = 28
    L_RTOE =    29

    L_FACE =    8
    L_TWEAK =   9
    L_HEAD =    10
    L_SPINE2 =  11
    L_CUSTOM =  16
    L_CUSTOM2 = 17

    L_HELP =    14
    L_HELP2 =   15
    L_HIDDEN =  30
    L_DEF =     31
else:
    L_MAIN =    "Root"
    L_SPINE =   "Spine"

    L_LARMIK =  "IK Arm Left"
    L_LARMFK =  "FK Arm Left"
    L_LLEGIK =  "IK Leg Left"
    L_LLEGFK =  "FK Leg Left"
    L_LHAND =   "Hand Left"
    L_LFINGER = "Fingers Left"
    L_LARM2IK = "IK Arm 2 Left"
    L_LLEG2IK = "IK Leg 2 Left"
    L_LTOE =    "Toes Left"

    L_RARMIK =  "IK Arm Right"
    L_RARMFK =  "FK Arm Right"
    L_RLEGIK =  "IK Leg Right"
    L_RLEGFK =  "FK Leg Right"
    L_RHAND =   "Hand Right"
    L_RFINGER = "Fingers Right"
    L_RARM2IK = "IK Arm 2 Right"
    L_RLEG2IK = "IK Leg 2 Right"
    L_RTOE =    "Toes Right"

    L_FACE =    "Face"
    L_TWEAK =   "Tweak"
    L_HEAD =    "Head"
    L_SPINE2 =  "Spine 2"
    L_CUSTOM =  "Custom"
    L_CUSTOM2 = "Custom 2"

    L_HELP =    "Help"
    L_HELP2 =   "Help 2"
    L_HIDDEN =  "Hidden"
    L_DEF =     "Deform"


MhxLayers = {
    0 :     "Root",
    1 :     "Spine",

    2 :     "IK Arm Left",
    3 :     "FK Arm Left",
    4 :     "IK Leg Left",
    5 :     "FK Leg Left",
    6 :     "Hand Left",
    7 :     "Fingers Left",
    12 :    "Extra Left",
    13 :    "Toes Left",

    18 :    "IK Arm Right",
    19 :    "FK Arm Right",
    20 :    "IK Leg Right",
    21 :    "FK Leg Right",
    22 :    "Hand Right",
    23 :    "Fingers Right",
    28 :    "Extra Right",
    29 :    "Toes Right",

    8 :     "Face",
    9 :     "Tweak",
    10 :    "Head",
    11 :    "Spine 2",
    16 :    "Custom",
    17 :    "Custom 2",

    14 :    "Help",
    15 :    "Help 2",
    30 :    "Hidden",
    31 :    "Deform",
}


F_TONGUE = 1
F_FINGER = 2
F_IDPROPS = 4
F_SPINE = 8
F_SHAFT = 16
F_NECK = 32

