from typing import NamedTuple

import bpy
from bpy.app.handlers import persistent

from ... import __package__ as base_package
from . import (
    ops_aura,
    ops_billow_dust,
    ops_bulge,
    ops_cloth_rip,
    ops_cloth_tear,
    ops_crush,
    ops_dirt,
    ops_disintegration,
    ops_dust_motes,
    ops_dust_puff,
    ops_fireball,
    ops_foam,
    ops_footprints,
    ops_hex_dissolve,
    ops_imprints,
    ops_jiggle,
    ops_marks,
    ops_rain,
    ops_ripple,
    ops_shatter,
    ops_shockwave,
    ops_shrinkwrap,
    ops_sticky_liquid,
    ops_sticky_spurts,
    ops_sticky_strands,
    ops_wet,
    ops_wrap,
)
from .effect import effects_available, is_effect, materials, shader_nodes


class Effect(NamedTuple):
    icon: str
    node_group: str | None
    material_group: str | None
    # Remove operator, removeprefix("remove_") is the add operator
    remove: str
    # Hidden in the Effects panel unless the Experimental Features preference is on
    experimental: bool = False


EFFECTS = {
    "Ripple": Effect("MOD_WAVE", ops_ripple.NODE_GROUP, None, "remove_ripple"),
    "Jiggle": Effect("MOD_SOFT", ops_jiggle.NODE_GROUP, None, "remove_jiggle_effect"),
    "Sticky Strands": Effect(
        "STRANDS", ops_sticky_strands.NODE_GROUP, None, "remove_sticky_strands"
    ),
    "Sticky Liquid": Effect(
        "MOD_FLUIDSIM", ops_sticky_liquid.NODE_GROUP, None, "remove_sticky_liquid"
    ),
    "Sticky Spurts": Effect(
        "MOD_FLUIDSIM", ops_sticky_spurts.NODE_GROUP, None, "remove_sticky_spurts"
    ),
    "Wet": Effect("MATFLUID", ops_wet.NODE_GROUP, ops_wet.FILM, "remove_wet"),
    "Dirt": Effect("MOD_NOISE", ops_dirt.NODE_GROUP, ops_dirt.FILM, "remove_dirt"),
    "Foam": Effect("OUTLINER_DATA_POINTCLOUD", ops_foam.NODE_GROUP, None, "remove_foam"),
    "Marks": Effect("TPAINT_HLT", ops_marks.NODE_GROUP, None, "remove_marks"),
    "Imprints": Effect("MOD_DISPLACE", ops_imprints.NODE_GROUP, None, "remove_imprints"),
    "Bulge": Effect("SPHERECURVE", ops_bulge.NODE_GROUP, None, "remove_bulge"),
    "Shrinkwrap": Effect("MOD_SHRINKWRAP", ops_shrinkwrap.NODE_GROUP, None, "remove_shrinkwrap"),
    "Dust Puff": Effect("FORCE_TURBULENCE", ops_dust_puff.NODE_GROUP, None, "remove_dust_puff"),
    "Wet Footprints": Effect(
        "MOD_DYNAMICPAINT",
        ops_footprints.NODE_GROUP,
        ops_footprints.FILM,
        "remove_footprints",
    ),
    "Dust Motes": Effect("PARTICLE_POINT", ops_dust_motes.NODE_GROUP, None, "remove_dust_motes"),
    "Aura": Effect("LIGHT_POINT", ops_aura.NODE_GROUP, ops_aura.GLOW, "remove_aura"),
    "Disintegration": Effect(
        "PARTICLES", ops_disintegration.NODE_GROUP, None, "remove_disintegration"
    ),
    "Hex Dissolve": Effect(
        "MESH_ICOSPHERE", None, ops_hex_dissolve.NODE_GROUP, "remove_hex_dissolve"
    ),
    "Cloth Tear": Effect("MOD_CLOTH", ops_cloth_tear.NODE_GROUP, None, "remove_cloth_tear"),
    "Cloth Rip": Effect("EMPTY_SINGLE_ARROW", ops_cloth_rip.NODE_GROUP, None, "remove_cloth_rip"),
    "Shatter": Effect("MOD_EXPLODE", ops_shatter.NODE_GROUP, None, "remove_shatter"),
    "Shockwave": Effect("FORCE_FORCE", ops_shockwave.NODE_GROUP, None, "remove_shockwave"),
    "Crush": Effect("MOD_MESHDEFORM", ops_crush.NODE_GROUP, None, "remove_crush"),
    "Billow Dust": Effect(
        "OUTLINER_OB_VOLUME", ops_billow_dust.NODE_GROUP, None, "remove_billow_dust"
    ),
    "Rope": Effect("CURVE_BEZCIRCLE", ops_wrap.Rope.node_group, None, "remove_rope"),
    "Tape": Effect("MOD_THICKNESS", ops_wrap.Tape.node_group, None, "remove_tape"),
    "Fireball": Effect("LIGHT_SUN", ops_fireball.NODE_GROUP, None, "remove_fireball"),
    "Rain": Effect("FORCE_FLUIDFLOW", ops_rain.NODE_GROUP, None, "remove_rain"),
}


class MustardUI_SceneEffect(bpy.types.PropertyGroup):
    effect: bpy.props.StringProperty()
    object: bpy.props.PointerProperty(type=bpy.types.Object)
    # Empty for the effects in the materials only
    modifier: bpy.props.StringProperty()


def scene_effects(scene):
    """Effect, object and modifier name of the effects in the scene"""
    # The Jiggle of the Physics Items is their physics, and it is set in the Physics panel
    physics = {x.object for arm in bpy.data.armatures for x in arm.MustardUI_PhysicsSettings.items}
    objects = list(scene.objects)
    # Run on each depsgraph update: the modifiers and the materials are read once
    nodes = [(x, mods) for x in objects if (mods := [m for m in x.modifiers if m.type == "NODES"])]
    for name, effect in EFFECTS.items():
        if effect.node_group:
            for obj, mods in nodes:
                if not (name == "Jiggle" and obj in physics):
                    yield from (
                        (name, obj, m.name) for m in mods if is_effect(m, effect.node_group)
                    )
        else:
            tagged = {m for m in materials(objects) if shader_nodes(m, effect.material_group)}
            for obj in objects:
                if any(s.material in tagged for s in obj.material_slots):
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
