"""Cloth Physics settings: per cloth object and per scene, presets, and the world."""

import bpy

from . import solver

STATE = {"running": False, "stop": False}  # Interactive Mode

FABRIC = (
    "stretch",
    "shear",
    "bend",
    "density",
    "friction",
    "damping",
    "thickness",
    "auto_fit",
    "follow",
)
WORLD_LIVE = (
    "substeps",
    "iterations",
    "gravity",
    "air",
    "smooth_display",
    "self_k",
    "self_radius",
    "untangle",
    "sew_force",
)

QUALITY = {"DRAFT": (32, 6), "NORMAL": (64, 6), "HIGH": (96, 8)}

# stretch, shear, bend (N/m), density (kg/m2), friction
MATERIALS = {
    "COTTON": (1.0e4, 100.0, 300.0, 0.15, 0.3),
    "SILK": (5.0e3, 30.0, 30.0, 0.08, 0.15),
    "DENIM": (3.0e4, 300.0, 3000.0, 0.4, 0.4),
    "LEATHER": (4.0e4, 600.0, 1.0e4, 0.6, 0.5),
    "WOOL": (8.0e3, 150.0, 800.0, 0.3, 0.4),
    "SPANDEX": (1.0e3, 50.0, 100.0, 0.2, 0.5),
}


def fabric_params(st):
    """Fabric of one cloth object"""
    p = dict(solver.DEFAULTS)
    p.update({k: type(p[k])(getattr(st, k)) for k in FABRIC})
    p["sewing"] = int(st.sewing)
    return p


def world_params(st):
    """Settings shared by all cloths, stepped together"""
    p = dict(solver.DEFAULTS)
    p.update(
        substeps=st.substeps,
        iterations=st.iterations,
        gravity=st.gravity,
        air=st.air,
        self_radius=st.self_radius,
    )
    p.update(sew_force=st.sew_force, self_k=solver.DEFAULTS["self_k"] if st.self_collision else 0.0)
    p.update(
        untangle=solver.DEFAULTS["untangle"] if st.untangle else 0,
        smooth_display=int(st.smooth_display),
    )
    return p


def fabric_update(self, context):
    """Fabric changes apply at once to the running cloth"""
    cloth, world = solver.SIMS.get(self.id_data.name), solver.WORLD["world"]
    if cloth and world:
        cloth.fabric.update(fabric_params(self))
        world.solver.upload_params()
        world.solver.upload_attach()


def world_update(self, context):
    world = solver.WORLD["world"]
    if world:
        p = world_params(self)
        world.solver.params.update({k: p[k] for k in WORLD_LIVE})


def quality_update(self, context):
    if self.quality in QUALITY:
        self.substeps, self.iterations = QUALITY[self.quality]


def material_update(self, context):
    if self.material in MATERIALS:
        self.stretch, self.shear, self.bend, self.density, self.friction = MATERIALS[self.material]


def mesh_poll(self, obj):
    return obj.type == "MESH" and obj != self.id_data


def preset_items(names):
    return [(k, k.title(), "") for k in names] + [("CUSTOM", "Custom", "")]


