# Mustard Simplify
# https://github.com/Mustard2/MustardSimplify

bl_info = {
    "name": "Mustard Simplify",
    "description": "A set of tools to simplify scenes for better viewport performance",
    "author": "Mustard",
    "version": (0, 3, 0),
    "blender": (4, 0, 0),
    "warning": "",
    "category": "3D View",
}

import bpy
import addon_utils
import sys
import os
import re
import time
import math
from bpy.props import *
from bpy.app.handlers import persistent
from mathutils import Vector, Color
import webbrowser

# ------------------------------------------------------------------------
#    Main Settings
# ------------------------------------------------------------------------

# Class with all the settings variables
class MustardSimplify_Settings(bpy.types.PropertyGroup):
    
    # Main Settings definitions
    # UI definitions
    advanced: bpy.props.BoolProperty(name="Advanced Options",
                                        description="Unlock advanced options",
                                        default=False)
    debug: bpy.props.BoolProperty(name="Debug mode",
                                        description="Unlock debug mode.\nThis will generate more messaged in the console.\nEnable it only if you encounter problems, as it might degrade general Blender performance",
                                        default=False)
    # Modifiers
    blender_simplify: bpy.props.BoolProperty(name="Blender Simplify",
                                        description="Enable Blender Simplify",
                                        default=True)
    # Modifiers
    modifiers: bpy.props.BoolProperty(name="Modifiers",
                                        description="Disable modifiers",
                                        default=True)
    # Shape Keys
    shape_keys: bpy.props.BoolProperty(name="Shape Keys",
                                        description="Mute un-used shape keys (value different from 0)",
                                        default=True)
    shape_keys_disable_not_null: bpy.props.BoolProperty(name="Disable only when Null",
                                        description="Disable only Shape Keys with value equal to 0.\nThis applies only to non-driven Shape Keys (i.e., without drivers or animation keyframes)",
                                        default=True)
    shape_keys_disable_with_drivers: bpy.props.BoolProperty(name="Disable if with Drivers",
                                        description="Disable Shape Keys driven by drivers",
                                        default=True)
    shape_keys_disable_with_drivers_not_null: bpy.props.BoolProperty(name="Disable only when Null",
                                        description="Disable Shape Keys driven by drivers only when null",
                                        default=False)
    shape_keys_disable_with_keyframes: bpy.props.BoolProperty(name="Disable if with Animation Key-Frames",
                                        description="Disable Shape Keys driven by animation keyframes regardless of other settings.\nThis is not affected by Disable when Null setting: if the setting is on, these Shape Keys are muted regardless of their value",
                                        default=False)
    # Physics
    physics: bpy.props.BoolProperty(name="Physics",
                                        description="Disable Physics",
                                        default=True)
    # Drivers
    drivers: bpy.props.BoolProperty(name="Drivers",
                                        description="Disable Drivers",
                                        default=True)
    # Normals Auto Smooth
    normals_auto_smooth: bpy.props.BoolProperty(name="Normals Auto Smooth",
                                        description="Disable Normals Auto Smooth",
                                        default=True)
    
    # UI Settings
    collapse_options: bpy.props.BoolProperty(name="Collapse",
                                        default=True)
    collapse_exceptions: bpy.props.BoolProperty(name="Collapse",
                                        default=True)
    collapse_others: bpy.props.BoolProperty(name="Collapse",
                                        default=True)
    
    # Exceptions
    exception_type: bpy.props.EnumProperty(name = "Exception",
                        description = "Exception Type",
                        default = "OBJECT",
                        items = (("OBJECT", "Objects", "Objects with exceptions", "OBJECT_DATAMODE", 0),
                        ("COLLISION", "Collection", "Collection with exceptions", "OUTLINER_COLLECTION", 1)))
    
    def poll_exception(self, object):
        exceptions = bpy.context.scene.MustardSimplify_Exceptions.exceptions
        exceptions = [x.exception for x in exceptions]
        return not object in exceptions
    
    exception_select: bpy.props.PointerProperty(type=bpy.types.Object,
                                        poll=poll_exception,
                                        name="Object",
                                        description="Object to add to exceptions")
    
    exception_collection: bpy.props.PointerProperty(type=bpy.types.Collection,
                                        name="Collection",
                                        description="Collection whose Objects will be considered full exceptions")
    
    # Internal Settings
    simplify_fastnormals_status: bpy.props.BoolProperty(default=False)
    simplify_status: bpy.props.BoolProperty(default=False)
    
    # Modifiers to not simplify by default
    modifiers_ignore = ["ARMATURE", "HOOK"]
            
bpy.utils.register_class(MustardSimplify_Settings)
bpy.types.Scene.MustardSimplify_Settings = bpy.props.PointerProperty(type=MustardSimplify_Settings)

# ------------------------------------------------------------------------
#    Status Properties
# ------------------------------------------------------------------------

# Modifier status
class MustardSimplify_ModifierStatus(bpy.types.PropertyGroup):
    status: bpy.props.BoolProperty(default=True)
    name: bpy.props.StringProperty(default="")
bpy.utils.register_class(MustardSimplify_ModifierStatus)

# Shape Keys
class MustardSimplify_ShapeKeysStatus(bpy.types.PropertyGroup):
    status: bpy.props.BoolProperty(default=True)
    name: bpy.props.StringProperty(default="")
bpy.utils.register_class(MustardSimplify_ShapeKeysStatus)

# Class with all the settings variables
class MustardSimplify_ObjectStatus(bpy.types.PropertyGroup):
    
    # Normals Auto Smooth
    normals_auto_smooth: bpy.props.BoolProperty(default=True)
    # Modifiers status
    modifiers: bpy.props.CollectionProperty(type=MustardSimplify_ModifierStatus)
    # Shape Keys status
    shape_keys: bpy.props.CollectionProperty(type=MustardSimplify_ShapeKeysStatus)
            
bpy.utils.register_class(MustardSimplify_ObjectStatus)
bpy.types.Object.MustardSimplify_Status = bpy.props.PointerProperty(type=MustardSimplify_ObjectStatus)

# Class to store the scene status
class MustardSimplify_SceneStatus(bpy.types.PropertyGroup):
    rigidbody_world: bpy.props.BoolProperty(default=False)
            
bpy.utils.register_class(MustardSimplify_SceneStatus)
bpy.types.Scene.MustardSimplify_Status = bpy.props.PointerProperty(type=MustardSimplify_SceneStatus)

# Classes to manage exceptions
class MustardSimplify_Exception(bpy.types.PropertyGroup):
    exception: bpy.props.PointerProperty(type=bpy.types.Object)
    modifiers: bpy.props.BoolProperty(name="Modifiers",
                                        description="Disable modifiers",
                                        default=False)
    shape_keys: bpy.props.BoolProperty(name="Shape Keys",
                                        description="Mute un-used shape keys (value different from 0)",
                                        default=False)
    drivers: bpy.props.BoolProperty(name="Drivers",
                                        description="Disable Drivers",
                                        default=False)
    normals_auto_smooth: bpy.props.BoolProperty(name="Normals Auto Smooth",
                                        description="Disable Normals Auto Smooth",
                                        default=False)
bpy.utils.register_class(MustardSimplify_Exception)

class MustardSimplify_Exceptions(bpy.types.PropertyGroup):
    exceptions: bpy.props.CollectionProperty(type=MustardSimplify_Exception)
            
bpy.utils.register_class(MustardSimplify_Exceptions)
bpy.types.Scene.MustardSimplify_Exceptions = bpy.props.PointerProperty(type=MustardSimplify_Exceptions)

# ------------------------------------------------------------------------
#    Normal Maps Optimizer (thanks to theoldben)
# ------------------------------------------------------------------------
# Original implementation: https://github.com/theoldben/BlenderNormalGroups

