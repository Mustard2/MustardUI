import bpy
from ..model_selection.active_object import *
from .update_enable import *


def poll_mesh(self, o):
    res, obj = mustardui_active_object(bpy.context, config=1)
    physics_settings = obj.MustardUI_PhysicsSettings

    return o.type == 'MESH' and not (o in [x.object for x in physics_settings.items])


def poll_mesh_linked(self, o):
    res, obj = mustardui_active_object(bpy.context, config=1)
    physics_settings = obj.MustardUI_PhysicsSettings

    return o.type == 'MESH' and (o in [x.object for x in physics_settings.items if x.type == "CAGE"]) and o != self.object


mustardui_physics_item_type = [("NONE", "None", "Disable Physics", "BLANK1", 0),
                               ("CAGE", "Cage", "A mesh that modifies another one through Mesh or Surface Deform modifiers", "MESH_UVSPHERE", 1),
                               ("COLLISION", "Collision", "A mesh that acts as collision for other meshes", "MOD_PHYSICS", 2),
                               ("SINGLE_ITEM", "Single Item", "An item that does not need Mesh or Surface Deform modifiers on the Body or the Outfits", "OBJECT_ORIGIN", 3),
                               ("BONES_DRIVER", "Bone Driver", "An item that drives the motion of bones through Constraints.\nOnly constraints with 'target' are supported", "BONE_DATA", 4)]
mustardui_physics_item_type_dict = {
    "NONE": "BLANK1",
    "CAGE": "MESH_UVSPHERE",
    "COLLISION": "MOD_PHYSICS",
    "SINGLE_ITEM": "OBJECT_ORIGIN",
    "BONES_DRIVER": "BONE_DATA"
}


class MustardUI_PhysicsItem(bpy.types.PropertyGroup):

    enable: bpy.props.BoolProperty(default=False,
                                   name="Enable Physics",
                                   update=enable_physics_update_single)

    unique_cache_frames: bpy.props.BoolProperty(default=False,
                                                name="Unique Cache Frames",
                                                description="Make the starting and ending cache frames for this "
                                                            "object independent from the global cache settings")

    object: bpy.props.PointerProperty(type=bpy.types.Object,
                                      poll=poll_mesh)

    type: bpy.props.EnumProperty(default="NONE",
                                 items=mustardui_physics_item_type,
                                 name="Type")

    collisions: bpy.props.BoolProperty(default=False,
                                       name="Collisions",
                                       description="Enable/disable collisions on the modifiers",
                                       update=collisions_physics_update_single)

    cage_influence: bpy.props.FloatProperty(default=1.0,
                                            max=1.0, min=0.0,
                                            name="Influence",
                                            description="Influence of this Cage on other Objects",
                                            update=cage_influence_update)

    bone_influence: bpy.props.FloatProperty(default=1.0,
                                            max=1.0, min=0.0,
                                            name="Influence",
                                            description="Influence of this item on bones constraints",
                                            update=bone_influence_update)

    # UI Collapse

    # Cloth
    collapse_cloth: bpy.props.BoolProperty(default=True, name="")
    collapse_cloth_stiffness: bpy.props.BoolProperty(default=True, name="")
    collapse_cloth_damping: bpy.props.BoolProperty(default=True, name="")
    collapse_cloth_internal_springs: bpy.props.BoolProperty(default=True, name="")
    collapse_cloth_pressure: bpy.props.BoolProperty(default=True, name="")
    collapse_cloth_cache: bpy.props.BoolProperty(default=True, name="")
    collapse_cloth_collisions: bpy.props.BoolProperty(default=True, name="")
    collapse_cloth_self_collisions: bpy.props.BoolProperty(default=True, name="")

    # Soft Body
    collapse_softbody: bpy.props.BoolProperty(default=True, name="")
    collapse_softbody_cache: bpy.props.BoolProperty(default=True, name="")

    # Collisions
    collapse_collisions: bpy.props.BoolProperty(default=True, name="")



def register():
    bpy.utils.register_class(MustardUI_PhysicsItem)


def unregister():
    bpy.utils.unregister_class(MustardUI_PhysicsItem)