class MustardUI_ModelToolkit_ClothSettings(bpy.types.PropertyGroup):
    enabled: bpy.props.BoolProperty(name="Enabled")
    sim_mesh: bpy.props.EnumProperty(
        name="Simulation Mesh",
        items=[
            ("CAGE", "Before Subdivision", "Simulate the cage, Subdivision smooths the result"),
            (
                "SUBDIVIDED",
                "Subdivided",
                "Simulate the subdivided mesh (finer folds on low poly outfits)",
            ),
        ],
        description="Applied on Rebuild",
    )
    collider: bpy.props.PointerProperty(name="Collider", type=bpy.types.Object, poll=mesh_poll)
    pin_group: bpy.props.StringProperty(
        name="Pin Group", description="Vertices weighted above 0.5 stay fixed"
    )
    pin_target: bpy.props.PointerProperty(
        name="Target Object",
        type=bpy.types.Object,
        poll=mesh_poll,
        description="Pins follow this object's surface",
    )
    material: bpy.props.EnumProperty(
        name="Material", items=preset_items(MATERIALS), default="COTTON", update=material_update
    )
    stretch: bpy.props.FloatProperty(name="Stretch", default=1.0e4, min=1.0, update=fabric_update)
    shear: bpy.props.FloatProperty(name="Shear", default=100.0, min=0.0, update=fabric_update)
    bend: bpy.props.FloatProperty(name="Bend", default=300.0, min=0.0, update=fabric_update)
    density: bpy.props.FloatProperty(
        name="Density", default=0.15, min=0.001, description="kg/m2", update=fabric_update
    )
    friction: bpy.props.FloatProperty(
        name="Friction", default=0.3, min=0.0, max=1.0, update=fabric_update
    )
    damping: bpy.props.FloatProperty(name="Damping", default=1.0, min=0.0, update=fabric_update)
    thickness: bpy.props.FloatProperty(
        name="Thickness",
        default=0.004,
        min=0.0,
        subtype="DISTANCE",
        description="Applied on Rebuild",
    )
    auto_fit: bpy.props.BoolProperty(
        name="Auto Fit",
        default=True,
        description="Fit the thickness to the modelled gap to the collider",
    )
    sewing: bpy.props.BoolProperty(
        name="Enable Sewing",
        description="Loose edges pull their vertices together (applied on Rebuild)",
    )
    follow: bpy.props.FloatProperty(
        name="Follow Body",
        description="During playback, pull toward the Armature shape: tight clothes stay put",
        default=0.2,
        min=0.0,
        max=1.0,
        subtype="FACTOR",
        update=fabric_update,
    )


def mode_update(self, context):
    """Interactive or Animation, one at a time"""
    animation = self.mode == "ANIMATION"
    if animation and STATE["running"]:
        STATE["stop"] = True
    if not animation and context.screen and context.screen.is_animation_playing:
        bpy.ops.screen.animation_cancel(restore_frame=False)


class MustardUI_ModelToolkit_ClothSceneSettings(bpy.types.PropertyGroup):
    mode: bpy.props.EnumProperty(
        name="Mode",
        items=[
            (
                "INTERACTIVE",
                "Interactive",
                "Edit the cloths live in the viewport: grab, push, smooth, pin",
                "HAND",
                0,
            ),
            (
                "ANIMATION",
                "Animation",
                "Simulate the cloths with the timeline on the animated body, cached and baked",
                "RENDER_ANIMATION",
                1,
            ),
        ],
        update=mode_update,
    )
    advanced: bpy.props.EnumProperty(
        name="Mode",
        items=[("SIMPLE", "Simple", "Presets only"), ("ADVANCED", "Advanced", "Every setting")],
    )
    quality: bpy.props.EnumProperty(
        name="Quality", items=preset_items(QUALITY), default="NORMAL", update=quality_update
    )
    substeps: bpy.props.IntProperty(
        name="Substeps", default=64, min=1, max=256, update=world_update
    )
    iterations: bpy.props.IntProperty(
        name="Iterations", default=6, min=1, max=16, update=world_update
    )
    gravity: bpy.props.FloatProperty(name="Gravity", default=1.0, update=world_update)
    debug: bpy.props.BoolProperty(
        name="Debug Info", description="Vertex counts, frame rate and step time", default=False
    )
    smooth_display: bpy.props.BoolProperty(
        name="Smooth Display",
        default=True,
        description="Interactive Mode shows the last frames blended: no flapping, a frame late",
        update=world_update,
    )
    air: bpy.props.FloatProperty(
        name="Air Drag",
        description="Drag across the cloth surface: calms flapping, but slows the whole cloth",
        default=0.0,
        min=0.0,
        soft_max=1000.0,
        update=world_update,
    )
    self_collision: bpy.props.BoolProperty(
        name="Self Collision",
        default=True,
        description="Also between the cloths",
        update=world_update,
    )
    untangle: bpy.props.BoolProperty(
        name="Untangle",
        default=True,
        description="Let layers that passed through each other (fast moves) back through",
        update=world_update,
    )
    self_radius: bpy.props.FloatProperty(
        name="Self Radius", default=0.003, min=0.0005, subtype="DISTANCE", update=world_update
    )
    sew_force: bpy.props.FloatProperty(
        name="Max Sewing Force",
        default=1.0,
        min=0.0,
        description="N per sewing edge",
        update=world_update,
    )
    brush: bpy.props.EnumProperty(
        name="Brush",
        items=[
            ("GRAB", "Grab", "Drag a vertex, or a range with E (key 1)", "VIEW_PAN", 0),
            (
                "PUSH",
                "Push",
                "Push the cloth away from the view, Ctrl pulls it (key 2)",
                "FORCE_FORCE",
                1,
            ),
            (
                "SMOOTH",
                "Smooth",
                "Relax wrinkles toward the neighbors' average (key 3)",
                "MOD_SMOOTH",
                2,
            ),
            ("PIN", "Pin", "Paint pins where the cloth is, Ctrl unpins (key 4)", "PINNED", 3),
            (
                "TACK",
                "Tack",
                "Pull and pin where released; drag a tack to move it, Ctrl+click removes it",
                "TRACKER",
                4,
            ),
        ],
    )
    brush_radius: bpy.props.FloatProperty(
        name="Brush Radius", default=0.05, min=0.001, subtype="DISTANCE"
    )
    brush_strength: bpy.props.FloatProperty(
        name="Strength", default=0.5, min=0.0, max=1.0, subtype="FACTOR"
    )