class MUSTARDSIMPLIFY_OT_FastNormals(bpy.types.Operator):
    bl_description = "Switch normal map nodes to a faster custom node"
    bl_idname = 'mustard_simplify.fast_normals'
    bl_label = "Eevee Fast Normals"
    bl_options = {'UNDO'}
    
    custom: bpy.props.BoolProperty(
        name="To Custom",
        description="Set all normals to custom group, or revert back to normal",
        default=True,
    )
    
    @classmethod
    def poll(self, context):
        return (bpy.data.materials or bpy.data.node_groups)

    def execute(self, context):
        
        def mirror(new, old):
            """Copy attributes of the old node to the new node"""
            new.parent = old.parent
            new.label = old.label
            new.mute = old.mute
            new.hide = old.hide
            new.select = old.select
            new.location = old.location

            # inputs
            for (name, point) in old.inputs.items():
                input = new.inputs.get(name)
                if input:
                    input.default_value = point.default_value
                    for link in point.links:
                        new.id_data.links.new(link.from_socket, input)

            # outputs
            for (name, point) in old.outputs.items():
                output = new.outputs.get(name)
                if output:
                    output.default_value = point.default_value
                    for link in point.links:
                        new.id_data.links.new(output, link.to_socket)

        def get_custom():
            name = 'Normal Map Optimized'
            group = bpy.data.node_groups.get(name)

            if not group and self.custom:
                group = default_custom_nodes()

            return group

        def set_custom(nodes):
            group = get_custom()
            if not group:
                return

            for node in reversed(nodes):
                new = None
                if self.custom:
                    if isinstance(node, bpy.types.ShaderNodeNormalMap):
                        new = nodes.new(type='ShaderNodeGroup')
                        new.node_tree = group
                else:
                    if isinstance(node, bpy.types.ShaderNodeGroup):
                        if node.node_tree == group:
                            new = nodes.new(type='ShaderNodeNormalMap')

                if new:
                    name = node.name
                    mirror(new, node)
                    
                    if isinstance(node, bpy.types.ShaderNodeNormalMap):
                        uvNode = nodes.new('ShaderNodeUVMap')
                        uvNode.uv_map = node.uv_map
                        uvNode.name = node.name+" UV"
                        uvNode.parent = new.parent
                        uvNode.mute = True
                        uvNode.hide = True
                        uvNode.select = False
                        uvNode.location = Vector((new.location.x, new.location.y-150.))
                        uvNode.id_data.links.new(uvNode.outputs['UV'], new.inputs[2])
                    else:
                        try:
                            try:
                                uvNode = nodes[node.name+" UV"]
                            except:
                                for input in node.inputs:
                                    if input and isinstance(input, bpy.types.NodeSocketVector) and input.is_linked:
                                        if isinstance(input.links[0].from_node, bpy.types.ShaderNodeUVMap):
                                            uvNode = input.links[0].from_node
                                            break
                            new.uv_map = uvNode.uv_map
                            nodes.remove(uvNode)
                        except:
                            print("Mustard Simplify - Could not restore UV before using Fast Normals")
                            pass
                    
                    nodes.remove(node)
                    new.name = name

        for mat in bpy.data.materials:
            set_custom(getattr(mat.node_tree, 'nodes', []))
        for group in bpy.data.node_groups:
            set_custom(group.nodes)

        if (not self.custom) and get_custom():
            bpy.data.node_groups.remove(get_custom())
        
        settings = bpy.context.scene.MustardSimplify_Settings
        settings.simplify_fastnormals_status = self.custom
        
        return {'FINISHED'}

