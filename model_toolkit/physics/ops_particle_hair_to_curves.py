import math
import os

import bpy
import numpy as np
from mathutils.bvhtree import BVHTree

from ...model_selection.active_object import (
    ModelMode,
    active_object_operator_poll,
    mustardui_active_object,
)
from ...physics.definitions_nodes import (
    HAIR_CHILDREN_MODIFIER,
    HAIR_CHILDREN_SWITCH,
    HAIR_DYNAMICS_MUSTARDUI_SOCKETS,
    HAIR_DYNAMICS_NODE_GROUP,
    hair_dynamics_available,
    hair_dynamics_input,
)

# Curve attribute storing the index of the particle system of each guide
SYSTEM_ATTRIBUTE = "particle_system"
# Point attribute with the stiffness of the pin to the groom, from the particle hair dynamics
PIN_ATTRIBUTE = "pin"
# Curve attribute with the normal of the surface at the root of each guide
NORMAL_ATTRIBUTE = "surface_normal"

# Hair Dynamics inputs matching the particle hair dynamics of the same settings
HAIR_DYNAMICS_INPUTS = {
    "substeps": 20,
    "bendiness": 0.3,
    "linear_damping": 6.0,
    "angular_damping": 6.0,
}


def node_group(file, name):
    """Node group of the Blender essentials assets, appended if not in the file"""
    if name in bpy.data.node_groups:
        return bpy.data.node_groups[name]
    # Blender 4.x stores the assets in 'geometry_nodes', 5.x in 'nodes'
    for folder in ("nodes", "geometry_nodes"):
        path = os.path.join(bpy.utils.resource_path("LOCAL"), "datafiles", "assets", folder, file)
        if os.path.isfile(path):
            with bpy.data.libraries.load(path) as (source, target):
                target.node_groups = [name]
            return target.node_groups[0]
    return None