def cloth_objects(context):
    return [o for o in context.view_layer.objects if o.type == "MESH" and o.MustardUI_Cloth.enabled]


def build_world(context):
    """One solver for every enabled cloth; None when there is none"""
    if not solver.gpu_available():
        raise RuntimeError("Cloth Physics needs a GPU with compute shaders")
    solver.SIMS.clear()
    solver.WORLD["world"] = None
    objs = cloth_objects(context)
    if not objs:
        return None
    cloths = []
    for o in objs:
        st = o.MustardUI_Cloth
        cloths.append(
            solver.Cloth(context, o, st.pin_group, fabric_params(st), st.pin_target, st.sim_mesh)
        )
    colliders = {o.MustardUI_Cloth.collider for o in objs if o.MustardUI_Cloth.collider} - set(objs)
    world = solver.World(
        context, cloths, list(colliders), world_params(context.scene.MustardUI_ClothScene)
    )
    solver.SIMS.update({c.obj_name: c for c in cloths})
    solver.WORLD["world"] = world
    return world


def current_world(context):
    """The world of the enabled cloths, rebuilt when that set changed"""
    world = solver.WORLD["world"]
    if world is None or set(solver.SIMS) != {o.name for o in cloth_objects(context)}:
        world = build_world(context)
    return world


def guess_collider(obj):
    """The model body: MustardUI's, else a Body mesh on the armature, else the largest mesh"""
    arm = next((m.object for m in obj.modifiers if m.type == "ARMATURE" and m.object), None)
    if arm is None:
        return None
    body = getattr(getattr(arm.data, "MustardUI_RigSettings", None), "model_body", None)
    if body:
        return body
    meshes = [
        o
        for o in bpy.data.objects
        if o.type == "MESH"
        and o != obj
        and any(m.type == "ARMATURE" and m.object == arm for m in o.modifiers)
    ]
    named = [o for o in meshes if "body" in o.name.lower()]
    return max(named or meshes, key=lambda o: len(o.data.vertices), default=None)


def rebuild_report(op, context):
    try:
        build_world(context)
    except Exception as e:  # noqa: BLE001 - shader or mesh errors end up in the report
        op.report({"ERROR"}, f"MustardUI - {e}")
        return False
    return True


def active_cloth(context):
    obj = context.active_object
    return obj if obj and obj.type == "MESH" and obj.MustardUI_Cloth.enabled else None


def register():
    bpy.utils.register_class(MustardUI_ModelToolkit_ClothSettings)
    bpy.utils.register_class(MustardUI_ModelToolkit_ClothSceneSettings)
    bpy.types.Object.MustardUI_Cloth = bpy.props.PointerProperty(
        type=MustardUI_ModelToolkit_ClothSettings
    )
    bpy.types.Scene.MustardUI_ClothScene = bpy.props.PointerProperty(
        type=MustardUI_ModelToolkit_ClothSceneSettings
    )


def unregister():
    del bpy.types.Scene.MustardUI_ClothScene
    del bpy.types.Object.MustardUI_Cloth
    bpy.utils.unregister_class(MustardUI_ModelToolkit_ClothSceneSettings)
    bpy.utils.unregister_class(MustardUI_ModelToolkit_ClothSettings)
