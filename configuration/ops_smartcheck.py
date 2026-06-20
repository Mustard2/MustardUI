import bpy

from .. import __package__ as base_package
from ..model_selection.active_object import mustardui_active_object
from ..tools_creators.ops_optimize_mods import mask_vg_name


def smartcheck_body_mask_from_vg(self, context, rig_settings):
    warnings = 0

    outfit_colls = [x.collection for x in rig_settings.outfits_collections if x.collection]

    body = rig_settings.model_body
    if body is None:
        warnings += 1
        print("MustardUI Smart Check - Body Mask from Vertex Groups - No Body Object found")
        return warnings

    arm_idx = next(
        (i for i, m in enumerate(body.modifiers) if m.type == "ARMATURE"),
        None,
    )
    if arm_idx is None:
        warnings += 1
        print("MustardUI Smart Check - Body Mask from Vertex Groups - No Armature on Body")
        return warnings

    all_colls = outfit_colls + (
        [rig_settings.extras_collection] if rig_settings.extras_collection else []
    )
    obj_to_col = {o: c for c in all_colls for o in c.objects if o.type == "MESH"}

    if len(obj_to_col) < 1:
        warnings += 1
        print(
            "MustardUI Smart Check - Body Mask from Vertex Groups - "
            "No Outfit added on the current model"
        )
        return warnings

    if any(
        mod.type in {"MASK", "VERTEX_WEIGHT_MIX"} and outfit_obj.name in mod.name.split("|")
        for outfit_obj in obj_to_col
        for mod in body.modifiers
    ):
        rig_settings.outfits_enable_global_mask = True

    if mask_vg_name not in body.vertex_groups:
        body.vertex_groups.new(name=mask_vg_name)

    insert_pos = arm_idx + 1 if arm_idx is not None else 0

    # Temporarily set body as active for modifier_move_to_index
    prev_active = context.view_layer.objects.active
    context.view_layer.objects.active = body

    outfits_with_mask = 0
    for vg in body.vertex_groups:
        mod = next(
            (
                m
                for m in body.modifiers
                if (m.type == "VERTEX_WEIGHT_MIX" and m.vertex_group_b == vg.name)
                or (
                    self.smartcheck_body_mask_optimize
                    and m.type == "MASK"
                    and m.vertex_group == vg.name
                )
            ),
            None,
        )

        for outfit_obj, col in obj_to_col.items():
            if outfit_obj.name not in vg.name.split("|"):
                continue

            outfits_with_mask += 1

            if mod is None or (mod is not None and mod.type == "MASK"):
                if mod is not None and mod.type == "MASK":
                    body.modifiers.remove(mod)
                mod = body.modifiers.new(name=vg.name, type="VERTEX_WEIGHT_MIX")
                mod.vertex_group_a = mask_vg_name
                mod.vertex_group_b = vg.name
                mod.mix_set = "ALL"
                mod.mix_mode = "ADD"
                mod.show_expanded = False

            is_active = col.name == rig_settings.outfits_list
            is_locked = getattr(outfit_obj, "MustardUI_outfit_lock", False)
            visible = (
                (is_active or is_locked)
                and not outfit_obj.hide_viewport
                and rig_settings.outfits_global_mask
            )
            mod.show_viewport = visible
            mod.show_render = visible
            bpy.ops.object.modifier_move_to_index(modifier=mod.name, index=insert_pos)
            insert_pos += 1
            rig_settings.outfits_enable_global_mask = True
            break  # first-match wins: one outfit per VG

    if outfits_with_mask < 1:
        warnings += 1
        print("MustardUI Smart Check - Body Mask from Vertex Groups - No valid Vertex Group to add")
        return warnings

    mask_mod = next(
        (m for m in body.modifiers if m.type == "MASK" and m.name == mask_vg_name),
        None,
    )
    if mask_mod is None:
        mask_mod = body.modifiers.new(name=mask_vg_name, type="MASK")
        mask_mod.vertex_group = mask_vg_name
        mask_mod.invert_vertex_group = True
        mask_mod.show_expanded = False
        rig_settings.outfits_enable_global_mask = True

    last_vwm = next(
        (i for i, m in reversed(list(enumerate(body.modifiers))) if m.type == "VERTEX_WEIGHT_MIX"),
        -1,
    )
    target_mask = min(
        last_vwm + 1 if last_vwm >= 0 else insert_pos,
        len(body.modifiers) - 1,
    )
    current_mask_idx = next(
        i for i, m in enumerate(body.modifiers) if m.name == mask_vg_name and m.type == "MASK"
    )
    if current_mask_idx != target_mask:
        bpy.ops.object.modifier_move_to_index(modifier=mask_mod.name, index=target_mask)
        print(
            f"MustardUI Smart Check - Body Mask from Vertex Groups - "
            f"Mask repositioned to index {target_mask}"
        )

    context.view_layer.objects.active = prev_active

    subdiv_idx = None
    mask_pos = None
    for i, mod in enumerate(body.modifiers):
        if mod.type == "SUBSURF" and subdiv_idx is None:
            subdiv_idx = i
        if mod.type == "MASK" and mod.name == mask_vg_name and mask_pos is None:
            mask_pos = i
    if subdiv_idx is not None and mask_pos is not None and subdiv_idx < mask_pos:
        warnings += 1
        print(
            "MustardUI Smart Check - Body Mask from Vertex Groups - "
            "The Subdivision modifier should be manually placed after "
            "the Mask"
        )

    return warnings