def add_surface_uv_map(mesh):
    """UV Map with each face in its own cell, as the hair is attached to the surface by UV"""
    count = len(mesh.polygons)
    cells = math.ceil(math.sqrt(count))
    starts, totals = np.empty(count, dtype=np.int32), np.empty(count, dtype=np.int32)
    mesh.polygons.foreach_get("loop_start", starts)
    mesh.polygons.foreach_get("loop_total", totals)
    face = np.repeat(np.arange(count), totals)
    corner = np.arange(totals.sum()) - np.repeat(np.cumsum(totals) - totals, totals)
    angle = 2 * np.pi * corner / totals[face]
    center = np.stack([face % cells, face // cells], axis=1) + 0.5
    uvs = np.empty((len(mesh.loops), 2), dtype=np.float32)
    uvs[np.repeat(starts, totals) + corner] = (
        center + 0.45 * np.stack([np.cos(angle), np.sin(angle)], axis=1)
    ) / cells
    mesh.uv_layers.new(name="Hair Surface").data.foreach_set("uv", uvs.ravel())


def resample(points, segment_length):
    """Points evenly spaced along the strand, at least 3, with the other columns interpolated"""
    lengths = np.linalg.norm(np.diff(points[:, :3], axis=0), axis=1)
    lengths = np.concatenate([[0], np.cumsum(lengths)])
    count = int(np.clip(round(lengths[-1] / segment_length) + 1, 3, max(len(points), 3)))
    samples = np.linspace(0, lengths[-1], count)
    return np.stack([np.interp(samples, lengths, x) for x in points.T], axis=1)


def hair_dynamics_node_group():
    """Hair Dynamics with the rest lengths in world space, and the hair pinned to its groom"""
    name = f"{HAIR_DYNAMICS_NODE_GROUP} (MustardUI)"
    if name in bpy.data.node_groups:
        return bpy.data.node_groups[name]
    ng = node_group("geometry_nodes_dynamics_assets.blend", HAIR_DYNAMICS_NODE_GROUP).copy()
    ng.name = name
    ng.asset_clear()
    nodes, links = ng.nodes, ng.links

    # The rest lengths are computed before moving the hair to world space, so the object
    # scale stretched the hair: compute them on the hair scaled as in world space
    rest = next(
        x
        for x in nodes
        if x.bl_idname == "GeometryNodeGroup"
        and x.node_tree.name.startswith("Setup Structural Rest Data")
    )
    scale = nodes.new("FunctionNodeSeparateTransform")
    links.new(nodes["Convert Simulation Space.003"].outputs["Transform"], scale.inputs[0])
    inverse = nodes.new("ShaderNodeVectorMath")
    inverse.operation = "DIVIDE"
    inverse.inputs[0].default_value = (1.0, 1.0, 1.0)
    links.new(scale.outputs["Scale"], inverse.inputs[1])
    to_world, back = nodes.new("GeometryNodeTransform"), nodes.new("GeometryNodeTransform")
    links.new(scale.outputs["Scale"], to_world.inputs["Scale"])
    links.new(inverse.outputs[0], back.inputs["Scale"])
    links.new(rest.inputs["Geometry"].links[0].from_socket, to_world.inputs["Geometry"])
    for link in list(rest.outputs["Geometry"].links):
        links.new(back.outputs["Geometry"], link.to_socket)
    links.new(to_world.outputs["Geometry"], rest.inputs["Geometry"])
    links.new(rest.outputs["Geometry"], back.inputs["Geometry"])

    # Simulation in the space of an object, so that moving it carries the simulated hair
    socket = ng.interface.new_socket(
        HAIR_DYNAMICS_MUSTARDUI_SOCKETS["simulation_space"],
        in_out="INPUT",
        socket_type="NodeSocketObject",
    )
    socket.description = "Object whose space the hair is simulated in (world space if empty)"
    solver = next(x for x in ng.interface.items_tree if x.name == "Solver")
    ng.interface.move_to_parent(socket, solver, len(solver.interface_items))
    space = nodes.new("GeometryNodeObjectInfo")
    space.transform_space = "ORIGINAL"
    links.new(nodes.new("NodeGroupInput").outputs[socket.identifier], space.inputs["Object"])
    to_world = nodes.new("FunctionNodeMatrixMultiply")
    links.new(space.outputs["Transform"], to_world.inputs[0])
    for output in [
        x.outputs["Simulation to World"]
        for x in nodes
        if x.bl_idname == "NodeGroupInput" and x.outputs["Simulation to World"].links
    ]:
        for link in list(output.links):
            links.new(to_world.outputs[0], link.to_socket)
        links.new(output, to_world.inputs[1])

    # Soft pin of the points to the groom, as the particle hair goal
    socket = ng.interface.new_socket(
        HAIR_DYNAMICS_MUSTARDUI_SOCKETS["pin_stiffness"],
        in_out="INPUT",
        socket_type="NodeSocketFloat",
    )
    socket.description = (
        f"Stiffness of the pin to the groom, multiplied by the '{PIN_ATTRIBUTE}' attribute"
    )
    socket.default_value = 30.0
    socket.min_value = 0.0
    structure = next(x for x in ng.interface.items_tree if x.name == "Structure")
    ng.interface.move_to_parent(socket, structure, len(structure.interface_items))
    pin = nodes.new("GeometryNodeInputNamedAttribute")
    pin.data_type = "FLOAT"
    pin.inputs["Name"].default_value = PIN_ATTRIBUTE
    pinned = nodes.new("FunctionNodeCompare")
    pinned.operation = "GREATER_THAN"
    links.new(pin.outputs["Attribute"], pinned.inputs["A"])
    stiffness = nodes.new("ShaderNodeMath")
    stiffness.operation = "MULTIPLY"
    links.new(pin.outputs["Attribute"], stiffness.inputs[0])
    links.new(nodes.new("NodeGroupInput").outputs[socket.identifier], stiffness.inputs[1])
    compliance = nodes.new("ShaderNodeMath")
    compliance.operation = "DIVIDE"
    compliance.inputs[0].default_value = 1.0
    links.new(stiffness.outputs[0], compliance.inputs[1])
    root_pin = nodes["Pin Positions"]
    goal = nodes.new("GeometryNodeGroup")
    goal.node_tree = root_pin.node_tree
    links.new(pinned.outputs["Result"], goal.inputs["Selection"])
    links.new(root_pin.inputs["Position"].links[0].from_socket, goal.inputs["Position"])
    links.new(compliance.outputs[0], goal.inputs["Compliance"])
    constraints = root_pin.outputs["Constraint"].links[0].to_node
    constraints.bundle_items.new("BUNDLE", "Pin Goal")
    links.new(goal.outputs["Constraint"], constraints.inputs["Pin Goal"])

    return ng


def simple_children_node_group():
    """Particle hair simple children: the guides are followed by children offset in a ball around
    their root, flattened on the surface by the roundness, and carried along the guide frame"""
    name = "Simple Hair Children (MustardUI)"
    if name in bpy.data.node_groups:
        return bpy.data.node_groups[name]
    ng = bpy.data.node_groups.new(name, "GeometryNodeTree")
    for socket_name, socket_type, props in (
        ("Geometry", "NodeSocketGeometry", {}),
        ("Amount", "NodeSocketInt", {"min_value": 0}),
        ("Viewport Amount", "NodeSocketInt", {"min_value": 0}),
        ("Radius", "NodeSocketFloat", {"min_value": 0.0, "subtype": "DISTANCE"}),
        ("Roundness", "NodeSocketFloat", {"min_value": 0.0, "max_value": 1.0, "subtype": "FACTOR"}),
        ("Clump", "NodeSocketFloat", {"min_value": -1.0, "max_value": 1.0, "subtype": "FACTOR"}),
        ("Clump Shape", "NodeSocketFloat", {"min_value": -1.0, "max_value": 1.0}),
        ("Keep Guides", "NodeSocketBool", {}),
        ("Seed", "NodeSocketInt", {}),
    ):
        socket = ng.interface.new_socket(socket_name, in_out="INPUT", socket_type=socket_type)
        for key, value in props.items():
            setattr(socket, key, value)
    ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    nodes, links = ng.nodes, ng.links
    group_input = nodes.new("NodeGroupInput").outputs

    def node(idname, *inputs, output=0, **props):
        new = nodes.new(idname)
        for key, value in props.items():
            setattr(new, key, value)
        for socket, value in zip([x for x in new.inputs if x.enabled], inputs, strict=False):
            if isinstance(value, bpy.types.NodeSocket):
                links.new(value, socket)
            elif value is not None:
                socket.default_value = value
        outputs = [x for x in new.outputs if x.enabled]
        return new.outputs[output] if isinstance(output, str) else outputs[output]

    def math(operation, *inputs):
        return node("ShaderNodeMath", *inputs, operation=operation)

    def vector(operation, *inputs, output=0):
        return node("ShaderNodeVectorMath", *inputs, output=output, operation=operation)

    def scale(vec, factor):
        new = nodes.new("ShaderNodeVectorMath")
        new.operation = "SCALE"
        links.new(vec, new.inputs[0])
        links.new(factor, new.inputs["Scale"])
        return new.outputs[0]

    # Each guide is the guide of itself and its children
    guides = node(
        "GeometryNodeStoreNamedAttribute",
        group_input["Geometry"],
        None,
        "guide",
        node("GeometryNodeInputIndex"),
        data_type="INT",
        domain="CURVE",
    )
    amount = node(
        "GeometryNodeSwitch",
        node("GeometryNodeIsViewport"),
        group_input["Amount"],
        group_input["Viewport Amount"],
        input_type="INT",
    )
    children = node("GeometryNodeDuplicateElements", guides, None, amount, domain="SPLINE")

    # Offset in a ball around the root, as the particle children
    random = nodes.new("FunctionNodeRandomValue")
    random.data_type = "FLOAT_VECTOR"
    links.new(node("GeometryNodeCurveOfPoint"), random.inputs["ID"])
    links.new(group_input["Seed"], random.inputs["Seed"])
    u = nodes.new("ShaderNodeSeparateXYZ")
    links.new(next(x for x in random.outputs if x.enabled), u.inputs[0])
    height = math("MULTIPLY_ADD", u.outputs[0], 2.0, -1.0)
    angle = math("MULTIPLY", u.outputs[1], 6.283185307)
    ring = math("SQRT", math("SUBTRACT", 1.0, math("MULTIPLY", height, height)))
    radius = math("MULTIPLY", group_input["Radius"], math("POWER", u.outputs[2], 1 / 3))
    x = math("MULTIPLY", radius, math("MULTIPLY", ring, math("COSINE", angle)))
    y = math("MULTIPLY", radius, math("MULTIPLY", ring, math("SINE", angle)))
    z = math("MULTIPLY", radius, math("MULTIPLY", height, group_input["Roundness"]))

    # Root frame of the guide
    root = node("GeometryNodeCurveOfPoint")
    root = node("GeometryNodePointsOfCurve", root)

    def at_root(field):
        at = nodes.new("GeometryNodeFieldAtIndex")
        at.data_type = "FLOAT_VECTOR"
        links.new(root, at.inputs["Index"])
        links.new(field, next(x for x in at.inputs if x.enabled and x.name == "Value"))
        return next(x for x in at.outputs if x.enabled)

    tangent, normal = node("GeometryNodeInputTangent"), node("GeometryNodeInputNormal")
    tangent_root, normal_root = at_root(tangent), at_root(normal)
    binormal_root = vector("CROSS_PRODUCT", tangent_root, normal_root)
    surface = node("GeometryNodeInputNamedAttribute", NORMAL_ATTRIBUTE, data_type="FLOAT_VECTOR")
    # Any basis of the tangent plane, as the angle on it is random
    parallel = node(
        "FunctionNodeCompare",
        math("ABSOLUTE", node("ShaderNodeSeparateXYZ", surface)),
        0.9,
        data_type="FLOAT",
        operation="GREATER_THAN",
    )
    axis = node(
        "GeometryNodeSwitch", parallel, (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), input_type="VECTOR"
    )
    side_a = vector("NORMALIZE", vector("CROSS_PRODUCT", surface, axis))
    side_b = vector("CROSS_PRODUCT", surface, side_a)
    offset = vector(
        "ADD",
        vector("ADD", scale(side_a, x), scale(side_b, y)),
        scale(surface, z),
    )

    # The offset turns with the guide along the strand
    binormal = vector("CROSS_PRODUCT", tangent, normal)
    offset = vector(
        "ADD",
        vector(
            "ADD",
            scale(tangent, vector("DOT_PRODUCT", offset, tangent_root, output="Value")),
            scale(normal, vector("DOT_PRODUCT", offset, normal_root, output="Value")),
        ),
        scale(binormal, vector("DOT_PRODUCT", offset, binormal_root, output="Value")),
    )
    children = node("GeometryNodeSetPosition", children, None, None, offset)

    # Clump towards the guides, which are first in the joined geometry
    join = nodes.new("GeometryNodeJoinGeometry")
    links.new(children, join.inputs[0])
    links.new(guides, join.inputs[0])
    clump = nodes.new("GeometryNodeGroup")
    clump.node_tree = node_group("procedural_hair_node_assets.blend", "Clump Hair Curves")
    links.new(join.outputs[0], clump.inputs["Geometry"])
    links.new(group_input["Clump"], clump.inputs["Factor"])
    links.new(group_input["Clump Shape"], clump.inputs["Shape"])
    guide = node("GeometryNodeInputNamedAttribute", "guide", data_type="INT")
    links.new(guide, clump.inputs["Guide Index"])

    count = node("GeometryNodeAttributeDomainSize", group_input["Geometry"], component="CURVE")
    is_guide = node(
        "FunctionNodeCompare",
        node("GeometryNodeInputIndex"),
        count.node.outputs["Spline Count"],
        data_type="INT",
        operation="LESS_THAN",
    )
    remove = node(
        "FunctionNodeBooleanMath", is_guide, group_input["Keep Guides"], operation="NIMPLY"
    )
    result = node("GeometryNodeDeleteGeometry", clump.outputs["Geometry"], remove, domain="CURVE")
    links.new(result, nodes.new("NodeGroupOutput").inputs[0])
    return ng


def hair_children_node_group(name, emitter, systems):
    """Children, clump, strand profile and material of each particle system, with the
    children settings as inputs, in a panel per particle system if more than one"""
    ng = bpy.data.node_groups.new(name, "GeometryNodeTree")
    ng.is_modifier = True
    interface = ng.interface
    interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    with_children = [x for x in systems if x.settings.child_type != "NONE"]
    if with_children:
        interface.new_socket(
            HAIR_CHILDREN_SWITCH, in_out="INPUT", socket_type="NodeSocketBool"
        ).default_value = True
    nodes, links = ng.nodes, ng.links
    group_input = nodes.new("NodeGroupInput")
    join = nodes.new("GeometryNodeJoinGeometry")
    links.new(join.outputs[0], nodes.new("NodeGroupOutput").inputs[0])
    system = nodes.new("GeometryNodeInputNamedAttribute")
    system.data_type = "INT"
    system.inputs["Name"].default_value = SYSTEM_ATTRIBUTE
    scale = sum(emitter.matrix_world.to_scale()) / 3

    for index, particle_system in enumerate(systems):
        settings = particle_system.settings
        compare = nodes.new("FunctionNodeCompare")
        compare.data_type = "INT"
        compare.operation = "EQUAL"
        links.new(system.outputs["Attribute"], compare.inputs["A"])
        compare.inputs["B"].default_value = index
        separate = nodes.new("GeometryNodeSeparateGeometry")
        separate.domain = "CURVE"
        links.new(group_input.outputs[0], separate.inputs["Geometry"])
        links.new(compare.outputs["Result"], separate.inputs["Selection"])
        geometry = separate.outputs["Selection"]

        if settings.child_type != "NONE":
            # Particle clump is factor * t^power, the assets use t^(shape / (1 - shape))
            power = 1 + settings.clump_shape * (1 if settings.clump_shape < 0 else 9)
            # Children radius does not follow the object scale, while the curves do
            children = nodes.new("GeometryNodeGroup")
            children.node_tree = simple_children_node_group()
            children.inputs["Seed"].default_value = index
            links.new(geometry, children.inputs["Geometry"])
            panel = interface.new_panel(particle_system.name) if len(with_children) > 1 else None
            # The settings are inputs of the modifier
            for key, value in {
                "Amount": settings.rendered_child_count,
                "Viewport Amount": settings.child_percent,
                "Radius": settings.child_radius / scale,
                "Roundness": settings.child_roundness,
                "Clump": settings.clump_factor,
                "Clump Shape": power / (1 + power),
                "Keep Guides": settings.use_parent_particles,
            }.items():
                item = children.node_tree.interface.items_tree[key]
                socket = interface.new_socket(
                    key, in_out="INPUT", socket_type=item.socket_type, parent=panel
                )
                for prop in ("subtype", "min_value", "max_value"):
                    if hasattr(item, prop):
                        setattr(socket, prop, getattr(item, prop))
                socket.default_value = value
                links.new(group_input.outputs[socket.identifier], children.inputs[key])

            switch = nodes.new("GeometryNodeSwitch")
            switch.input_type = "GEOMETRY"
            links.new(group_input.outputs[HAIR_CHILDREN_SWITCH], switch.inputs["Switch"])
            links.new(geometry, switch.inputs["False"])
            links.new(children.outputs["Geometry"], switch.inputs["True"])
            geometry = switch.outputs[0]

        profile = nodes.new("GeometryNodeGroup")
        profile.node_tree = node_group(
            "procedural_hair_node_assets.blend", "Set Hair Curve Profile"
        )
        profile.inputs["Radius"].default_value = 0.5 * settings.radius_scale * settings.root_radius
        profile.inputs["Factor Min"].default_value = settings.tip_radius / max(
            settings.root_radius, 1e-6
        )
        links.new(geometry, profile.inputs["Geometry"])
        geometry = profile.outputs["Geometry"]

        if 0 < settings.material <= len(emitter.material_slots):
            material = nodes.new("GeometryNodeSetMaterial")
            material.inputs["Material"].default_value = emitter.material_slots[
                settings.material - 1
            ].material
            links.new(geometry, material.inputs["Geometry"])
            geometry = material.outputs["Geometry"]

        links.new(geometry, join.inputs[0])

    return ng


def add_collider(obj):
    """Deforming collider for the Hair Dynamics"""
    if "Hair Collider" in obj.modifiers:
        return
    group = node_group("geometry_nodes_dynamics_assets.blend", "Collider")
    mod = obj.modifiers.new("Hair Collider", "NODES")
    mod.node_group = group
    deforming = next(x for x in group.interface.items_tree if x.name == "Deforming")
    getattr(mod.properties.inputs, deforming.identifier).value = True
    # Enabled with the collision cage physics
    mod.show_viewport = mod.show_render = any(
        m.type == "COLLISION" and m.show_viewport for m in obj.modifiers
    )


class MustardUI_ModelToolkit_ParticleHairToCurves(bpy.types.Operator):
    bl_idname = "mustardui.model_toolkit_particle_hair_to_curves"
    bl_label = "Convert Particle Hair to Curves"
    bl_description = (
        "Convert the particle hair of the selected Hair objects to Hair Curves, with "
        "children and Hair Dynamics.\nThe guides are resampled so that the simulation is stable"
    )
    bl_options = {"REGISTER", "UNDO"}

    segment_length: bpy.props.FloatProperty(
        name="Segment Length",
        description="Length of the segments of the resampled guides.\nShorter segments "
        "keep more detail, but need more Substeps to avoid stretching",
        default=0.04,
        min=0.001,
        soft_max=0.1,
        subtype="DISTANCE",
    )
    physics: bpy.props.BoolProperty(
        name="Hair Dynamics",
        description="Add the Hair Dynamics simulation, colliding with the model collision "
        "cages.\nAvailable from Blender 5.2",
        default=True,
    )

    @classmethod
    def poll(cls, context):
        return active_object_operator_poll(context, config=ModelMode.MODEL_TOOLKIT)

    def execute(self, context):
        res, arm = mustardui_active_object(context, config=ModelMode.MODEL_TOOLKIT)
        rig_settings = arm.MustardUI_RigSettings
        hair_collection = rig_settings.hair_collection

        emitters = [
            x
            for x in context.selected_objects
            if hair_collection
            and x.name in hair_collection.objects
            and any(p.settings.type == "HAIR" for p in x.particle_systems)
        ]
        if not emitters:
            self.report(
                {"WARNING"}, "MustardUI - Select Hair objects of the model with particle hair."
            )
            return {"CANCELLED"}

        # Collision cages collide with the hair
        physics = self.physics and hair_dynamics_available()
        cages = [
            x.object
            for x in arm.MustardUI_PhysicsSettings.items
            if x.type == "COLLISION" and x.object
        ]
        colliders = None
        if physics and cages:
            name = f"{rig_settings.model_name} Hair Colliders".strip()
            colliders = bpy.data.collections.get(name) or bpy.data.collections.new(name)
            # In the collection of the cages, to be found in the Outliner
            if colliders not in context.scene.collection.children_recursive:
                parent = next(
                    (x for x in cages[0].users_collection if x != colliders),
                    context.scene.collection,
                )
                parent.children.link(colliders)
            for cage in cages:
                add_collider(cage)
                if cage.name not in colliders.objects:
                    colliders.objects.link(cage)

        surfaces = hair_collection.children.get(f"{hair_collection.name} Surfaces")
        if surfaces is None:
            surfaces = bpy.data.collections.new(f"{hair_collection.name} Surfaces")
            hair_collection.children.link(surfaces)
            surfaces.hide_viewport = True
            surfaces.hide_render = True

        converted = 0
        for emitter in emitters:
            if not emitter.data.uv_layers:
                add_surface_uv_map(emitter.data)

            # The hair keys are available on the evaluated emitter only
            hidden = emitter.hide_viewport, hair_collection.hide_viewport
            emitter.hide_viewport = hair_collection.hide_viewport = False
            mods = [x for x in emitter.modifiers if x.type == "PARTICLE_SYSTEM"]
            mods = [x for x in mods if x.particle_system.settings.type == "HAIR"]
            for mod in mods:
                mod.show_viewport = True
            depsgraph = context.evaluated_depsgraph_get()
            evaluated = emitter.evaluated_get(depsgraph)

            # Strands of positions and pin stiffness of the keys, and surface normals at the roots
            bvh = BVHTree.FromObject(evaluated, depsgraph)
            strands, uvs, normals, systems = [], [], [], []
            for index, mod in enumerate(mods):
                mod_eval = evaluated.modifiers[mod.name]
                cloth = mod_eval.particle_system.cloth
                pin = cloth.settings.pin_stiffness if cloth else 1.0
                for particle in mod_eval.particle_system.particles:
                    points = np.array(
                        [
                            (*k.co_object(evaluated, mod_eval, particle), pin * k.weight)
                            for k in particle.hair_keys
                        ]
                    )
                    strands.append(resample(points, self.segment_length))
                    uvs.append(particle.uv_on_emitter(mod_eval))
                    normals.append(bvh.find_nearest(points[0, :3])[1])
                    systems.append(index)

            emitter.hide_viewport, hair_collection.hide_viewport = hidden
            if not strands:
                self.report({"WARNING"}, f"MustardUI - {emitter.name} has no hair, skipped.")
                continue
            for mod in mods:
                mod.show_viewport = mod.show_render = False

            name = emitter.name
            emitter.name = f"{name} Surface"
            curves = bpy.data.hair_curves.new(name)
            curves.add_curves([len(x) for x in strands])
            strands = np.concatenate(strands)
            curves.position_data.foreach_set("vector", strands[:, :3].ravel())
            curves.attributes.new(PIN_ATTRIBUTE, "FLOAT", "POINT").data.foreach_set(
                "value", strands[:, 3]
            )
            curves.surface = emitter
            curves.surface_uv_map = emitter.data.uv_layers.active.name
            curves.attributes.new("surface_uv_coordinate", "FLOAT2", "CURVE").data.foreach_set(
                "vector", np.array(uvs).ravel()
            )
            curves.attributes.new(NORMAL_ATTRIBUTE, "FLOAT_VECTOR", "CURVE").data.foreach_set(
                "vector", np.array(normals).ravel()
            )
            curves.attributes.new(SYSTEM_ATTRIBUTE, "INT", "CURVE").data.foreach_set(
                "value", systems
            )
            for slot in emitter.material_slots:
                if slot.material and slot.material.name not in curves.materials:
                    curves.materials.append(slot.material)

            obj = bpy.data.objects.new(name, curves)
            hair_collection.objects.link(obj)
            obj.parent = emitter
            obj.hide_viewport, obj.hide_render = emitter.hide_viewport, emitter.hide_render

            # The emitter is the surface the hair is attached to
            for coll in list(emitter.users_collection):
                coll.objects.unlink(emitter)
            surfaces.objects.link(emitter)
            emitter.add_rest_position_attribute = True

            if physics:
                dynamics = obj.modifiers.new(HAIR_DYNAMICS_NODE_GROUP, "NODES")
                group = hair_dynamics_node_group()
                dynamics.node_group = group
                mode = next(x for x in group.interface.items_tree if x.name == "Mode")
                getattr(
                    dynamics.properties.inputs, mode.identifier
                ).value = "Physics (Experimental)"
                for key, value in {
                    **HAIR_DYNAMICS_INPUTS,
                    "effectors_collection": colliders,
                    "simulation_space": rig_settings.model_armature_object,
                }.items():
                    hair_dynamics_input(dynamics, key).value = value

                # The MustardUI physics switch of the hair
                obj.MustardUI_OutfitSettings.physics = True

            children = obj.modifiers.new(HAIR_CHILDREN_MODIFIER, "NODES")
            children.node_group = hair_children_node_group(
                f"{name} Children", emitter, [m.particle_system for m in mods]
            )
            converted += 1

        if not converted:
            return {"CANCELLED"}
        self.report({"INFO"}, f"MustardUI - {converted} particle hair converted to curves.")
        return {"FINISHED"}

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "segment_length")
        row = layout.row()
        row.enabled = hair_dynamics_available()
        row.prop(self, "physics")

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=300)


def register():
    bpy.utils.register_class(MustardUI_ModelToolkit_ParticleHairToCurves)


def unregister():
    bpy.utils.unregister_class(MustardUI_ModelToolkit_ParticleHairToCurves)
