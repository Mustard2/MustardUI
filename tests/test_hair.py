import importlib
import unittest

import bpy
from fake_ui import draw_all
from helpers import (
    ADDON,
    BlenderTestCase,
    build_model,
    configure_model,
    new_mesh_object,
    new_object,
    set_active,
)
from mathutils import Vector

definitions_nodes = importlib.import_module(ADDON + ".physics.definitions_nodes")
HAIR_DYNAMICS_SOCKETS = definitions_nodes.HAIR_DYNAMICS_SOCKETS
hair_dynamics_input = definitions_nodes.hair_dynamics_input


def set_modifier_input(modifier, name, value, panel=""):
    """Set a Geometry Nodes modifier input by name, in the given interface panel"""
    item = next(
        x
        for x in modifier.node_group.interface.items_tree
        if x.item_type == "SOCKET" and x.name == name and x.parent.name == panel
    )
    if bpy.app.version >= (5, 2, 0):
        getattr(modifier.properties.inputs, item.identifier).value = value
    else:
        modifier[item.identifier] = value
    # Set from Python, the object is not tagged for update as from the UI
    modifier.id_data.update_tag()


class TestHair(BlenderTestCase):
    def setUp(self):
        super().setUp()
        self.model = build_model()
        self.rig_settings = configure_model(self.model)

    def visible(self, name):
        obj = bpy.data.objects[name]
        return not obj.hide_viewport and not obj.hide_render

    # Switching hair shows only the selected one
    def test_switch_hair(self):
        self.rig_settings.hair_list = "Hair Long"
        self.assertTrue(self.visible("Hair Long"))
        self.assertFalse(self.visible("Hair Short"))

        self.rig_settings.hair_list = "Hair Short"
        self.assertTrue(self.visible("Hair Short"))
        self.assertFalse(self.visible("Hair Long"))

    # Hair global switch toggles the Subdivision modifiers
    def test_global_modifier_switch(self):
        subsurf = bpy.data.objects["Hair Long"].modifiers.new("Subdivision", "SUBSURF")
        self.rig_settings.hair_enable_global_subsurface = True
        bpy.ops.mustardui.hair_switchglobal(enable=0)
        self.assertFalse(subsurf.show_viewport)
        bpy.ops.mustardui.hair_switchglobal(enable=1)
        self.assertTrue(subsurf.show_viewport)

    # Clean Model deletes the hair not in use and their rigs, keeping the rigs of the selected hair
    def test_clean_model_unselected_hair(self):
        hair = self.model["hair"]
        rigs = {}
        for name, users in (
            ("Short Rig", ("Hair Short",)),
            ("Long Rig", ("Hair Long",)),
            ("Shared Rig", ("Hair Short", "Hair Long")),
        ):
            rigs[name] = new_object(name, bpy.data.armatures.new(name), hair)
            for user in users:
                bpy.data.objects[user].modifiers.new(name, "ARMATURE").object = rigs[name]
        bpy.data.objects["Hair Long"].parent = rigs["Long Rig"]
        new_mesh_object("Hair Short Bangs", hair)
        self.rig_settings.hair_list = "Hair Short"

        bpy.ops.mustardui.cleanmodel(remove_unselected_hair=True)
        self.assertEqual(
            sorted(o.name for o in hair.objects), ["Hair Short", "Shared Rig", "Short Rig"]
        )

    # Deleting a hair before the selected one keeps the selection, and Clean Model the worn hair
    def test_selection_after_deleting_hair(self):
        new_mesh_object("Hair Bob", self.model["hair"])
        self.rig_settings.hair_list = "Hair Long"
        bpy.data.objects.remove(bpy.data.objects["Hair Short"])
        self.assertEqual(self.rig_settings.hair_list, "Hair Long")

        bpy.ops.mustardui.cleanmodel(remove_unselected_hair=True)
        self.assertEqual([o.name for o in self.model["hair"].objects], ["Hair Long"])