class MustardUI_Configuration_SmartCheck(bpy.types.Operator):
    """Search for MustardUI configuration options based on the name of the model and its body"""  # noqa: E501

    bl_idname = "mustardui.configuration_smartcheck"
    bl_label = "Smart Check"
    bl_options = {"UNDO"}

    smartcheck_custom_properties: bpy.props.BoolProperty(
        name="Body Custom Properties",
        default=True,
        description="Search for Body Custom Properties that respects "
        "MustardUI Naming Convention.\nThis will "
        "overwrite previous manual modifications of "
        "custom properties found with this tool.",
    )
    smartcheck_outfits: bpy.props.BoolProperty(
        name="Outfits",
        default=True,
        description="Find the Outfit collections in the current scene.\n"
        "The collections will be added only if their name contains "
        "the name of the model as set in the Configuration menu.",
    )
    smartcheck_armature: bpy.props.BoolProperty(
        name="Armature",
        default=True,
        description="Search for Armature bone collection based on the Armature"
        "type defaults.\nCurrent supported: ARP, Rigify and MHX.",
    )
    reset_current_collections: bpy.props.BoolProperty(
        name="Reset Current Bone Collections",
        default=True,
        description="If disabled, do not remote the current enabled bone "
        "collections from the UI.\nNote that the bone "
        "collections not added to the UI will not be "
        "preserved, i.e., in case they are generated by "
        "default for the armature data type (ARP, Rigify, "
        "MHX).",
    )
    smartcheck_settings: bpy.props.BoolProperty(
        name="Global Settings",
        default=True,
        description="Look for Global settings on the current Body and Outfits."
        "\nFor instance, if a Smooth Correction modifier is found "
        "on the Body Object or in the Outfits/Extras/Hair, it will "
        "be added as a Global Setting.",
    )
    smartcheck_body_mask_from_vg: bpy.props.BoolProperty(
        name="Create Masks from Vertex Groups",
        default=True,
        description="Auto-create Vertex Weight Mix modifiers on the Body "
        "by matching vertex group with Outfit Objects names",
    )
    smartcheck_body_mask_optimize: bpy.props.BoolProperty(
        name="Optimize Mask modifiers",
        default=True,
        description="Replace Mask modifiers with Vertex Weight Mix modifiers.\n"
        "This should greatly improve the performance of the model "
        "when several Maks are used",
    )

    @classmethod
    def poll(cls, context):

        res, arm = mustardui_active_object(context, config=1)
        if arm is None:
            return False

        rig_settings = arm.MustardUI_RigSettings
        return (
            res
            and rig_settings.model_MustardUI_naming_convention
            and rig_settings.model_body is not None
            and rig_settings.model_name != ""
        )

    def execute(self, context):

        res, obj = mustardui_active_object(context, config=1)
        rig_settings = obj.MustardUI_RigSettings
        addon_prefs = context.preferences.addons[base_package].preferences

        warnings = 0

        # Try to assign the rig object
        if not obj.MustardUI_created:
            if context.active_object is not None and context.active_object.type == "ARMATURE":
                rig_settings.model_armature_object = context.active_object

        # Initialize Smart Check header
        if addon_prefs.debug:
            print("\nMustardUI - Smart Check - Start\n")

        if self.smartcheck_custom_properties:
            if addon_prefs.debug:
                print("MustardUI - Smart Check - Searching for body additional options\n")
            # Check for body additional properties
            bpy.ops.mustardui.property_smartcheck()

        # Search for outfit collections
        if self.smartcheck_outfits:
            if addon_prefs.debug:
                print("\nMustardUI - Smart Check - Searching for outfits\n")
            bpy.ops.mustardui.outfits_smartcheck()

        # Search for hair
        if addon_prefs.debug:
            print("\nMustardUI - Smart Check - Searching for hair.")
        hair_collections = [
            x
            for x in bpy.data.collections
            if (rig_settings.model_name in x.name) and ("Hair" in x.name)
        ]
        if rig_settings.hair_collection is None:
            if len(hair_collections) == 1:
                rig_settings.hair_collection = hair_collections[0]
                print(
                    "\nMustardUI - Smart Check - "
                    + hair_collections[0].name
                    + " set as Hair collection"
                )
            elif len(hair_collections) == 0:
                print(
                    "\nMustardUI - Smart Check - Can not find any Hair collection "
                    "compatible with MustardUI naming convention."
                )
            else:
                print(
                    "\nMustardUI - Smart Check - More than 1 collection has been "
                    "found. No collection has been set as the Hair one to avoid "
                    "un-wanted behaviour."
                )
        else:
            print(
                "\nMustardUI - Smart Check - Hair collection already defined. Skipping this part."
            )

        # Search for Extras
        if addon_prefs.debug:
            print("\nMustardUI - Smart Check - Searching for extras.")

        if rig_settings.extras_collection is None:
            extras_collections = [
                x
                for x in bpy.data.collections
                if (rig_settings.model_name in x.name) and ("Extras" in x.name)
            ]
            if len(extras_collections) == 1:
                rig_settings.extras_collection = extras_collections[0]
                print(
                    "\nMustardUI - Smart Check - "
                    + extras_collections[0].name
                    + " set as Extras collection"
                )
            elif len(extras_collections) == 0:
                print(
                    "\nMustardUI - Smart Check - Can not find any Extras collection "
                    "compatible with MustardUI naming convention."
                )
            else:
                print(
                    "\nMustardUI - Smart Check - More than 1 collection has been "
                    "found. No collection has been set as the Extras one to avoid "
                    "un-wanted behaviour."
                )
        else:
            print(
                "\nMustardUI - Smart Check - Extras collection already defined. Skipping this part."
            )

        # Search for Hair Extras
        if addon_prefs.debug:
            print("\nMustardUI - Smart Check - Searching for extras.")

        if rig_settings.hair_extras_collection is None:
            hair_extras_collection = [
                x
                for x in bpy.data.collections
                if (rig_settings.model_name in x.name)
                and ("Extras" in x.name)
                and ("Hair" in x.name)
            ]
            if len(hair_extras_collection) == 1:
                rig_settings.extras_hair_collection = hair_extras_collection[0]
                print(
                    "\nMustardUI - Smart Check - "
                    + hair_extras_collection[0].name
                    + "set as Hair Extras "
                    "collection"
                )
            elif len(hair_extras_collection) == 0:
                print(
                    "\nMustardUI - Smart Check - Can not find any Hair Extras "
                    "collection compatible with MustardUI naming convention."
                )
            else:
                print(
                    "\nMustardUI - Smart Check - More than 1 collection has been "
                    "found. No collection has been set as the Hair Extras one to "
                    "avoid un-wanted behaviour."
                )
        else:
            print(
                "\nMustardUI - Smart Check - Hair Extras collection already defined. "
                "Skipping this part."
            )

        if self.smartcheck_armature:
            bpy.ops.mustardui.armature_smartcheck(
                reset_current_collections=self.reset_current_collections
            )

        if self.smartcheck_settings:
            if addon_prefs.debug:
                print("\nMustardUI - Smart Check - Searching for Global Settings to enable.")

            # Body
            if rig_settings.model_body is not None:
                rig_settings.body_enable_subdiv = False
                rig_settings.body_enable_smoothcorr = False
                rig_settings.body_enable_solidify = False

                for m in rig_settings.model_body.modifiers:
                    if m.type == "SUBSURF":
                        rig_settings.body_enable_subdiv = True
                    elif m.type == "CORRECTIVE_SMOOTH":
                        rig_settings.body_enable_smoothcorr = True
                    elif m.type == "SOLIDIFY":
                        rig_settings.body_enable_solidify = True
            else:
                if addon_prefs.debug:
                    print("\nMustardUI - Smart Check - Could not check Body Global Properties.")

            # Outfits
            objects = []
            outfit_colls = [x.collection for x in rig_settings.outfits_collections if x.collection]
            for c in outfit_colls:
                for obj in [x for x in c.objects if x.type == "MESH"]:
                    objects.append(obj)
            if rig_settings.extras_collection is not None:
                for obj in [x for x in rig_settings.extras_collection.objects if x.type == "MESH"]:
                    objects.append(obj)

            rig_settings.outfits_enable_global_subsurface = False
            rig_settings.outfits_enable_global_smoothcorrection = False
            rig_settings.outfits_enable_global_surfacedeform = False
            rig_settings.outfits_enable_global_shrinkwrap = False
            rig_settings.outfits_enable_global_mask = False
            rig_settings.outfits_enable_global_solidify = False
            rig_settings.outfits_enable_global_triangulate = False

            for obj in [x for x in objects if x is not None]:
                for m in obj.modifiers:
                    if m.type == "SUBSURF":
                        rig_settings.outfits_enable_global_subsurface = True
                    elif m.type == "CORRECTIVE_SMOOTH":
                        rig_settings.outfits_enable_global_smoothcorrection = True
                    elif m.type == "SURFACE_DEFORM":
                        rig_settings.outfits_enable_global_surfacedeform = True
                    elif m.type == "SHRINKWRAP":
                        rig_settings.outfits_enable_global_shrinkwrap = True
                    elif m.type == "MASK":
                        rig_settings.outfits_enable_global_mask = True
                    elif m.type == "SOLIDIFY":
                        rig_settings.outfits_enable_global_solidify = True
                    elif m.type == "TRIANGULATE":
                        rig_settings.outfits_enable_global_triangulate = True

            # Hair
            if rig_settings.hair_collection is not None:
                objects = []
                for obj in [
                    x for x in rig_settings.hair_collection.objects if x.type in {"MESH", "CURVES"}
                ]:
                    objects.append(obj)

                rig_settings.hair_enable_global_subsurface = False
                rig_settings.hair_enable_global_smoothcorrection = False
                rig_settings.hair_enable_global_solidify = False
                rig_settings.hair_enable_global_particles = False

                for obj in [x for x in objects if x is not None]:
                    for m in obj.modifiers:
                        if m.type == "SUBSURF":
                            rig_settings.hair_enable_global_subsurface = True
                        elif m.type == "CORRECTIVE_SMOOTH":
                            rig_settings.hair_enable_global_smoothcorrection = True
                        elif m.type == "SOLIDIFY":
                            rig_settings.hair_enable_global_solidify = True
                        elif m.type == "PARTICLE_SYSTEM":
                            rig_settings.hair_enable_global_particles = True

        # Auto-create VERTEX_WEIGHT_MIX from body VGs matching outfit objects
        if self.smartcheck_body_mask_from_vg:
            warnings += smartcheck_body_mask_from_vg(self, context, rig_settings)

        # End of debug messages
        if addon_prefs.debug:
            print("\nMustardUI - Smart Check - End")

        if warnings:
            self.report(
                {"WARNING"},
                "MustardUI - Smart Check generated Warnings. See the Console for more information.",
            )
        else:
            self.report({"INFO"}, "MustardUI - Smart Check complete.")

        return {"FINISHED"}

    def invoke(self, context, event):
        addon_prefs = context.preferences.addons[base_package].preferences
        return context.window_manager.invoke_props_dialog(
            self, width=550 if addon_prefs.debug else 450
        )

    def draw(self, context):

        layout = self.layout

        box = layout.box()
        box.label(text="Categories", icon="DUPLICATE")
        col = box.column()
        col.prop(self, "smartcheck_outfits")

        col.prop(self, "smartcheck_armature")
        row = col.row(align=True)
        row.enabled = self.smartcheck_armature
        row.label(text="", icon="BLANK1")
        row.prop(self, "reset_current_collections")

        col.prop(self, "smartcheck_settings")
        col.prop(self, "smartcheck_custom_properties")

        box = layout.box()
        box.label(text="Mask", icon="MOD_MASK")
        col = box.column(align=True)
        col.prop(self, "smartcheck_body_mask_from_vg")
        col.prop(self, "smartcheck_body_mask_optimize")


def register():
    bpy.utils.register_class(MustardUI_Configuration_SmartCheck)


def unregister():
    bpy.utils.unregister_class(MustardUI_Configuration_SmartCheck)