def default_custom_nodes():
    use_new_nodes = bpy.app.version >= (2, 81) and bpy.app.version < (3, 2, 0)

    group = bpy.data.node_groups.new('Normal Map Optimized', 'ShaderNodeTree')

    nodes = group.nodes
    links = group.links

    # Input
    input = group.interface.new_socket("Strength", in_out='INPUT', socket_type='NodeSocketFloat')
    input.default_value = 1.0
    input.min_value = 0.0
    input.max_value = 1.0
    input = group.interface.new_socket("Color", in_out='INPUT', socket_type='NodeSocketColor')
    input.default_value = ((0.5, 0.5, 1.0, 1.0))
    
    # Input UV as Backup
    input = group.interface.new_socket("UV", in_out='INPUT', socket_type='NodeSocketVector')

    # Output
    group.interface.new_socket("Normal", in_out='OUTPUT', socket_type='NodeSocketVector')
    
    # Add Nodes
    frame = nodes.new('NodeFrame')
    frame.name = 'Matrix * Normal Map'
    frame.label = 'Matrix * Normal Map'
    frame.location = Vector((540.0, -80.0))
    frame.hide = False
    frame.color = Color((0.6079999804496765, 0.6079999804496765, 0.6079999804496765))
    node = nodes.new('ShaderNodeVectorMath')
    node.name = 'Vector Math'
    node.label = ''
    node.parent = frame
    node.hide = True
    node.color = Color((0.6079999804496765, 0.6079999804496765, 0.6079999804496765))
    node.location = Vector((-60.0, 20.0))
    node.operation = 'DOT_PRODUCT'
    node.inputs[0].default_value = (0.5, 0.5, 0.5)  # Vector
    node.inputs[1].default_value = (0.5, 0.5, 0.5)  # Vector
    if use_new_nodes:
        node.inputs[2].default_value = (1.0, 1.0, 1.0)  # Scale
    node = nodes.new('ShaderNodeVectorMath')
    node.name = 'Vector Math.001'
    node.label = ''
    node.parent = frame
    node.hide = True
    node.color = Color((0.6079999804496765, 0.6079999804496765, 0.6079999804496765))
    node.location = Vector((-60.0, -20.0))
    node.operation = 'DOT_PRODUCT'
    node.inputs[0].default_value = (0.5, 0.5, 0.5)  # Vector
    node.inputs[1].default_value = (0.5, 0.5, 0.5)  # Vector
    if use_new_nodes:
        node.inputs[2].default_value = (1.0, 1.0, 1.0)  # Scale
    node = nodes.new('ShaderNodeVectorMath')
    node.name = 'Vector Math.002'
    node.label = ''
    node.parent = frame
    node.hide = True
    node.color = Color((0.6079999804496765, 0.6079999804496765, 0.6079999804496765))
    node.location = Vector((-60.0, -60.0))
    node.inputs[0].default_value = (0.5, 0.5, 0.5)  # Vector
    node.inputs[1].default_value = (0.5, 0.5, 0.5)  # Vector
    if use_new_nodes:
        node.inputs[2].default_value = (1.0, 1.0, 1.0)  # Scale
    node.operation = 'DOT_PRODUCT'
    node = nodes.new('ShaderNodeCombineXYZ')
    node.name = 'Combine XYZ'
    node.label = ''
    node.parent = frame
    node.hide = True
    node.color = Color((0.6079999804496765, 0.6079999804496765, 0.6079999804496765))
    node.location = Vector((100.0, -20.0))
    node.inputs[0].default_value = 0.0  # X
    node.inputs[1].default_value = 0.0  # Y
    node.inputs[2].default_value = 0.0  # Z

    frame = nodes.new('NodeFrame')
    frame.name = 'Generate TBN from Bump Node'
    frame.label = 'Generate TBN from Bump Node'
    frame.location = Vector((-192.01412963867188, -77.50459289550781))
    frame.hide = False
    frame.color = Color((0.6079999804496765, 0.6079999804496765, 0.6079999804496765))
    node = nodes.new('ShaderNodeUVMap')
    node.name = 'UV Map'
    node.label = ''
    node.parent = frame
    node.hide = True
    node.color = Color((0.6079999804496765, 0.6079999804496765, 0.6079999804496765))
    node.location = Vector((-247.98587036132812, -2.4954071044921875))
    node = nodes.new('ShaderNodeSeparateXYZ')
    node.name = 'UV Gradients'
    node.label = 'UV Gradients'
    node.parent = frame
    node.hide = True
    node.color = Color((0.6079999804496765, 0.6079999804496765, 0.6079999804496765))
    node.location = Vector((-87.98587036132812, -2.4954071044921875))
    node.inputs[0].default_value = (0.0, 0.0, 0.0)  # Vector
    # node.outputs.remove((node.outputs['Z']))
    node = nodes.new('ShaderNodeNewGeometry')
    node.name = 'Normal'
    node.label = 'Normal'
    node.parent = frame
    node.hide = True
    node.color = Color((0.6079999804496765, 0.6079999804496765, 0.6079999804496765))
    node.location = Vector((72.01412963867188, -62.49540710449219))
    # for out in node.outputs:
    #     if out.name not in ['Normal']:
    #         node.outputs.remove(out)
    node = nodes.new('ShaderNodeBump')
    node.name = 'Bi-Tangent'
    node.label = 'Bi-Tangent'
    node.parent = frame
    node.hide = True
    node.color = Color((0.6079999804496765, 0.6079999804496765, 0.6079999804496765))
    node.location = Vector((72.01412963867188, -22.495407104492188))
    node.invert = True
    node.inputs[0].default_value = 1.0  # Strength
    node.inputs[1].default_value = 1000.0  # Distance
    node.inputs[2].default_value = 1.0  # Height
    if use_new_nodes:
        node.inputs[3].default_value = 1.0  # Height_dx
        node.inputs[4].default_value = 1.0  # Height_dy
        node.inputs[5].default_value = (0.0, 0.0, 0.0)  # Normal
    else:
        node.inputs[3].default_value = (0.0, 0.0, 0.0)  # Normal
    
    node = nodes.new('ShaderNodeBump')
    node.name = 'Tangent'
    node.label = 'Tangent'
    node.parent = frame
    node.hide = True
    node.color = Color((0.6079999804496765, 0.6079999804496765, 0.6079999804496765))
    node.location = Vector((72.01412963867188, 17.504592895507812))
    node.invert = True

    frame = nodes.new('NodeFrame')
    frame.name = 'Node'
    frame.label = 'Normal Map Processing'
    frame.location = Vector((180.0, -260.0))
    frame.hide = False
    frame.color = Color((0.6079999804496765, 0.6079999804496765, 0.6079999804496765))
    node = nodes.new('NodeGroupInput')
    node.name = 'Group Input'
    node.label = ''
    node.parent = frame
    node.hide = True
    node.color = Color((0.6079999804496765, 0.6079999804496765, 0.6079999804496765))
    node.location = Vector((-400.0, 20.0))
    node = nodes.new('ShaderNodeMixRGB')
    node.name = 'Influence'
    node.label = ''
    node.parent = frame
    node.hide = True
    node.location = Vector((-240.0, 20.0))
    node.inputs[1].default_value = (0.5, 0.5, 1.0, 1.0)  # Color1
    node = nodes.new('ShaderNodeVectorMath')
    node.name = 'Vector Math.003'
    node.label = ''
    node.parent = frame
    node.hide = True
    node.color = Color((0.6079999804496765, 0.6079999804496765, 0.6079999804496765))
    node.location = Vector((-80.0, 20.0))
    node.operation = 'SUBTRACT'
    node.inputs[0].default_value = (0.5, 0.5, 0.5)  # Vector
    node.inputs[1].default_value = (0.5, 0.5, 0.5)  # Vector
    if use_new_nodes:
        node.inputs[2].default_value = (1.0, 1.0, 1.0)  # Scale
    # node.inputs.remove(node.inputs[1])
    node = nodes.new('ShaderNodeVectorMath')
    node.name = 'Vector Math.004'
    node.label = ''
    node.parent = frame
    node.hide = True
    node.color = Color((0.6079999804496765, 0.6079999804496765, 0.6079999804496765))
    node.location = Vector((80.0, 20.0))
    node.inputs[0].default_value = (0.5, 0.5, 0.5)  # Vector
    node.inputs[1].default_value = (0.5, 0.5, 0.5)  # Vector
    if use_new_nodes:
        node.inputs[2].default_value = (1.0, 1.0, 1.0)  # Scale

    frame = nodes.new('NodeFrame')
    frame.name = 'Transpose Matrix'
    frame.label = 'Transpose Matrix'
    frame.location = Vector((180.0, -80.0))
    frame.hide = False
    frame.color = Color((0.6079999804496765, 0.6079999804496765, 0.6079999804496765))
    node = nodes.new('ShaderNodeCombineXYZ')
    node.name = 'Combine XYZ.001'
    node.label = ''
    node.parent = frame
    node.hide = True
    node.color = Color((0.6079999804496765, 0.6079999804496765, 0.6079999804496765))
    node.location = Vector((80.0, 20.0))
    node.inputs[0].default_value = 0.0  # X
    node.inputs[1].default_value = 0.0  # Y
    node.inputs[2].default_value = 0.0  # Z
    node = nodes.new('ShaderNodeCombineXYZ')
    node.name = 'Combine XYZ.002'
    node.label = ''
    node.parent = frame
    node.hide = True
    node.color = Color((0.6079999804496765, 0.6079999804496765, 0.6079999804496765))
    node.location = Vector((80.0, -20.0))
    node.inputs[0].default_value = 0.0  # X
    node.inputs[1].default_value = 0.0  # Y
    node.inputs[2].default_value = 0.0  # Z
    node = nodes.new('ShaderNodeCombineXYZ')
    node.name = 'Combine XYZ.003'
    node.label = ''
    node.parent = frame
    node.hide = True
    node.color = Color((0.6079999804496765, 0.6079999804496765, 0.6079999804496765))
    node.location = Vector((80.0, -60.0))
    node.inputs[0].default_value = 0.0  # X
    node.inputs[1].default_value = 0.0  # Y
    node.inputs[2].default_value = 0.0  # Z
    node = nodes.new('ShaderNodeSeparateXYZ')
    node.name = 'Separate XYZ.001'
    node.label = ''
    node.parent = frame
    node.hide = True
    node.color = Color((0.6079999804496765, 0.6079999804496765, 0.6079999804496765))
    node.location = Vector((-80.0, 20.0))
    node.inputs[0].default_value = (0.0, 0.0, 0.0)  # Vector
    node = nodes.new('ShaderNodeSeparateXYZ')
    node.name = 'Separate XYZ.002'
    node.label = ''
    node.parent = frame
    node.hide = True
    node.color = Color((0.6079999804496765, 0.6079999804496765, 0.6079999804496765))
    node.location = Vector((-80.0, -20.0))
    node.inputs[0].default_value = (0.0, 0.0, 0.0)  # Vector
    node = nodes.new('ShaderNodeSeparateXYZ')
    node.name = 'Separate XYZ.003'
    node.label = ''
    node.parent = frame
    node.hide = True
    node.color = Color((0.6079999804496765, 0.6079999804496765, 0.6079999804496765))
    node.location = Vector((-80.0, -60.0))
    node.inputs[0].default_value = (0.0, 0.0, 0.0)  # Vector

    node = nodes.new('NodeGroupOutput')
    node.name = 'Group Output'
    node.label = ''
    node.location = Vector((840.0, -80.0))
    node.hide = False
    node.color = Color((0.6079999804496765, 0.6079999804496765, 0.6079999804496765))
    node.inputs[0].default_value = (0.0, 0.0, 0.0)  # Normal

    # Connect the nodes
    links.new(nodes['Group Input'].outputs['Strength'], nodes['Influence'].inputs[0])
    links.new(nodes['Group Input'].outputs['Color'], nodes['Influence'].inputs[2])
    links.new(nodes['Influence'].outputs['Color'], nodes['Vector Math.003'].inputs[0])
    links.new(nodes['UV Gradients'].outputs['X'], nodes['Tangent'].inputs['Height'])
    links.new(nodes['UV Gradients'].outputs['Y'], nodes['Bi-Tangent'].inputs['Height'])
    links.new(nodes['UV Map'].outputs['UV'], nodes['UV Gradients'].inputs['Vector'])
    links.new(nodes['Tangent'].outputs['Normal'], nodes['Separate XYZ.001'].inputs[0])
    links.new(nodes['Bi-Tangent'].outputs['Normal'], nodes['Separate XYZ.002'].inputs[0])
    links.new(nodes['Normal'].outputs['Normal'], nodes['Separate XYZ.003'].inputs[0])
    links.new(nodes['Vector Math.004'].outputs['Vector'], nodes['Vector Math'].inputs[1])
    links.new(nodes['Combine XYZ.001'].outputs['Vector'], nodes['Vector Math'].inputs[0])
    links.new(nodes['Vector Math.004'].outputs['Vector'], nodes['Vector Math.001'].inputs[1])
    links.new(nodes['Combine XYZ.002'].outputs['Vector'], nodes['Vector Math.001'].inputs[0])
    links.new(nodes['Vector Math.004'].outputs['Vector'], nodes['Vector Math.002'].inputs[1])
    links.new(nodes['Combine XYZ.003'].outputs['Vector'], nodes['Vector Math.002'].inputs[0])
    links.new(nodes['Vector Math.003'].outputs['Vector'], nodes['Vector Math.004'].inputs[0])
    links.new(nodes['Vector Math.003'].outputs['Vector'], nodes['Vector Math.004'].inputs[1])
    links.new(nodes['Vector Math'].outputs['Value'], nodes['Combine XYZ'].inputs['X'])
    links.new(nodes['Vector Math.001'].outputs['Value'], nodes['Combine XYZ'].inputs['Y'])
    links.new(nodes['Vector Math.002'].outputs['Value'], nodes['Combine XYZ'].inputs['Z'])
    links.new(nodes['Separate XYZ.001'].outputs['X'], nodes['Combine XYZ.001'].inputs['X'])
    links.new(nodes['Separate XYZ.002'].outputs['X'], nodes['Combine XYZ.001'].inputs['Y'])
    links.new(nodes['Separate XYZ.003'].outputs['X'], nodes['Combine XYZ.001'].inputs['Z'])
    links.new(nodes['Separate XYZ.001'].outputs['Y'], nodes['Combine XYZ.002'].inputs['X'])
    links.new(nodes['Separate XYZ.002'].outputs['Y'], nodes['Combine XYZ.002'].inputs['Y'])
    links.new(nodes['Separate XYZ.003'].outputs['Y'], nodes['Combine XYZ.002'].inputs['Z'])
    links.new(nodes['Separate XYZ.001'].outputs['Z'], nodes['Combine XYZ.003'].inputs['X'])
    links.new(nodes['Separate XYZ.002'].outputs['Z'], nodes['Combine XYZ.003'].inputs['Y'])
    links.new(nodes['Separate XYZ.003'].outputs['Z'], nodes['Combine XYZ.003'].inputs['Z'])
    links.new(nodes['Combine XYZ'].outputs['Vector'], nodes['Group Output'].inputs['Normal'])

    return group

