import bmesh
import bpy
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree
from rna_prop_ui import rna_idprop_ui_create

from .. import __package__ as base_package
from ..model_selection.active_object import mustardui_active_object
from . import physics_presets


class MustardUI_ToolsCreators_CreateJiggleAccurate(bpy.types.Operator):
    """Needs to select vertices in Edit Mode.\nCreates a simplified cage from the selected vertices and binds the selection to it, so that the cage can drive the Physics of that specific part of the mesh"""  # noqa: E501

    bl_idname = "mustardui.tools_creators_create_jiggle_accurate"
    bl_label = "Create Jiggle Cage (High-resolution)"
    bl_options = {"REGISTER", "UNDO", "PRESET"}

    cage_type: bpy.props.EnumProperty(
        name="Cage Type",
        description="Type of cage generated from the selection",
        items=[
            (
                "CLOSED",
                "Closed",
                "Simplify the surface of the selection and close its border, to "
                "obtain a single closed cage.\nBest for volume parts (breasts, "
                "belly, hair clumps, ears)",
                "MESH_UVSPHERE",
                0,
            ),
            (
                "OPEN",
                "Open",
                "Simplify the surface of the selection, leaving its border open.\n"
                "Best for cloth-like parts (skirts, capes, sleeves, long hair)",
                "OUTLINER_OB_SURFACE",
                1,
            ),
        ],
        default="CLOSED",
    )

    merge_cages: bpy.props.BoolProperty(
        name="Merge Cages",
        description="Generate a single cage from the whole selection, even when it is "
        "made of several disconnected vertex islands.\nWhen disabled, each island gets "
        "its own cage, with its own Pin group and its own Physics",
        default=False,
    )

    cage_faces: bpy.props.IntProperty(
        name="Cage Faces",
        description="Number of faces of the generated cage.\nNote: This is a target, and "
        "not an exact count.\nWhen the selection is made of several islands, this is the "
        "target of each one of them",
        default=500,
        min=20,
        soft_max=2000,
        max=20000,
    )
    relax_iterations: bpy.props.IntProperty(
        name="Relax Iterations",
        description="Number of relax iterations applied to the cage.\nEach "
        "iteration evens out the triangles and projects them back on the mesh: this "
        "cleans up the irregular topology left by the simplification, without "
        "changing the shape of the cage",
        default=20,
        min=0,
        max=50,
    )
    cage_offset: bpy.props.FloatProperty(
        name="Offset",
        description="Distance kept between the cage and the original mesh",
        default=0.005,
        min=0.0,
        soft_max=0.1,
        step=1,
        precision=4,
        subtype="DISTANCE",
        unit="LENGTH",
    )

    physics_engine: physics_presets.physics_engine_property()
    cloth_preset: physics_presets.cloth_preset_property(default="CAGE")
    nodes_preset: physics_presets.nodes_preset_property(default="CAGE")

    structural_enable: bpy.props.BoolProperty(
        name="Structural Stiffness",
        description="Stiffen the cage where the model is dense, so that the "
        "detailed parts are carried around rigidly instead of being stretched.\n"
        "When disabled the cage uses the same stiffness everywhere",
        default=False,
    )
    structural_stiffness: bpy.props.FloatProperty(
        name="Stiffness",
        description="How much the cage resists being stretched where the model is "
        "dense.\nCan be useful when some parts are extruding from the main mesh "
        "(for instance the tip of a breast)",
        default=1.0,
        min=0.0,
        max=1.0,
        step=3,
        precision=3,
    )

    structural_spread: bpy.props.IntProperty(
        name="Spread",
        description="How concentrated the structural stiffness is on the dense "
        "areas of the model.\nWith a low value the stiffness stays on the detailed "
        "parts and drops to zero right after them; with a high one it fades out "
        "slowly and reaches the rest of the cage, up to stiffening it uniformly",
        default=2,
        min=0,
        max=20,
    )

    # Common settings
    falloff_rings: bpy.props.IntProperty(
        name="Pin Falloff Rings",
        description="Number of vertex rings of the cage used to fade the Pin group "
        "from the border towards the inside.\nWith 0, only the border of the cage "
        "is pinned, and the rest of it is free to move",
        default=3,
        min=0,
        max=20,
    )
    add_to_panel: bpy.props.BoolProperty(
        name="Add to Physics Panel",
        description="Add the Cage item to Physics Panel",
        default=True,
    )
    parent_to_model: bpy.props.BoolProperty(
        name="Parent to Model",
        description="Parent the cage to the Model Armature",
        default=False,
    )
    name: bpy.props.StringProperty(
        name="Cage Name",
        description="Assign a name to the Cage and the associated modifiers",
        default="",
    )

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=1)
        return (
            res
            and context.active_object is not None
            and context.active_object.type == "MESH"
            and context.mode == "EDIT_MESH"
        )

    def execute(self, context):

        res, arm = mustardui_active_object(context, config=1)
        rig_settings = arm.MustardUI_RigSettings
        physics_settings = arm.MustardUI_PhysicsSettings
        addon_prefs = context.preferences.addons[base_package].preferences

        source = context.active_object

        # Read the selection in Object Mode, as the Edit Mode selection is not
        # flushed to the mesh data until the mode is toggled
        bpy.ops.object.mode_set(mode="OBJECT")

        selected_indices = {v.index for v in source.data.vertices if v.select}
        if not selected_indices:
            bpy.ops.object.mode_set(mode="EDIT")
            self.report({"ERROR"}, "MustardUI - No vertex selected.")
            return {"CANCELLED"}

        base_name = self.name if self.name != "" else f"{source.name} Cage"

        # Store the Armature pose states, and switch all of them to rest position.
        # Cages are generated, and bound, on the rest shape of the model
        stored_pose_states = {}
        for obj in context.scene.objects:
            if obj.type == "ARMATURE":
                stored_pose_states[obj.name] = obj.data.pose_position
                obj.data.pose_position = "REST"
        context.view_layer.update()

        # ------------------------------------------------------------------
        # Islands and borders of the selection
        # ------------------------------------------------------------------

        # Neighbours of every selected vertex, inside the whole mesh: the ones
        # falling outside of the selection are what makes a border
        neighbors = {i: set() for i in selected_indices}
        for edge in source.data.edges:
            a, b = edge.vertices
            if a in selected_indices:
                neighbors[a].add(b)
            if b in selected_indices:
                neighbors[b].add(a)

        def selection_islands():
            """The connected parts of the selection.

            Each one gets a cage of its own: a selection covering two breasts, or a
            dozen hair clumps, is not a single soft body, and a single cage would
            tie parts which have nothing to do with each other to the same
            simulation, on top of splitting the face budget among them.
            """
            if self.merge_cages:
                return [set(selected_indices)]

            islands = []
            visited = set()
            # Walked in a sorted order, so that the islands (and the names built out
            # of their position) do not depend on how the set is laid out in memory
            for start in sorted(selected_indices):
                if start in visited:
                    continue
                island = set()
                stack = [start]
                while stack:
                    current = stack.pop()
                    if current in visited:
                        continue
                    visited.add(current)
                    island.add(current)
                    stack.extend(
                        n for n in neighbors[current] if n in selected_indices and n not in visited
                    )
                islands.append(island)

            return islands

        def selection_border(island):
            """The vertices of an island which touch the rest of the mesh."""
            return {i for i in island if any(n not in island for n in neighbors[i])}

        # ------------------------------------------------------------------
        # Cage generation
        # ------------------------------------------------------------------

        def generate_unique_name(name):
            unique_name = name
            count = 1
            while bpy.data.objects.get(unique_name) is not None:
                unique_name = f"{name}.{str(count).zfill(3)}"
                count += 1
            return unique_name

        def isolate_selection(obj, island):
            """Delete everything which does not belong to the island on the copy.

            The deletion is done with bmesh, and not by selecting the vertices and
            calling the delete operator: entering Edit Mode flushes the selection of
            the faces of the mesh down to their vertices, which would select back
            the whole mesh.
            """
            bm = bmesh.new()
            bm.from_mesh(obj.data)
            bm.verts.ensure_lookup_table()

            unselected = [v for v in bm.verts if v.index not in island]
            bmesh.ops.delete(bm, geom=unselected, context="VERTS")

            # Vertices and edges left without any face (a selection is rarely made
            # of faces only) would make the cage invalid for the Surface Deform
            loose = [v for v in bm.verts if not v.link_faces]
            if loose:
                bmesh.ops.delete(bm, geom=loose, context="VERTS")

            bm.to_mesh(obj.data)
            bm.free()
            obj.data.update()

            # Hidden geometry is deleted as well, but what is left has to be shown
            for vert in obj.data.vertices:
                vert.hide = False
            for edge in obj.data.edges:
                edge.hide = False
            for polygon in obj.data.polygons:
                polygon.hide = False

        def clean_topology(bm):
            """Make the cage a clean surface: no extra faces, no loose geometry.

            The Surface Deform refuses the whole target as soon as a single edge has
            more than two faces ('Target has edges with more than two polygons').
            Filling a border which pinches on itself, and dissolving degenerate
            geometry, can both produce them. The smallest faces are dropped, so what
            is removed is the overlapping sliver and not the surface of the cage.

            The collapses also leave wire edges and stray vertices behind. They are
            invisible on the cage but they keep it from ever being reported as
            closed, and the simulation has no use for them.
            """
            extra = set()
            for edge in bm.edges:
                faces = [f for f in edge.link_faces if f not in extra]
                if len(faces) > 2:
                    faces.sort(key=lambda f: f.calc_area())
                    extra.update(faces[: len(faces) - 2])

            if extra:
                bmesh.ops.delete(bm, geom=list(extra), context="FACES_ONLY")

            wire = [e for e in bm.edges if not e.link_faces]
            if wire:
                bmesh.ops.delete(bm, geom=wire, context="EDGES")

            stray = [v for v in bm.verts if not v.link_faces]
            if stray:
                bmesh.ops.delete(bm, geom=stray, context="VERTS")

            return bool(extra)

        def triangulate(obj):
            """Triangulate the whole cage.

            The Surface Deform modifier refuses to bind on a target containing
            concave polygons, and it reads a quad which is concave *or* simply too
            non planar as such. Both are produced in quantity by the simplification
            of a dense, irregular mesh, and splitting only the concave faces is not
            enough. Triangles are always convex and always planar, so this removes
            the problem at the root. The simulation is not affected: the cloth
            solver triangulates the mesh internally anyway.
            """
            bm = bmesh.new()
            bm.from_mesh(obj.data)

            # Near degenerate faces are reported as invalid by the Surface Deform:
            # the edges too short to matter are dissolved away first
            lengths = sorted(e.calc_length() for e in bm.edges)
            if lengths:
                bmesh.ops.dissolve_degenerate(
                    bm, dist=lengths[len(lengths) // 2] * 0.05, edges=bm.edges[:]
                )

            bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method="BEAUTY", ngon_method="BEAUTY")

            # Flip the diagonals which give the worst looking triangles. This only
            # rewires the mesh, so the shape of the cage is left untouched
            bmesh.ops.beautify_fill(bm, faces=bm.faces[:], edges=bm.edges[:])
            clean_topology(bm)

            bm.to_mesh(obj.data)
            bm.free()
            obj.data.update()

        def simplify_border(bm):
            """Bring the border loops down to the density of the rest of the cage.

            The un-subdivision simplifies the inside of the cage but leaves the
            border loops untouched. Closing a border which is still as dense as the
            original mesh gives a fan of hundreds of sliver triangles, which the
            Surface Deform refuses to bind and the simulation handles badly.
            """
            interior = [e.calc_length() for e in bm.edges if len(e.link_faces) > 1]
            if not interior:
                return
            interior.sort()
            target = interior[len(interior) // 2]

            # Collapsing changes the border, so the shortest edges are collapsed a
            # few times over instead of all at once
            for _ in range(12):
                short = [
                    e
                    for e in bm.edges
                    if len(e.link_faces) == 1 and e.calc_length() < target * 0.75
                ]
                if not short:
                    break
                bmesh.ops.collapse(bm, edges=short, uvs=False)
                bmesh.ops.dissolve_degenerate(bm, dist=1e-6, edges=bm.edges[:])

        def finalize_border(obj, border_positions):
            """Simplify the border of the cage, record it, and close it if needed.

            bmesh is used instead of the fill_holes operator: the latter works on
            the selection, and on a ragged border it both leaves holes open and
            creates edges shared by three faces, which the Surface Deform rejects.
            """
            bm = bmesh.new()
            bm.from_mesh(obj.data)

            simplify_border(bm)

            # The border is where the cage is attached to the rest of the model, and
            # it is recorded here, once it is not going to move any more, to build
            # the Pin group out of it further down
            border_positions.extend(
                v.co.copy()
                for v in {v for e in bm.edges if len(e.link_faces) == 1 for v in e.verts}
            )

            if self.cage_type == "CLOSED":
                # Filling can leave holes behind and can make faces overlap, so it
                # is repeated until the cage is closed and manifold
                for _ in range(6):
                    # Repairing deletes faces, which can open the cage again, so the
                    # repair and the filling are repeated until both are satisfied
                    repaired = clean_topology(bm)

                    # 'sides=0' fills the border loops whatever their edge count
                    border = [e for e in bm.edges if len(e.link_faces) == 1]
                    if not border and not repaired:
                        break
                    if not border:
                        continue

                    filled = bmesh.ops.holes_fill(bm, edges=border, sides=0)
                    new_faces = list(filled.get("faces", []))

                    # holes_fill only handles borders which are simple closed loops,
                    # and gives up on the ones pinching on themselves, which the
                    # simplification of a ragged border easily produces. Whatever it
                    # left open is filled as a generic net of edges instead
                    border = [e for e in bm.edges if len(e.link_faces) == 1]
                    if border:
                        net = bmesh.ops.triangle_fill(
                            bm, use_beauty=True, use_dissolve=False, edges=border
                        )
                        new_faces.extend(
                            g for g in net.get("geom", []) if isinstance(g, bmesh.types.BMFace)
                        )

                    if not new_faces:
                        break

                    # Each hole is filled with a single n-gon. It is triangulated
                    # with 'BEAUTY', and not poked, because poking fans every border
                    # vertex to a single centre, which on a wide border gives slivers
                    triangulated = bmesh.ops.triangulate(
                        bm,
                        faces=new_faces,
                        quad_method="BEAUTY",
                        ngon_method="BEAUTY",
                    )
                    # The border loops are rarely flat, and triangulating a loop
                    # which is not flat leaves thin triangles behind: the fill is
                    # rewired to use the best looking triangles it can
                    tri_faces = triangulated.get("faces", [])
                    if tri_faces:
                        bmesh.ops.beautify_fill(
                            bm,
                            faces=tri_faces,
                            edges=list({e for f in tri_faces for e in f.edges}),
                        )

            if self.cage_type != "CLOSED":
                clean_topology(bm)

            bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])

            bm.to_mesh(obj.data)
            bm.free()
            obj.data.update()

        def relax(obj):
            """Even out the triangles of the cage, keeping it on the original mesh.

            The collapse decimation keeps the detail where the mesh curves the most,
            so the cage it returns has triangles of very different sizes and shapes.
            Each iteration here relaxes the vertices towards the centre of their
            neighbours, rewires the triangles which can be improved, and projects
            everything back on the mesh so that the shape of the cage is preserved.
            """
            if self.relax_iterations <= 0:
                return

            bvh = BVHTree.FromObject(source, context.evaluated_depsgraph_get())

            bm = bmesh.new()
            bm.from_mesh(obj.data)

            # The border is left alone: relaxing it would shrink the outline of the
            # cage away from the selection it has to cover
            interior = [v for v in bm.verts if all(len(e.link_faces) > 1 for e in v.link_edges)]
            if not interior:
                bm.free()
                return

            for _ in range(self.relax_iterations):
                bmesh.ops.smooth_vert(
                    bm,
                    verts=interior,
                    factor=0.5,
                    use_axis_x=True,
                    use_axis_y=True,
                    use_axis_z=True,
                )
                bmesh.ops.beautify_fill(bm, faces=bm.faces[:], edges=bm.edges[:])
                for vert in interior:
                    location = bvh.find_nearest(vert.co)[0]
                    if location is not None:
                        vert.co = location

            bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
            bm.to_mesh(obj.data)
            bm.free()
            obj.data.update()

        def create_cage(island, cage_name, border_positions):
            bpy.ops.object.select_all(action="DESELECT")
            source.select_set(True)
            context.view_layer.objects.active = source
            bpy.ops.object.duplicate(linked=False)

            cage = context.active_object
            cage.name = generate_unique_name(cage_name)
            cage.data.name = cage.name

            # Shape Keys and modifiers of the source mesh would prevent the
            # generation modifiers from being applied
            cage.shape_key_clear()
            cage.modifiers.clear()
            cage.data.materials.clear()
            cage.vertex_groups.clear()

            isolate_selection(cage, island)

            # Returned as it is: the caller takes care of removing empty cages
            if not cage.data.vertices:
                return cage

            # The cage is the surface of the selection itself, simplified. No
            # solidification and no re-meshing are used: they would produce a cage
            # made of two layers, and one detached from the shape of the selection.
            #
            # The simplification is a collapse decimation and not an un-subdivision:
            # un-subdivide reverses a Catmull-Clark subdivision, so it only behaves
            # on a regular quad grid. On the dense and irregular topology of a real
            # model it leaves large tangled polygons in the middle of the cage.
            # The ratio is derived from the face count of the selection, so that the
            # result does not depend on how dense the model is
            face_count = len(cage.data.polygons)
            if face_count > self.cage_faces:
                decimate = cage.modifiers.new(name="Decimate", type="DECIMATE")
                decimate.decimate_type = "COLLAPSE"
                decimate.ratio = self.cage_faces / face_count
                decimate.use_collapse_triangulate = True

            bpy.ops.object.convert(target="MESH")

            # Triangulated before relaxing: the relax rewires triangles, and it can
            # only do so on a mesh which is made of triangles in the first place
            triangulate(cage)
            relax(cage)

            # Place every vertex of the cage at Offset distance from the mesh. The
            # relax already put them on it, this lifts the whole cage off the
            # surface: the Surface Deform cannot bind on a target which touches the
            # vertices it has to deform, and a cage lying on the body intersects it.
            # 'OUTSIDE_SURFACE' and not 'ABOVE_SURFACE': the cage is built from the
            # outer surface of the selection, so the side to keep it on is known.
            # 'ABOVE_SURFACE' has to guess that side, and on the vertices which are
            # exactly on the mesh it can guess differently for two neighbours,
            # producing flipped faces the Surface Deform rejects
            shrinkwrap = cage.modifiers.new(name="Shrinkwrap", type="SHRINKWRAP")
            shrinkwrap.target = source
            shrinkwrap.wrap_method = "NEAREST_SURFACEPOINT"
            shrinkwrap.wrap_mode = "OUTSIDE_SURFACE"
            shrinkwrap.offset = self.cage_offset

            bpy.ops.object.convert(target="MESH")

            # The clean up comes first: it dissolves degenerate geometry and drops
            # faces, which would open a cage that had already been closed
            triangulate(cage)

            # Closing is the last step: the faces added here have to span across the
            # opening, and must not be snapped on the mesh nor deleted afterwards
            finalize_border(cage, border_positions)

            bpy.ops.object.shade_flat()
            cage.display_type = "WIRE"
            cage.hide_render = True

            return cage

        islands = selection_islands()

        # ------------------------------------------------------------------
        # Cages and their vertex groups, one island at a time
        # ------------------------------------------------------------------

        # Every cage is generated before any modifier is added to the source mesh:
        # the cages are built on the shape of the source and projected back on it,
        # and the modifiers of the first cage would already be deforming that shape
        # while the following ones are being generated
        cages = []

        for position, island in enumerate(islands):
            item_name = base_name if len(islands) == 1 else f"{base_name} {position + 1}"
            pin_name = f"{item_name} Pin"

            # Filled by the cage generation with the border of the cage itself
            cage_border_positions = []

            cage = create_cage(island, item_name, cage_border_positions)

            # An island left without a single face has nothing to build a cage
            # with. The other islands are still processed: the whole selection is
            # not thrown away because one of its parts was a stray vertex
            if cage is not None and not cage.data.vertices:
                bpy.data.objects.remove(cage, do_unlink=True)
                cage = None
            if cage is None:
                continue

            # --------------------------------------------------------------
            # Vertex groups
            # --------------------------------------------------------------

            # Transfer the vertex groups of the source mesh on the cage, to let the
            # Armature deform it.
            # The transfer is done in the standard direction (from the active object
            # to the selected ones): with 'use_reverse_transfer' the layers_select_src
            # and layers_select_dst enums accept each other's items, which is error
            # prone
            bpy.ops.object.select_all(action="DESELECT")
            cage.select_set(True)
            source.select_set(True)
            context.view_layer.objects.active = source
            bpy.ops.object.data_transfer(
                use_reverse_transfer=False,
                use_freeze=False,
                data_type="VGROUP_WEIGHTS",
                use_create=True,
                vert_mapping="POLYINTERP_NEAREST",
                use_auto_transform=False,
                use_object_transform=True,
                use_max_distance=False,
                ray_radius=0.1,
                layers_select_src="ALL",
                layers_select_dst="NAME",
                mix_mode="REPLACE",
                mix_factor=1.0,
            )

            # Build the Pin group from the distance of each cage vertex to the border
            # of the cage itself.
            # The weights are not looked up on the closest vertex of the source mesh:
            # the simplification moves the border of the cage away from the vertices
            # it came from, so the vertices on the border would pick up the weight of
            # the ring behind them and be left slightly loose, letting the edge of the
            # cage move. Measuring the distance to the border gives exactly 1 on it
            pin_group = cage.vertex_groups.new(name=pin_name)

            if cage_border_positions:
                kd = KDTree(len(cage_border_positions))
                for border_index, coordinates in enumerate(cage_border_positions):
                    kd.insert(coordinates, border_index)
                kd.balance()

                # Length of a step from one vertex ring of the cage to the next, which
                # turns the Falloff Rings into a distance.
                # It is measured on the cage and not on the model: the two have
                # nothing to do with each other, and taking it from the model made the
                # same number of rings cover the whole cage on a low poly model and
                # barely leave the border on a dense one
                cage_edges = sorted(
                    (cage.data.vertices[a].co - cage.data.vertices[b].co).length
                    for a, b in (e.vertices for e in cage.data.edges)
                )
                ring_length = cage_edges[len(cage_edges) // 2] if cage_edges else 0.0

                falloff_distance = ring_length * self.falloff_rings
                # Vertices this close to the border are considered to be on it: the
                # clean up passes can move them by a fraction of an edge
                tolerance = ring_length * 0.1

                for vert in cage.data.vertices:
                    distance = kd.find(vert.co)[2]
                    if distance <= tolerance:
                        weight = 1.0
                    elif falloff_distance > 0.0:
                        weight = max(0.0, 1.0 - distance / falloff_distance)
                    else:
                        weight = 0.0
                    if weight > 0.0:
                        pin_group.add([vert.index], weight, "REPLACE")

            # Group driving the structural stiffness of the simulation, weighted on
            # how dense the model is under each vertex of the cage.
            # A modeller puts vertices where the details are, so the dense areas (the
            # tip of a breast, the lips) are exactly the ones which look wrong when
            # the cage stretches: those are stiffened, the flat areas are left free
            structural_group_name = ""
            # Only the Cloth modifier uses it: Cloth Dynamics has no stiffness to
            # scale, its faces do not stretch to begin with
            if (
                self.physics_engine == "CLOTH"
                and self.structural_enable
                and self.structural_stiffness > 0.0
            ):
                # The density is measured on the model and then projected on the cage,
                # and not sampled from the cage: the cage has a small fraction of the
                # vertices of the model, so reading it from the cage would step right
                # over the small dense areas, which are the ones being looked for

                # Local spacing of the model: mean length of the edges around a vertex
                incident = {i: [] for i in island}
                for edge in source.data.edges:
                    a, b = edge.vertices
                    if a in island and b in island:
                        length = (source.data.vertices[a].co - source.data.vertices[b].co).length
                        incident[a].append(length)
                        incident[b].append(length)

                spacing = {i: sum(v) / len(v) for i, v in incident.items() if v}

                density = [1.0] * len(cage.data.vertices)
                if spacing:
                    # The spacing is turned into a weight against the range found on
                    # this island, so the result does not depend on its scale. The
                    # range is taken well inside the ends: everything as dense as the
                    # densest fifth counts as fully dense, and a stray vertex cannot
                    # set the whole range on its own
                    ordered = sorted(spacing.values())
                    low = ordered[int(len(ordered) * 0.20)]
                    high = ordered[int(len(ordered) * 0.90)]

                    # How quickly the stiffness falls off away from the dense areas.
                    # It is derived from the Spread instead of being a setting of its
                    # own: a small Spread means the stiffness stays on the detailed
                    # parts and drops to zero right after them, a large one means it
                    # is carried over the cage gently
                    sharpness = 1.0 + 6.0 / (1.0 + self.structural_spread)

                    if high - low > 1e-9:
                        cage_kd = KDTree(len(cage.data.vertices))
                        for vert in cage.data.vertices:
                            cage_kd.insert(vert.co, vert.index)
                        cage_kd.balance()

                        # Every vertex of the model pushes its density on the closest
                        # vertex of the cage, and the highest one wins: a dense area
                        # is never lost, however few vertices the cage has over it
                        density = [0.0] * len(cage.data.vertices)
                        for index, value in spacing.items():
                            weight = min(1.0, max(0.0, 1.0 - (value - low) / (high - low)))
                            nearest = cage_kd.find(source.data.vertices[index].co)[1]
                            density[nearest] = max(density[nearest], weight**sharpness)

                        # Spread the values on the neighbours: the projection lands on
                        # single vertices, and the simulation behaves better with a
                        # gradient than with isolated stiff spots
                        neighbours = [[] for _ in cage.data.vertices]
                        for edge in cage.data.edges:
                            a, b = edge.vertices
                            neighbours[a].append(b)
                            neighbours[b].append(a)

                        for _ in range(self.structural_spread):
                            density = [
                                max(value, sum(density[n] for n in linked) / len(linked))
                                if linked
                                else value
                                for value, linked in zip(density, neighbours)
                            ]

                structural_group = cage.vertex_groups.new(name=f"{item_name} Structural")
                for index, value in enumerate(density):
                    weight = self.structural_stiffness * value
                    if weight > 0.0:
                        structural_group.add([index], weight, "REPLACE")

                structural_group_name = structural_group.name

            cage.vertex_groups.active_index = pin_group.index

            if not cage_border_positions:
                self.report(
                    {"WARNING"},
                    f"MustardUI - '{cage.name}' has no border: its Pin group is empty.",
                )

            cages.append(
                {
                    "object": cage,
                    "island": island,
                    "name": item_name,
                    "pin_name": pin_name,
                    "structural_group_name": structural_group_name,
                    "border_indices": selection_border(island),
                }
            )

        if not cages:
            for name, pose_position in stored_pose_states.items():
                bpy.data.objects[name].data.pose_position = pose_position
            bpy.ops.object.select_all(action="DESELECT")
            source.select_set(True)
            context.view_layer.objects.active = source
            bpy.ops.object.mode_set(mode="EDIT")
            self.report({"ERROR"}, "MustardUI - The cage generation produced an empty mesh.")
            return {"CANCELLED"}

        if len(cages) < len(islands):
            self.report(
                {"WARNING"},
                f"MustardUI - {len(islands) - len(cages)} vertex islands produced an "
                "empty cage and were skipped.",
            )

        # ------------------------------------------------------------------
        # Modifiers
        # ------------------------------------------------------------------

        for item in cages:
            cage = item["object"]
            item_name = item["name"]

            # Group used to restrict the Surface Deform (and the Corrective Smooth)
            # on the source mesh to the island this cage was built from
            deform_group = source.vertex_groups.new(name=item_name)
            deform_group.add(list(item["island"]), 1.0, "REPLACE")

            # Bind the island of the source mesh to its cage.
            # This is the first modifier added, because the binding is computed on
            # the evaluated shape of the cage: it has to happen while the cage is
            # still at its rest shape, before it gets its own modifiers.
            # The geometry of the cage has been rebuilt from scratch: the depsgraph
            # is forced to re-evaluate it, otherwise the binding can be computed on
            # the mesh the cage had before, and fail with 'Target contains invalid
            # polygons'
            cage.data.update()
            context.view_layer.update()
            context.evaluated_depsgraph_get().update()

            bpy.ops.object.select_all(action="DESELECT")
            source.select_set(True)
            context.view_layer.objects.active = source

            surface_deform = source.modifiers.new(name=f"{item_name} Deform", type="SURFACE_DEFORM")
            surface_deform.target = cage
            surface_deform.vertex_group = deform_group.name

            # A handful of near degenerate triangles can survive the clean up, and a
            # single one of them is enough for Blender to refuse the whole target.
            # When that happens the cage is cleaned again with a larger tolerance,
            # which removes the offending triangles, and the binding is attempted
            # once more
            for attempt in range(3):
                bpy.ops.object.surfacedeform_bind(modifier=surface_deform.name)
                if surface_deform.is_bound:
                    break

                bm = bmesh.new()
                bm.from_mesh(cage.data)
                lengths = sorted(e.calc_length() for e in bm.edges)
                if lengths:
                    bmesh.ops.dissolve_degenerate(
                        bm,
                        dist=lengths[len(lengths) // 2] * 0.1 * (attempt + 1),
                        edges=bm.edges[:],
                    )
                bmesh.ops.triangulate(
                    bm, faces=bm.faces[:], quad_method="BEAUTY", ngon_method="BEAUTY"
                )
                bmesh.ops.beautify_fill(bm, faces=bm.faces[:], edges=bm.edges[:])
                clean_topology(bm)
                bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
                bm.to_mesh(cage.data)
                bm.free()

                cage.data.update()
                context.view_layer.update()
                context.evaluated_depsgraph_get().update()

            if not surface_deform.is_bound:
                self.report(
                    {"WARNING"},
                    f"MustardUI - The Surface Deform could not be bound to "
                    f"'{cage.name}'. Try to lower the Cage Faces, or to increase the "
                    "Offset",
                )

            corrective = source.modifiers.new(name=item_name, type="CORRECTIVE_SMOOTH")
            corrective.iterations = 10
            corrective.smooth_type = "LENGTH_WEIGHTED"
            corrective.rest_source = "BIND"
            corrective.vertex_group = deform_group.name
            bpy.ops.object.correctivesmooth_bind(modifier=corrective.name)

            # Copy the Armature modifiers of the source mesh on the cage, and move
            # them at the top of the stack
            for modifier in source.modifiers:
                if modifier.type != "ARMATURE":
                    continue
                armature_modifier = cage.modifiers.new(name=modifier.name, type="ARMATURE")
                armature_modifier.object = modifier.object
                armature_modifier.use_vertex_groups = modifier.use_vertex_groups
                armature_modifier.use_bone_envelopes = modifier.use_bone_envelopes
                armature_modifier.use_deform_preserve_volume = modifier.use_deform_preserve_volume
                armature_modifier.use_multi_modifier = modifier.use_multi_modifier
                context.view_layer.objects.active = cage
                bpy.ops.object.modifier_move_to_index(modifier=armature_modifier.name, index=0)

            # Inflate custom property, to adjust the cage on the mesh
            if "Inflate" in cage.keys():
                del cage["Inflate"]
            rna_idprop_ui_create(
                cage,
                "Inflate",
                default=0.0,
                min=0.0,
                soft_min=0.0,
                max=1.0,
                soft_max=1.0,
                overridable=True,
            )

            displace = cage.modifiers.new(name="Displace", type="DISPLACE")
            displace.mid_level = 0.990
            displace.vertex_group = item["pin_name"]
            displace.invert_vertex_group = True
            fcurve = displace.driver_add("strength")
            driver = fcurve.driver
            driver.type = "AVERAGE"
            variable = driver.variables.new()
            variable.name = "var"
            variable.type = "SINGLE_PROP"
            variable.targets[0].id = cage
            variable.targets[0].data_path = '["Inflate"]'

            # Corrective Smooth on the cage
            context.view_layer.objects.active = cage
            corrective = cage.modifiers.new(name=item_name, type="CORRECTIVE_SMOOTH")
            corrective.iterations = 10
            corrective.smooth_type = "SIMPLE"
            corrective.rest_source = "BIND"
            bpy.ops.object.correctivesmooth_bind(modifier=corrective.name)

            # --------------------------------------------------------------
            # Final setup
            # --------------------------------------------------------------

            if self.parent_to_model and rig_settings.model_armature_object is not None:
                parent = rig_settings.model_armature_object
                cage.parent = parent
                cage.matrix_parent_inverse = parent.matrix_world.inverted()

            # Disable shadows for viewport/render
            cage.visible_camera = False
            cage.visible_shadow = False
            cage.visible_diffuse = False
            cage.visible_glossy = False
            cage.visible_transmission = False
            cage.visible_volume_scatter = False

            # Flag the mesh as Cage
            cage.MustardUI_tools_creators_is_created = True

            if self.add_to_panel:
                add_item = physics_settings.items.add()
                add_item.object = cage
                add_item.type = "CAGE"

            if addon_prefs.debug:
                print(
                    f"MustardUI - Cage '{cage.name}' created from "
                    f"{len(item['island'])} vertices of '{source.name}' "
                    f"({len(cage.data.vertices)} cage vertices, "
                    f"{len(item['border_indices'])} pinned border vertices)."
                )

        # Restore the Armature pose states. Every cage has been generated and bound
        # by now: what follows does not depend on the shape of the model any more
        for name, pose_position in stored_pose_states.items():
            bpy.data.objects[name].data.pose_position = pose_position
        context.view_layer.update()

        # Leave the cages selected, with the first one active
        bpy.ops.object.select_all(action="DESELECT")
        for item in cages:
            item["object"].select_set(True)
        context.view_layer.objects.active = cages[0]["object"]

        engine, preset = physics_presets.selected_preset(self)
        fallback = False

        for item in cages:
            cage = item["object"]
            if (
                physics_presets.apply_physics(
                    cage,
                    engine=engine,
                    preset=preset,
                    pin_group_name=item["pin_name"],
                    structural_group_name=item["structural_group_name"],
                )
                is None
            ):
                fallback = True
                physics_presets.apply_physics(
                    cage,
                    engine="CLOTH",
                    preset=self.cloth_preset,
                    pin_group_name=item["pin_name"],
                    structural_group_name=item["structural_group_name"],
                )

        if fallback:
            self.report(
                {"WARNING"},
                "MustardUI - The Cloth Dynamics physics could not be added: the "
                "Cloth modifier was used instead.",
            )

        if len(cages) > 1:
            self.report({"INFO"}, f"MustardUI - {len(cages)} cages created.")
        else:
            self.report({"INFO"}, "MustardUI - Cage created.")

        return {"FINISHED"}

    def draw(self, context):

        layout = self.layout

        layout.separator()

        layout.prop(self, "cage_type")

        box = layout.box()
        box.label(text="Cage Generation Settings", icon="SPHERE")
        box.prop(self, "merge_cages")
        col = box.column(align=True)
        col.prop(self, "cage_faces")
        col.prop(self, "relax_iterations")

        col = box.column(align=True)
        col.prop(self, "cage_offset")

        box.prop(self, "falloff_rings")

        box = layout.box()
        box.label(text="Physics Settings", icon="PHYSICS")
        physics_presets.draw_physics_presets(box, self)

        col = box.column(align=True)
        col.enabled = self.physics_engine == "CLOTH"
        col.prop(self, "structural_enable")
        sub = col.column(align=True)
        sub.active = self.structural_enable and self.physics_engine == "CLOTH"
        sub.prop(self, "structural_stiffness", slider=True)
        sub.prop(self, "structural_spread")

        layout.separator()

        layout.prop(self, "name")

        col = layout.column(align=True)
        col.prop(self, "parent_to_model")
        col.prop(self, "add_to_panel")

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=300)


def register():
    bpy.utils.register_class(MustardUI_ToolsCreators_CreateJiggleAccurate)


def unregister():
    bpy.utils.unregister_class(MustardUI_ToolsCreators_CreateJiggleAccurate)
