import bpy
from bpy.app.handlers import persistent

from ... import __package__ as base_package
from . import (
    ops_aura,
    ops_cloth_tear,
    ops_crush,
    ops_disintegration,
    ops_dust_motes,
    ops_dust_puff,
    ops_fireball,
    ops_foam,
    ops_hex_dissolve,
    ops_imprints,
    ops_marks,
    ops_ripple,
    ops_shatter,
    ops_sticky_liquid,
    ops_sticky_strands,
    ops_wet,
    ops_wrap,
)
from .effect import effects_available, is_effect, materials, shader_nodes

# Icon, modifier node group and material node group of the effects
EFFECTS = {
    "Ripple": ("MOD_WAVE", ops_ripple.NODE_GROUP, None),
    "Sticky Strands": ("STRANDS", ops_sticky_strands.NODE_GROUP, None),
    "Sticky Liquid": ("MOD_FLUIDSIM", ops_sticky_liquid.NODE_GROUP, None),
    "Wet": ("MATFLUID", ops_wet.NODE_GROUP, ops_wet.FILM),
    "Foam": ("OUTLINER_DATA_POINTCLOUD", ops_foam.NODE_GROUP, None),
    "Marks": ("TPAINT_HLT", ops_marks.NODE_GROUP, None),
    "Imprints": ("MOD_DISPLACE", ops_imprints.NODE_GROUP, None),
    "Dust Puff": ("FORCE_TURBULENCE", ops_dust_puff.NODE_GROUP, None),
    "Dust Motes": ("PARTICLE_POINT", ops_dust_motes.NODE_GROUP, None),
    "Aura": ("LIGHT_POINT", ops_aura.NODE_GROUP, ops_aura.GLOW),
    "Disintegration": ("PARTICLES", ops_disintegration.NODE_GROUP, None),
    "Hex Dissolve": ("MESH_ICOSPHERE", None, ops_hex_dissolve.NODE_GROUP),
    "Cloth Tear": ("MOD_CLOTH", ops_cloth_tear.NODE_GROUP, None),
    "Shatter": ("MOD_EXPLODE", ops_shatter.NODE_GROUP, None),
    "Crush": ("MOD_MESHDEFORM", ops_crush.NODE_GROUP, None),
    "Rope": ("CURVE_BEZCIRCLE", ops_wrap.Rope.node_group, None),
    "Tape": ("MOD_THICKNESS", ops_wrap.Tape.node_group, None),
    "Fireball": ("LIGHT_SUN", ops_fireball.NODE_GROUP, None),
}


class MustardUI_SceneEffect(bpy.types.PropertyGroup):
    effect: bpy.props.StringProperty()
    object: bpy.props.PointerProperty(type=bpy.types.Object)
    # Empty for the effects in the materials only
    modifier: bpy.props.StringProperty()


def scene_effects(scene):
    """Effect, object and modifier name of the effects in the scene"""
    for name, (_, node_group, material_group) in EFFECTS.items():
        for obj in scene.objects:
            if node_group:
                yield from ((name, obj, m.name) for m in obj.modifiers if is_effect(m, node_group))
            elif any(shader_nodes(m, material_group) for m in materials([obj])):
                yield name, obj, ""


@persistent
def sync_scene_effects(*args):
    """Update the list of the effects in the scene, keeping the active one"""
    scene = bpy.context.scene
    prefs = bpy.context.preferences.addons[base_package].preferences
    if scene is None or not prefs.model_toolkit or not effects_available():
        return
    effects = list(scene_effects(scene))
    items = scene.MustardUI_SceneEffects
    old = [(x.effect, x.object, x.modifier) for x in items]
    if effects == old:
        return
    index = scene.mustardui_scene_effects_uilist_index
    active = old[index] if index < len(old) else None
    items.clear()
    for effect, obj, modifier in effects:
        item = items.add()
        item.effect, item.object, item.modifier = effect, obj, modifier
    scene.mustardui_scene_effects_uilist_index = (
        effects.index(active) if active in effects else max(0, min(index, len(effects) - 1))
    )


_handlers = (
    bpy.app.handlers.load_post,
    bpy.app.handlers.undo_post,
    bpy.app.handlers.redo_post,
    bpy.app.handlers.depsgraph_update_post,
)


def register():
    bpy.utils.register_class(MustardUI_SceneEffect)
    bpy.types.Scene.MustardUI_SceneEffects = bpy.props.CollectionProperty(
        type=MustardUI_SceneEffect
    )
    bpy.types.Scene.mustardui_scene_effects_uilist_index = bpy.props.IntProperty(name="", default=0)
    for handlers in _handlers:
        handlers.append(sync_scene_effects)


def unregister():
    for handlers in _handlers:
        if sync_scene_effects in handlers:
            handlers.remove(sync_scene_effects)
    del bpy.types.Scene.mustardui_scene_effects_uilist_index
    del bpy.types.Scene.MustardUI_SceneEffects
    bpy.utils.unregister_class(MustardUI_SceneEffect)