# ------------------------------------------------------------------------
#    Simplify Scene
# ------------------------------------------------------------------------

class MUSTARDSIMPLIFY_OT_SimplifyScene(bpy.types.Operator):
    """Simplify the scene to increase the viewport performance"""
    bl_idname = "mustard_simplify.scene"
    bl_label = "Simplify Scene"
    bl_options = {'UNDO'}
    
    enable_simplify: bpy.props.BoolProperty(name="Simplify",
                                default=True)
    
    @classmethod
    def poll(cls, context):
        
        scene = context.scene
        settings = scene.MustardSimplify_Settings
        
        if not settings.simplify_status:
            return settings.modifiers or settings.shape_keys or settings.physics or settings.drivers or settings.normals_auto_smooth
        else:
            return True

    def execute(self, context):
        
        def add_prop_status (collection, item):
            for el in collection:
                if el.name == item[0] and el.status == item[1]:
                    return
            add_item = collection.add()
            add_item.name = item[0]
            add_item.status = item[1]
            return
        
        def find_prop_status (collection, mod):
            for el in collection:
                if el.name == mod.name:
                    return el.name, el.status
            return "", None
        
        def find_exception_obj (collection, obj):
            for el in collection:
                if el.exception == obj:
                    return el
            return None
        
        def has_keyframe(ob, attr):
            anim = ob.animation_data
            if anim is not None and anim.action is not None:
                for fcu in anim.action.fcurves:
                    if fcu.data_path == attr:
                        return len(fcu.keyframe_points) > 0
            return False
        
        def has_driver(ob, attr):
            anim = ob.animation_data
            if anim is not None and anim.drivers is not None:
                for fcu in anim.drivers:
                    if fcu.data_path == attr:
                        return True
            return False
        
        scene = context.scene
        settings = scene.MustardSimplify_Settings
        
        # BLENDER SIMPLIFY
        rd = context.scene.render
        if settings.blender_simplify:
            rd.use_simplify = self.enable_simplify
        
        # OBJECTS
        
        # Remove objects in the exception collection
        objects = [x for x in bpy.data.objects if x.override_library == None]
        if settings.exception_collection != None:
            objects = [x for x in bpy.data.objects if not x in [x for x in settings.exception_collection.objects]]
        
        # Create list of modifiers to simplify
        if settings.modifiers:
            
            chosen_mods = scene.MustardSimplify_SetModifiers.modifiers
            
            # If the user hasn't used the Modifiers menu, use the default settings
            if not len(chosen_mods):
                modifiers_ignore = settings.modifiers_ignore
            else:
                modifiers_ignore = [x.name for x in chosen_mods if not x.simplify]
        
        if settings.debug:
            print("\n ----------- MUSTARD SIMPLIFY LOG -----------")
        
        for obj in objects:
            
            eo = find_exception_obj(scene.MustardSimplify_Exceptions.exceptions, obj)
            
            if settings.debug:
                print("\n ----------- Object: " + obj.name + " -----------")
            
            # Modifiers
            if settings.modifiers and (eo.modifiers if eo != None else True):
                
                modifiers = [x for x in obj.modifiers if not x.type in modifiers_ignore]
                
                if self.enable_simplify:
                    obj.MustardSimplify_Status.modifiers.clear()
                    for mod in modifiers:
                        status = mod.show_viewport
                        add_prop_status(obj.MustardSimplify_Status.modifiers, [mod.name, status])
                        mod.show_viewport = False
                        if settings.debug:
                            print("Modifier " + mod.name + " disabled (previous viewport_hide: " + str(status) + ").")
                else:
                    for mod in modifiers:
                        name, status = find_prop_status(obj.MustardSimplify_Status.modifiers, mod)
                        if name != "":
                            mod.show_viewport = status
                            if settings.debug:
                                print("Modifier " + mod.name + " reverted to viewport_hide: " + str(status) + ".")
            
            # Shape Keys
            if settings.shape_keys and obj.type == "MESH" and (eo.shape_keys if eo != None else True):
                
                if self.enable_simplify:
                    obj.MustardSimplify_Status.shape_keys.clear()
                    if obj.data.shape_keys != None:
                        for sk in obj.data.shape_keys.key_blocks:
                            status = sk.mute
                            add_prop_status(obj.MustardSimplify_Status.shape_keys, [sk.name, status])
                            attr = 'key_blocks["'+sk.name+'"].value'
                            value_bool = True if sk.value < 1e-5 else False
                            if has_driver(obj.data.shape_keys, attr):
                                sk.mute = value_bool if (settings.shape_keys_disable_with_drivers and settings.shape_keys_disable_with_drivers_not_null) else settings.shape_keys_disable_with_drivers
                            elif has_keyframe(obj.data.shape_keys, attr):
                                sk.mute = settings.shape_keys_disable_with_keyframes
                            else:
                                sk.mute = value_bool if settings.shape_keys_disable_not_null else True
                            if settings.debug:
                                if sk.mute:
                                    print("Shape key " + sk.name + " disabled (previous mute: " + str(status) + ").")
                                else:
                                    print("Shape key " + sk.name + " not muted (previous mute: " + str(status) + ").")
                else:
                    if obj.data.shape_keys != None:
                        for sk in obj.data.shape_keys.key_blocks:
                            name, status = find_prop_status(obj.MustardSimplify_Status.shape_keys, sk)
                            if name != "":
                                sk.mute = status
                                if settings.debug:
                                    print("Shape key " + sk.name + " reverted to mute: " + str(status) + ".")
            
            # Normals Auto Smooth
            if settings.normals_auto_smooth and obj.type == "MESH" and (eo.normals_auto_smooth if eo != None else True):
                
                if self.enable_simplify:
                    status = obj.data.use_auto_smooth
                    obj.MustardSimplify_Status.normals_auto_smooth = obj.data.use_auto_smooth
                    obj.data.use_auto_smooth = False
                    if settings.debug:
                        print("Normals Auto Smooth disabled (previous status: " + str(status) + ").")
                else:
                    obj.data.use_auto_smooth = obj.MustardSimplify_Status.normals_auto_smooth
                    if settings.debug:
                        print("Normals Auto Smooth reverted to status: " + str(obj.data.use_auto_smooth) + ".")
        
        # SCENE
        if settings.physics:
            
            # Rigid Body World
            if context.scene.rigidbody_world:
                
                if settings.debug:
                    print("\n ----------- Scene: " + scene.name + " -----------")
                
                if self.enable_simplify:
                    status = scene.rigidbody_world.enabled
                    scene.MustardSimplify_Status.rigidbody_world = status
                    scene.rigidbody_world.enabled = False
                    if settings.debug:
                        print("Rigid Body World disabled (previous status: " + str(status) + ").")
                else:
                    scene.rigidbody_world.enabled = scene.MustardSimplify_Status.rigidbody_world
                    if settings.debug:
                        print("Rigid Body World disabled reverted to status: " + str(scene.rigidbody_world.enabled) + ").")
        
        # DRIVERS
        if settings.drivers:
            collections = ["scenes","objects","meshes","materials","textures","speakers",
                           "worlds","curves","armatures","particles","lattices","shape_keys","lights","cameras"]
            num_drivers = 0
            
            for col in collections:
                collection = eval("bpy.data.%s"%col)
                if col == "objects":
                    collection = objects
                for ob in collection:
                    if col == "objects":
                        eo = find_exception_obj(scene.MustardSimplify_Exceptions.exceptions, ob)
                    if ob.animation_data is not None:
                        for driver in ob.animation_data.drivers:
                            dp = driver.data_path
                            pp = dp
                            if dp.find("[") != 0:pp = ".%s"%dp
                            resolved = False
                            try:
                                dob = ob.path_resolve(dp)
                                resolved = True
                            except:
                                dob = None
                                
                            if not resolved:
                                try:
                                    dob = eval('bpy.data.%s["%s"]%s' % (col,ob.name,pp))
                                    resolved = True
                                except:
                                    dob = None
                                
                            idx = driver.array_index
                            if dob is not None and (isinstance(dob,Vector) or isinstance(dob,Color)):
                                pp = "%s[%d]"%(pp,idx)
                            if col == "objects":
                                driver.mute = self.enable_simplify and (eo.drivers if eo != None else True)
                            else:
                                driver.mute = self.enable_simplify
                            num_drivers = num_drivers + 1
            
            if settings.debug and self.enable_simplify:
                print("\n ----------- Drivers disabled: " + str(num_drivers) + " -----------")
            if settings.debug and not self.enable_simplify:
                print("\n ----------- Drivers reverted: " + str(num_drivers) + " -----------")
        
        if settings.debug:
            print("\n")
        
        settings.simplify_status = self.enable_simplify
        
        if self.enable_simplify:
            self.report({'INFO'}, 'Mustard Simplify - Simplify Enabled.')
        else:
            self.report({'INFO'}, 'Mustard Simplify - Simplify Disabled.')
        
        return {'FINISHED'}