class TestParticleHairToCurves(BlenderTestCase):
    def setUp(self):
        super().setUp()
        self.model = build_model()
        self.rig_settings = configure_model(self.model)
        self.rig_settings.hair_list = "Hair Long"
        self.hair = bpy.data.objects["Hair Long"]
        self.hair.modifiers.new("Hair", "PARTICLE_SYSTEM")
        settings = self.hair.particle_systems[0].settings
        settings.type = "HAIR"
        settings.count = 20
        settings.hair_length = 0.3
        settings.hair_step = 10
        # Hair leaving the surface at an angle
        settings.tangent_factor = 1.0
        settings.child_type = "SIMPLE"
        settings.child_percent = settings.rendered_child_count = 5
        set_active(self.model["armature"])
        self.hair.select_set(True)

    def roots(self):
        dg = bpy.context.evaluated_depsgraph_get()
        obj = self.hair.evaluated_get(dg)
        mod = obj.modifiers["Hair"]
        return [p.hair_keys[0].co_object(obj, mod, p) for p in mod.particle_system.particles]

    # The guides become attached curves, replacing the particle hair in the hair list
    def test_convert(self):
        roots = self.roots()
        self.assertEqual(bpy.ops.mustardui.model_toolkit_particle_hair_to_curves(), {"FINISHED"})

        curves = bpy.data.objects["Hair Long"]
        self.assertEqual(curves.type, "CURVES")
        self.assertEqual(curves.parent, self.hair)
        self.assertEqual(curves.data.surface, self.hair)
        # Without UV Maps, one is added to attach the curves
        self.assertEqual(curves.data.surface_uv_map, "Hair Surface")
        self.assertEqual(self.hair.name, "Hair Long Surface")
        self.assertNotIn(self.hair.name, self.model["hair"].objects)
        self.assertEqual(self.rig_settings.hair_list, "Hair Long")
        self.assertFalse(self.hair.modifiers["Hair"].show_viewport)

        self.assertEqual(len(curves.data.curves), 20)
        self.assertTrue(all(3 <= c.points_length <= 11 for c in curves.data.curves))
        for curve, root in zip(curves.data.curves, roots, strict=True):
            self.assertLess((curve.points[0].position - root).length, 1e-5)

        # Simple children replace the guides, with the roots on the surface around them
        dg = bpy.context.evaluated_depsgraph_get()
        evaluated = curves.evaluated_get(dg).data
        self.assertEqual(len(evaluated.curves), 20 * 5)
        radius = self.hair.particle_systems[0].settings.child_radius
        normals = curves.data.attributes["surface_normal"].data
        guides = evaluated.attributes["guide"].data
        for curve, guide in zip(evaluated.curves, guides, strict=True):
            offset = curve.points[0].position - curves.data.curves[guide.value].points[0].position
            self.assertTrue(0 < offset.length <= radius + 1e-5)
            self.assertLess(abs(offset.dot(normals[guide.value].vector)), 1e-5)

    def curves_count(self):
        curves = bpy.data.objects["Hair Long"]
        return len(curves.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.curves)

    # The children are turned off and set from the modifier inputs, shown in the Hair panel
    def test_children_settings(self):
        bpy.ops.mustardui.model_toolkit_particle_hair_to_curves()
        children = bpy.data.objects["Hair Long"].modifiers["Hair Children"]

        set_modifier_input(children, "Viewport Amount", 3)
        self.assertEqual(self.curves_count(), 20 * 3)
        set_modifier_input(children, "Children", False)
        self.assertEqual(self.curves_count(), 20)

        drawer = draw_all(bpy.context)
        self.assertIn("PANEL_PT_MustardUI_Hair_Children", drawer.drawn)
        self.assertEqual(drawer.errors, [], "\n" + "\n".join(drawer.errors))

    # Each particle system has its own children settings, in a panel named after it
    def test_children_settings_systems(self):
        self.hair.modifiers.new("Fringe", "PARTICLE_SYSTEM")
        settings = self.hair.particle_systems[0].settings.copy()
        settings.child_percent = settings.rendered_child_count = 2
        self.hair.particle_systems[1].settings = settings
        names = [x.name for x in self.hair.particle_systems]
        bpy.ops.mustardui.model_toolkit_particle_hair_to_curves()
        children = bpy.data.objects["Hair Long"].modifiers["Hair Children"]

        interface = children.node_group.interface.items_tree
        self.assertEqual([x.name for x in interface if x.item_type == "PANEL"], names)
        self.assertEqual(self.curves_count(), 20 * 5 + 20 * 2)
        set_modifier_input(children, "Viewport Amount", 4, panel=names[1])
        self.assertEqual(self.curves_count(), 20 * 5 + 20 * 4)

        drawer = draw_all(bpy.context)
        self.assertIn("PANEL_PT_MustardUI_Hair_Children", drawer.drawn)
        self.assertEqual(drawer.errors, [], "\n" + "\n".join(drawer.errors))

    # Without the Hair Dynamics, the children are not taken as the hair physics
    def test_children_without_physics(self):
        self.rig_settings.hair_physics_support = True
        bpy.ops.mustardui.model_toolkit_particle_hair_to_curves(physics=False)

        drawer = draw_all(bpy.context)
        self.assertIn("PANEL_PT_MustardUI_Hair_Children", drawer.drawn)
        self.assertNotIn("PANEL_PT_MustardUI_Hair_Dynamics", drawer.drawn)

    # The simulated roots follow the deformation of the surface
    @unittest.skipIf(bpy.app.version < (5, 2, 0), "Hair Dynamics needs Blender 5.2")
    def test_physics_follows_surface(self):
        self.hair.shape_key_add(name="Basis")
        key = self.hair.shape_key_add(name="Up")
        for point in key.data:
            point.co.z += 0.1
        key.value = 0.0
        key.keyframe_insert("value", frame=1)
        key.value = 1.0
        key.keyframe_insert("value", frame=5)
        roots = self.roots()
        bpy.ops.mustardui.model_toolkit_particle_hair_to_curves()

        curves = bpy.data.objects["Hair Long"]
        self.assertEqual(curves.modifiers[0].name, "Hair Dynamics")
        curves.modifiers["Hair Children"].show_viewport = False
        for frame in range(1, 6):
            bpy.context.scene.frame_set(frame)
        dg = bpy.context.evaluated_depsgraph_get()
        evaluated = curves.evaluated_get(dg).data.curves
        for curve, root in zip(evaluated, roots, strict=True):
            self.assertAlmostEqual((curve.points[0].position - root).z, 0.1, delta=1e-3)

    # Scaled hair keeps its length, and the pin follows the particle hair pin weights
    @unittest.skipIf(bpy.app.version < (5, 2, 0), "Hair Dynamics needs Blender 5.2")
    def test_physics_scaled_hair(self):
        self.hair.scale = (0.5, 0.5, 0.5)
        bpy.ops.mustardui.model_toolkit_particle_hair_to_curves()

        curves = bpy.data.objects["Hair Long"]
        pin = [x.value for x in curves.data.attributes["pin"].data]
        self.assertAlmostEqual(max(pin), 1.0, places=5)
        self.assertAlmostEqual(min(pin), 0.0, places=5)

        curves.modifiers["Hair Children"].show_viewport = False
        rest = [p.position.copy() for p in curves.data.points]
        for frame in range(1, 11):
            bpy.context.scene.frame_set(frame)
        dg = bpy.context.evaluated_depsgraph_get()
        evaluated = curves.evaluated_get(dg).data
        for a, b in zip(curves.data.curves, evaluated.curves, strict=True):
            for i in range(a.points_length - 1):
                length = (rest[a.first_point_index + i + 1] - rest[a.first_point_index + i]).length
                simulated = (b.points[i + 1].position - b.points[i].position).length
                self.assertAlmostEqual(simulated / length, 1.0, delta=0.05)

    # Moving the model during the simulation carries the simulated hair
    @unittest.skipIf(bpy.app.version < (5, 2, 0), "Hair Dynamics needs Blender 5.2")
    def test_physics_follows_model(self):
        bpy.ops.mustardui.model_toolkit_particle_hair_to_curves()
        curves = bpy.data.objects["Hair Long"]
        dynamics = curves.modifiers["Hair Dynamics"]
        self.assertEqual(
            hair_dynamics_input(dynamics, "simulation_space").value, self.model["armature"]
        )
        self.assertEqual(hair_dynamics_input(dynamics, "pin_stiffness").value, 30.0)
        curves.modifiers["Hair Children"].show_viewport = False
        for frame in range(1, 6):
            bpy.context.scene.frame_set(frame)

        def points():
            evaluated = curves.evaluated_get(bpy.context.evaluated_depsgraph_get())
            return [evaluated.matrix_world @ p.position for p in evaluated.data.points]

        before = points()
        self.model["armature"].location.x += 1.0
        bpy.context.view_layer.update()
        for a, b in zip(before, points(), strict=True):
            self.assertLess((b - a - Vector((1.0, 0.0, 0.0))).length, 1e-3)

    # Collision cages collide with the hair when their physics is enabled
    @unittest.skipIf(bpy.app.version < (5, 2, 0), "Hair Dynamics needs Blender 5.2")
    def test_physics_collision_cage(self):
        set_active(self.model["body"])
        self.model["body"].select_set(True)
        bpy.ops.mustardui.model_toolkit_create_collision_cage(add_to_panel=True)
        physics = self.model["armature"].data.MustardUI_PhysicsSettings
        cage = physics.items[0].object
        physics.enable_physics = True
        physics.items[0].enable = True

        # A collection from a previous conversion, out of the scene, is linked again
        bpy.data.collections.new("Tester Hair Colliders").objects.link(cage)
        set_active(self.model["armature"])
        self.hair.select_set(True)
        bpy.ops.mustardui.model_toolkit_particle_hair_to_curves()
        dynamics = bpy.data.objects["Hair Long"].modifiers["Hair Dynamics"]
        colliders = getattr(
            dynamics.properties.inputs, HAIR_DYNAMICS_SOCKETS["effectors_collection"]
        ).value
        self.assertEqual(list(colliders.objects), [cage])
        self.assertIn(colliders, bpy.context.scene.collection.children_recursive)

        collider = cage.modifiers["Hair Collider"]
        self.assertTrue(collider.show_viewport)
        physics.items[0].enable = False
        self.assertFalse(collider.show_viewport)

    # The hair physics switch turns the simulation on and off, also across hair switches
    @unittest.skipIf(bpy.app.version < (5, 2, 0), "Hair Dynamics needs Blender 5.2")
    def test_physics_switch(self):
        bpy.ops.mustardui.model_toolkit_particle_hair_to_curves()
        curves = bpy.data.objects["Hair Long"]
        dynamics, children = curves.modifiers["Hair Dynamics"], curves.modifiers["Hair Children"]
        self.assertTrue(curves.MustardUI_OutfitSettings.physics)
        self.assertTrue(dynamics.show_viewport)

        curves.MustardUI_OutfitSettings.physics = False
        self.assertFalse(dynamics.show_viewport)
        self.assertTrue(children.show_viewport)

        rig_settings = self.model["armature"].data.MustardUI_RigSettings
        rig_settings.hair_list = "Hair Short"
        rig_settings.hair_list = "Hair Long"
        self.assertFalse(dynamics.show_viewport)
        self.assertTrue(children.show_viewport)

        curves.MustardUI_OutfitSettings.physics = True
        self.assertTrue(dynamics.show_viewport)

        self.rig_settings.hair_physics_support = True
        self.assertIn("PANEL_PT_MustardUI_Hair_Dynamics", draw_all(bpy.context).drawn)