# ------------------------------------------------------------------------
#    Blender Simplify Settings
# ------------------------------------------------------------------------

class MUSTARDSIMPLIFY_OT_MenuBlenderSimplifySettings(bpy.types.Operator):
    """Modify Blender Simplify settings"""
    bl_idname = "mustard_simplify.menu_blender_simplify_settings"
    bl_label = "Blender Simplify Settings"
    
    @classmethod
    def poll(cls, context):
        return True
 
    def execute(self, context):
        
        return{'FINISHED'}
    
    def invoke(self, context, event):
        
        return context.window_manager.invoke_props_dialog(self, width = 400)
            
    def draw(self, context):
        
        scene = context.scene
        modifiers = scene.MustardSimplify_SetModifiers.modifiers
        settings = bpy.context.scene.MustardSimplify_Settings
        
        layout = self.layout
        layout.use_property_split = True
        rd = scene.render
        
        # Viewport
        box = layout.box()
        
        box.label(text="Viewport", icon="RESTRICT_VIEW_ON")

        flow = box.grid_flow(row_major=True, columns=0, even_columns=False, even_rows=False, align=True)

        col = flow.column()
        col.prop(rd, "simplify_subdivision", text="Max Subdivision")
        col = flow.column()
        col.prop(rd, "simplify_child_particles", text="Max Child Particles")
        col = flow.column()
        col.prop(rd, "simplify_volumes", text="Volume Resolution")
        if context.engine in 'BLENDER_EEVEE_NEXT':
            col = flow.column()
            col.prop(rd, "simplify_shadows", text="Shadow Resolution")
        
        # Render
        box = layout.box()
        
        box.label(text="Render", icon="RESTRICT_RENDER_ON")

        flow = box.grid_flow(row_major=True, columns=0, even_columns=False, even_rows=False, align=True)
        
        col = flow.column()
        col.prop(rd, "simplify_subdivision_render", text="Max Subdivision")
        col = flow.column()
        col.prop(rd, "simplify_child_particles_render", text="Max Child Particles")
        if context.engine in 'BLENDER_EEVEE_NEXT':
            col = flow.column()
            col.prop(rd, "simplify_shadows_render", text="Shadow Resolution")
        
        

# ------------------------------------------------------------------------
#    Modifiers Select
# ------------------------------------------------------------------------

# Classes to manage exceptions
class MustardSimplify_SetModifier(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(default="")
    disp_name: bpy.props.StringProperty(default="")
    icon: bpy.props.StringProperty(default="")
    simplify: bpy.props.BoolProperty(default=True)
bpy.utils.register_class(MustardSimplify_SetModifier)

class MustardSimplify_SetModifiers(bpy.types.PropertyGroup):
    modifiers: bpy.props.CollectionProperty(type=MustardSimplify_SetModifier)
bpy.utils.register_class(MustardSimplify_SetModifiers)
bpy.types.Scene.MustardSimplify_SetModifiers = bpy.props.PointerProperty(type=MustardSimplify_SetModifiers)

class MUSTARDSIMPLIFY_OT_MenuModifiersSelect(bpy.types.Operator):
    """Select the modifiers affected by the simplification process"""
    bl_idname = "mustard_simplify.menu_modifiers_select"
    bl_label = "Select Modifiers to Simplify"
    
    @classmethod
    def poll(cls, context):
        # Enable operator only when the scene is not simplified
        settings = bpy.context.scene.MustardSimplify_Settings
        return not settings.simplify_status
 
    def execute(self, context):
        
        return{'FINISHED'}
    
    def invoke(self, context, event):
        
        def add_modifier (collection, name, disp_name, icon, simplify):
            for el in collection:
                if el.name == name:
                    return False
            add_item = collection.add()
            add_item.name = name
            add_item.disp_name = disp_name
            add_item.icon = icon
            add_item.simplify = simplify
            return True
        
        scene = bpy.context.scene
        settings = scene.MustardSimplify_Settings
        modifiers = scene.MustardSimplify_SetModifiers.modifiers
        
        # Extract type of modifiers
        rna = bpy.ops.object.modifier_add.get_rna_type()
        mods_list = rna.bl_rna.properties['type'].enum_items.keys()
        
        # Make the list
        # This is done at run-time, so it should be version agnostic
        if len(mods_list) != len(modifiers):
            
            modifiers.clear()
        
            for m in mods_list:
                
                # Change the displayed name
                disp_name = m.replace("_", " ")
                disp_name = disp_name.title()
                
                icon = "MOD_"+m
                simplify = True
                
                # Manage single exceptions
                if m in ["MESH_CACHE", "MESH_SEQUENCE_CACHE", "LAPLACIANDEFORM", "MESH_DEFORM", "SURFACE_DEFORM", "SURFACE"]:
                    icon = "MOD_MESHDEFORM"
                if m in ["LAPLACIANDEFORM"]:
                    icon = "MOD_MESHDEFORM"
                    disp_name = "Laplacian Deform"
                elif m in ["NORMAL_EDIT",  "WEIGHTED_NORMAL"]:
                    icon = "MOD_NORMALEDIT"
                elif m in ["UV_PROJECT",  "UV_WARP"]:
                    icon = "MOD_UVPROJECT"
                elif m in ['VERTEX_WEIGHT_EDIT', 'VERTEX_WEIGHT_MIX', 'VERTEX_WEIGHT_PROXIMITY']:
                    icon = "MOD_VERTEX_WEIGHT"
                elif m in ['DECIMATE']:
                    icon = "MOD_DECIM"
                elif m in ['EDGE_SPLIT']:
                    icon = "MOD_EDGESPLIT"
                elif m in ['NODES']:
                    icon = "GEOMETRY_NODES"
                elif m in ['MULTIRES']:
                    icon = "MOD_MULTIRES"
                elif m in ["MESH_TO_VOLUME", "VOLUME_TO_MESH", "VOLUME_DISPLACE"]:
                    icon = "VOLUME_DATA"
                elif m in ["WELD"]:
                    icon = "AUTOMERGE_OFF"
                elif m in ['SIMPLE_DEFORM']:
                    icon = "MOD_SIMPLEDEFORM"
                elif m in ['SMOOTH', 'CORRECTIVE_SMOOTH']:
                    icon = "MOD_SMOOTH"
                if m in ["LAPLACIANSMOOTH"]:
                    icon = "MOD_SMOOTH"
                    disp_name = "Laplacian Smooth"
                elif m in ["HOOK"]:
                    icon = m
                elif m in ["COLLISION"]:
                    icon = "MOD_PHYSICS"
                elif m in ["DYNAMIC_PAINT"]:
                    icon = "MOD_DYNAMICPAINT"
                elif m in ["PARTICLE_SYSTEM"]:
                    icon = "MOD_PARTICLES"
                elif m in ["SOFT_BODY"]:
                    icon = "MOD_SOFT"
                
                if m in settings.modifiers_ignore:
                    simplify = False
                
                add_modifier(modifiers, m, disp_name, icon, simplify)
                
            if settings.debug:
                print("Mustard Simplify - Modifiers List generated")
        
        return context.window_manager.invoke_props_dialog(self, width = 800)
            
    def draw(self, context):
        
        scene = bpy.context.scene
        modifiers = scene.MustardSimplify_SetModifiers.modifiers
        settings = bpy.context.scene.MustardSimplify_Settings
        
        layout = self.layout
        box = layout.box()
        
        row = box.row()
        col = row.column()
        
        for m in modifiers:
            if m.name in ["ARRAY", "ARMATURE", "CLOTH"]:
                col = row.column()
            row2 = col.row()
            row2.prop(m, 'simplify', text="")
            # Avoid missing icon error
            try:
                row2.label(text=m.disp_name, icon=m.icon)
            except:
                row2.label(text=m.disp_name, icon="BLANK1")

# ------------------------------------------------------------------------
#    Shape Keys Settings
# ------------------------------------------------------------------------

class MUSTARDSIMPLIFY_OT_MenuShapeKeysSettings(bpy.types.Operator):
    """Modify Shape Keys settings"""
    bl_idname = "mustard_simplify.menu_shape_keys_settings"
    bl_label = "Shape Keys Settings"
    
    @classmethod
    def poll(cls, context):
        # Enable operator only when the scene is not simplified
        settings = bpy.context.scene.MustardSimplify_Settings
        return not settings.simplify_status
 
    def execute(self, context):
        
        return{'FINISHED'}
    
    def invoke(self, context, event):
        
        return context.window_manager.invoke_props_dialog(self, width = 400)
            
    def draw(self, context):
        
        scene = bpy.context.scene
        modifiers = scene.MustardSimplify_SetModifiers.modifiers
        settings = bpy.context.scene.MustardSimplify_Settings
        
        layout = self.layout
        
        box = layout.box()
        box.label(text="Global Settings", icon="SHAPEKEY_DATA")
        col = box.column()
        col.prop(settings, 'shape_keys_disable_not_null')
        
        box = layout.box()
        box.label(text="Driven Shape-Keys", icon="DRIVER")
        col = box.column()
        col.prop(settings, 'shape_keys_disable_with_keyframes')
        col.prop(settings, 'shape_keys_disable_with_drivers')
        row = col.row()
        row.enabled = settings.shape_keys_disable_with_drivers
        row.label(text="", icon="BLANK1")
        row.scale_x =0.5
        row.prop(settings, 'shape_keys_disable_with_drivers_not_null')
        

# ------------------------------------------------------------------------
#    Exceptions - Objects
# ------------------------------------------------------------------------

class MUSTARDSIMPLIFY_OT_AddException(bpy.types.Operator):
    """Add Object to the exceptions list"""
    bl_idname = "mustard_simplify.add_exception"
    bl_label = "Add Object"
    bl_options = {'UNDO'}
    
    @classmethod
    def poll(cls, context):
        # Enable operator only when the scene is not simplified
        settings = bpy.context.scene.MustardSimplify_Settings
        return not settings.simplify_status

    def execute(self, context):
        
        def add_exception (collection, obj):
            for el in collection:
                if el.exception == obj:
                    return False
            add_item = collection.add()
            add_item.exception = obj
            return True
        
        def find_exception (collection, mod):
            for el in collection:
                if el.exception == obj:
                    return el.exception
            return None
        
        settings = bpy.context.scene.MustardSimplify_Settings
        scene = context.scene
        
        if settings.exception_select != None:
            res = add_exception(scene.MustardSimplify_Exceptions.exceptions, settings.exception_select)
            if not res:
                self.report({'ERROR'}, 'Mustard Simplify - Object already added to exceptions.')
        
        settings.exception_select = None
        
        return {'FINISHED'}

class MUSTARDSIMPLIFY_OT_RemoveException(bpy.types.Operator):
    """Remove Object to the exceptions list"""
    bl_idname = "mustard_simplify.remove_exception"
    bl_label = "Remove Object"
    bl_options = {'UNDO'}
    
    @classmethod
    def poll(cls, context):
        return True
    
    def execute(self, context):
        
        scene = context.scene
        index = scene.mustardsimplify_exception_uilist_index
        uilist = scene.MustardSimplify_Exceptions.exceptions
        
        uilist.remove(index)
        index = min(max(0, index - 1), len(uilist) - 1)
        scene.mustardsimplify_exception_uilist_index = index
        
        return{'FINISHED'}

class MUSTARDSIMPLIFY_UL_Exceptions_UIList(bpy.types.UIList):
    """UIList for exceptions."""
    
    def draw_item(self, context, layout, data, item, icon, active_data,
                  active_propname, index):
        
        def draw_icon(layout, icon, cdx):
            if cdx:
                layout.label(text="", icon=icon)
            else:
                layout.label(text="", icon="BLANK1")
        
        scene = context.scene
        settings = scene.MustardSimplify_Settings
        
        item_in_exception_collection = False
        if settings.exception_collection != None:
            item_in_exception_collection = item.exception in [x for x in settings.exception_collection.objects]
        
        # Make sure your code supports all 3 layout types
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.prop(item.exception, 'name', text ="", icon ="OUTLINER_OB_" + item.exception.type, emboss=False, translate=False)
                
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.prop(item.exception, 'name', text ="", icon ="OUTLINER_OB_" + item.exception.type, emboss=False, translate=False)
        
        row = layout.row(align=True)
        draw_icon(row, "COLLECTION_COLOR_01", item_in_exception_collection)
        draw_icon(row, "MODIFIER", item.modifiers)
        draw_icon(row, "SHAPEKEY_DATA", item.shape_keys)
        draw_icon(row, "DRIVER", item.drivers)
        draw_icon(row, "NORMALS_FACE", item.normals_auto_smooth)

# ------------------------------------------------------------------------
#    Data Removal
# ------------------------------------------------------------------------

class MUSTARDSIMPLIFY_OT_DataRemoval(bpy.types.Operator):
    """Remove heavy data from objects"""
    bl_idname = "mustard_simplify.data_removal"
    bl_label = "Remove Data"
    bl_options = {'UNDO'}

    remove_diffeomorphic_data: bpy.props.BoolProperty(default=True,
                    name = "Diffeomorphic",
                    description = "Remove Diffeomorphic data")
    remove_diffeomorphic_data_preserve_morphs: bpy.props.BoolProperty(default=True,
                    name = "Preserve Morphs",
                    description = "Prevent Morphs deletion")
    remove_custom_string_data: bpy.props.StringProperty(default="",
                    name = "Custom Removal",
                    description = "Remove all data blocks which contains this custom string")

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        
        def remove_data(obj, attr):
            try:
                del obj[attr]
                return 1
            except:
                return 0
        
        scene = context.scene
        settings = scene.MustardSimplify_Settings
        
        if settings.debug:
            print("\n ----------- MUSTARD SIMPLIFY DATA REMOVAL LOG -----------\n")
        
        # Decide which data to remove
        to_remove = []
        to_preserve = []
        if self.remove_custom_string_data != "" and settings.advanced:
            to_remove.append(self.remove_custom_string_data)
            if settings.debug:
                print("Removing data with string: " + self.remove_custom_string_data)
        if self.remove_diffeomorphic_data:
            to_remove.append("Daz")
            if settings.debug:
                print("Removing Diffeomorphic data")
            if self.remove_diffeomorphic_data_preserve_morphs:
                to_preserve.append("DazExpressions")
                to_preserve.append("DazFacs")
                to_preserve.append("DazFacsexpr")
                to_preserve.append("DazFlexions")
                to_preserve.append("DazUnits")
                to_preserve.append("DazVisemes")
                to_preserve.append("DazMorphCats")
                to_preserve.append("DazCustomMorphs")
                to_preserve.append("DazCustom")
                to_preserve.append("DazActivated")
        
        if not len(to_remove):
            self.report({'WARNING'}, "Mustard Simplify - No Data Block to remove was selected.")
            return {'FINISHED'}
        
        # Gather Objects
        objects = []
        for obj in bpy.data.objects:
            objects.append(obj)
            if obj.data != None:
                objects.append(obj.data)
        
        # Remove data
        data_deleted = 0
        for obj in objects:
            items_to_remove = []
            for k,v in obj.items():
                for el in to_remove:
                    if el in k:
                        items_to_remove.append(k)
            items_to_remove.reverse()
            if settings.debug and len(items_to_remove) >0:
                print("\n Removing from Object: " + obj.name)
            for k in items_to_remove:
                if not k in to_preserve:
                    data_deleted = data_deleted + remove_data(obj, k)
                if settings.debug:
                    print("   - " + k)
            obj.update_tag()
        
        if data_deleted > 0:
            self.report({'INFO'}, "Mustard Simplify - Data Blocks removed: " + str(data_deleted))
        else:
            self.report({'WARNING'}, "Mustard Simplify - No Data Block to remove was found.")
        
        return {'FINISHED'}
    
    def invoke(self, context, event):
        
        return context.window_manager.invoke_props_dialog(self, width = 400)
    
    def draw(self, context):
        
        scene = context.scene
        settings = scene.MustardSimplify_Settings
        
        layout = self.layout
        
        if settings.advanced:
            box = layout.box()
            box.label(text="General", icon="SETTINGS")
            box.prop(self, 'remove_custom_string_data')
        
        box = layout.box()
        col = box.column()
        col.label(text="External Add-on", icon="WORLD_DATA")
        col.prop(self, 'remove_diffeomorphic_data')
        row = col.row(align=True)
        row.enabled = self.remove_diffeomorphic_data
        row.label(text="", icon="BLANK1")
        row.prop(self, 'remove_diffeomorphic_data_preserve_morphs')

# ------------------------------------------------------------------------
#    Link (thanks to Mets3D)
# ------------------------------------------------------------------------

class MUSTARDSIMPLIFY_OT_LinkButton(bpy.types.Operator):
    """Open links in a web browser"""
    bl_idname = "mustard_simplify.openlink"
    bl_label = "Open Link"
    bl_options = {'REGISTER'}
    
    url: StringProperty(name='URL',
        description="URL",
        default="http://blender.org/"
    )

    def execute(self, context):
        webbrowser.open_new(self.url)
        return {'FINISHED'}

# ------------------------------------------------------------------------
#    UI
# ------------------------------------------------------------------------

class MainPanel:
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Simplify"

class MUSTARDSIMPLIFY_PT_Simplify(MainPanel, bpy.types.Panel):
    bl_idname = "MUSTARDSIMPLIFY_PT_Simplify"
    bl_label = "Simplify"

    def draw(self, context):
        
        scene = context.scene
        layout = self.layout
        settings = scene.MustardSimplify_Settings
        
        if settings.simplify_status:
            op = layout.operator(MUSTARDSIMPLIFY_OT_SimplifyScene.bl_idname, text = "Un-Simplify Scene", icon="MOD_SIMPLIFY", depress=True)
        else:
            op = layout.operator(MUSTARDSIMPLIFY_OT_SimplifyScene.bl_idname, text = "Simplify Scene", icon="MOD_SIMPLIFY")
        op.enable_simplify = not settings.simplify_status
        
        row = layout.row(align=True)
        if settings.simplify_fastnormals_status and scene.render.engine == "CYCLES":
            op2 = row.operator(MUSTARDSIMPLIFY_OT_FastNormals.bl_idname, text = "Enable Eevee Fast Normals" if not settings.simplify_fastnormals_status else "Disable Eevee Fast Normals", icon = "ERROR", depress=settings.simplify_fastnormals_status)
        else:
            row.enabled = not scene.render.engine == "CYCLES"
            op2 = row.operator(MUSTARDSIMPLIFY_OT_FastNormals.bl_idname, text = "Enable Eevee Fast Normals" if not settings.simplify_fastnormals_status else "Disable Eevee Fast Normals", icon="MOD_NORMALEDIT", depress=settings.simplify_fastnormals_status)
        op2.custom = not settings.simplify_fastnormals_status
        
        box=layout.box()
        row = box.row()
        row.prop(settings, 'collapse_options', text="", icon="RIGHTARROW" if settings.collapse_options else "DOWNARROW_HLT", emboss=False)
        row.label(text="Options")
        row.operator(MUSTARDSIMPLIFY_OT_LinkButton.bl_idname, text="", icon="QUESTION").url="https://github.com/Mustard2/MustardSimplify/wiki#simplify"
        if not settings.collapse_options:
            row = box.row()
            col = row.column()
            col.enabled = not settings.simplify_status
            col.prop(settings,"blender_simplify")
            row.operator(MUSTARDSIMPLIFY_OT_MenuBlenderSimplifySettings.bl_idname, icon="PREFERENCES", text="")
            
            col = box.column(align=True)
            col.enabled = not settings.simplify_status
            row = col.row()
            row.prop(settings,"modifiers")
            row.operator(MUSTARDSIMPLIFY_OT_MenuModifiersSelect.bl_idname, icon="PREFERENCES", text="")
            row = col.row()
            row.prop(settings,"shape_keys")
            row.operator(MUSTARDSIMPLIFY_OT_MenuShapeKeysSettings.bl_idname, icon="PREFERENCES", text="")
            col.prop(settings,"drivers")
            col.prop(settings,"physics")
            col.prop(settings,"normals_auto_smooth")
        
        box=layout.box()
        row = box.row()
        row.prop(settings, 'collapse_exceptions', text="", icon="RIGHTARROW" if settings.collapse_exceptions else "DOWNARROW_HLT", emboss=False)
        row.label(text="Exceptions")
        row.operator(MUSTARDSIMPLIFY_OT_LinkButton.bl_idname, text="", icon="QUESTION").url="https://github.com/Mustard2/MustardSimplify/wiki#exceptions"
        if not settings.collapse_exceptions:
            
            row = box.row()
            row.prop(settings, 'exception_type', expand=True)
            
            if settings.exception_type == "OBJECT":
            
                row = box.row()
                row.enabled = not settings.simplify_status
                row.template_list("MUSTARDSIMPLIFY_UL_Exceptions_UIList", "The_List", scene.MustardSimplify_Exceptions,
                                "exceptions", scene, "mustardsimplify_exception_uilist_index")
                col = row.column(align=True)
                col.operator(MUSTARDSIMPLIFY_OT_RemoveException.bl_idname, icon = "REMOVE", text = "")
                
                row = box.row()
                row.enabled = not settings.simplify_status
                row.prop_search(settings, "exception_select", scene, "objects", text = "")
                row.operator(MUSTARDSIMPLIFY_OT_AddException.bl_idname, text="", icon="ADD")
                
                if scene.mustardsimplify_exception_uilist_index > -1 and len(scene.MustardSimplify_Exceptions.exceptions)>0:
                    obj = scene.MustardSimplify_Exceptions.exceptions[scene.mustardsimplify_exception_uilist_index]
                    
                    if obj != None:
                        box = box.box()
                        item_in_exception_collection = False
                        if settings.exception_collection != None:
                            item_in_exception_collection = obj.exception in [x for x in settings.exception_collection.objects]
                        box.enabled = not item_in_exception_collection
                        
                        col = box.column(align=True)
                        col.label(text="Properties to Simplify", icon="PROPERTIES")
                        
                        row = col.row()
                        row.enabled = obj.exception.type == "MESH"
                        row.prop(obj, 'modifiers')
                        
                        row = col.row()
                        row.enabled = obj.exception.type == "MESH"
                        row.prop(obj, 'shape_keys')
                        
                        row = col.row()
                        row.prop(obj, 'drivers')
                        
                        row = col.row()
                        row.enabled = obj.exception.type == "MESH"
                        row.prop(obj, 'normals_auto_smooth')
            
            else:
                
                row = box.row()
                row.enabled = not settings.simplify_status
                row.prop_search(settings, "exception_collection", bpy.data, "collections", text = "")
        
        if settings.advanced:
            box=layout.box()
            row = box.row()
            row.prop(settings, 'collapse_others', text="", icon="RIGHTARROW" if settings.collapse_others else "DOWNARROW_HLT", emboss=False)
            row.label(text="Advanced")
            row.operator(MUSTARDSIMPLIFY_OT_LinkButton.bl_idname, text="", icon="QUESTION").url="https://github.com/Mustard2/MustardSimplify/wiki#advanced"
            if not settings.collapse_others:
                row = box.row()
                
                prefs = context.preferences
                system = prefs.system

                row.label(text="Textures Size Limit")
                row.scale_x = 1.5
                row.prop(system, "gl_texture_limit", text="")
                

class MUSTARDSIMPLIFY_PT_Tools(MainPanel, bpy.types.Panel):
    bl_idname = "MUSTARDSIMPLIFY_PT_Tools"
    bl_label = "Tools"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        
        layout = self.layout
        settings = bpy.context.scene.MustardSimplify_Settings
        
        box=layout.box()
        row = box.row()
        row.label(text="Mesh", icon="OUTLINER_DATA_MESH")
        row.operator(MUSTARDSIMPLIFY_OT_LinkButton.bl_idname, text="", icon="QUESTION").url="https://github.com/Mustard2/MustardSimplify/wiki#tools"
        box.operator(MUSTARDSIMPLIFY_OT_DataRemoval.bl_idname, text="Data Removal", icon="LIBRARY_DATA_BROKEN")

class MUSTARDSIMPLIFY_PT_Settings(MainPanel, bpy.types.Panel):
    bl_idname = "MUSTARDSIMPLIFY_PT_Settings"
    bl_label = "Settings"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        
        layout = self.layout
        settings = bpy.context.scene.MustardSimplify_Settings
        
        box=layout.box()
        box.label(text="Main Settings", icon="SETTINGS")
        col = box.column(align=True)
        col.prop(settings,"advanced")
        col.prop(settings,"debug")
        
        layout.operator(MUSTARDSIMPLIFY_OT_LinkButton.bl_idname, text="Check New Version", icon="URL").url="https://github.com/Mustard2/MustardSimplify/releases"
        layout.operator(MUSTARDSIMPLIFY_OT_LinkButton.bl_idname, text="Report Issue", icon="URL").url="https://github.com/Mustard2/MustardSimplify/issues"

# ------------------------------------------------------------------------
#    Register
# ------------------------------------------------------------------------

classes = (
    MUSTARDSIMPLIFY_OT_FastNormals,
    MUSTARDSIMPLIFY_OT_SimplifyScene,
    MUSTARDSIMPLIFY_OT_MenuBlenderSimplifySettings,
    MUSTARDSIMPLIFY_OT_MenuModifiersSelect,
    MUSTARDSIMPLIFY_OT_MenuShapeKeysSettings,
    MUSTARDSIMPLIFY_OT_AddException,
    MUSTARDSIMPLIFY_OT_RemoveException,
    MUSTARDSIMPLIFY_UL_Exceptions_UIList,
    MUSTARDSIMPLIFY_OT_DataRemoval,
    MUSTARDSIMPLIFY_OT_LinkButton,
    MUSTARDSIMPLIFY_PT_Simplify,
    MUSTARDSIMPLIFY_PT_Tools,
    MUSTARDSIMPLIFY_PT_Settings,
)

def register():
    
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)
    
    # Indexes for UI Lists
    bpy.types.Scene.mustardsimplify_exception_uilist_index = IntProperty(name = "", default = 0)

def unregister():
    
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)

if __name__ == "__main__":
    register()