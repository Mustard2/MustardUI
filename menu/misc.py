from functools import cached_property

import bpy

from ..misc.prop_utils import evaluate_rna


class PieceDrawCache:
    def __init__(self, arm):
        self.arm = arm

    @cached_property
    def physics_objects(self):
        return {x.object for x in self.arm.MustardUI_PhysicsSettings.items}

    # First physics item of each outfit piece
    @cached_property
    def physics_items(self):
        items = {}
        for item in self.arm.MustardUI_PhysicsSettings.items:
            items.setdefault(item.outfit_object, item)
        return items

    @cached_property
    def outfit_custom_properties(self):
        return self._visible_by_piece(self.arm.MustardUI_CustomPropertiesOutfit, "outfit_piece")

    @cached_property
    def hair_custom_properties(self):
        return self._visible_by_piece(self.arm.MustardUI_CustomPropertiesHair, "hair")

    # Object.children scans all the objects in the file on every call
    @cached_property
    def children(self):
        children = {}
        for obj in bpy.data.objects:
            if obj.parent is not None:
                children.setdefault(obj.parent, []).append(obj)
        return children

    @staticmethod
    def _visible_by_piece(custom_properties, piece_attr):
        by_piece = {}
        for cp in custom_properties:
            if not cp.hidden:
                by_piece.setdefault(getattr(cp, piece_attr), []).append(cp)
        return by_piece


def mustardui_custom_properties_print(
    arm, settings, custom_properties, layout, icons_show, boxed=True
):
    if boxed:
        box = layout.box()
    else:
        box = layout
    for prop in [x for x in custom_properties if not x.hidden]:
        row = box.row(align=True)
        if icons_show:
            row.label(text=prop.name, icon=prop.icon if prop.icon != "NONE" else "DOT")
        else:
            row.label(text=prop.name)
        if not prop.is_animatable:
            try:
                row.prop(evaluate_rna(prop.rna), prop.path, text="")
            except Exception:
                row.prop(
                    settings,
                    "custom_properties_error_nonanimatable",
                    icon="ERROR",
                    text="",
                    icon_only=True,
                    emboss=False,
                )
        else:
            if prop.prop_name in arm:
                row.prop(arm, f'["{prop.prop_name}"]', text="")
            else:
                row.prop(
                    settings,
                    "custom_properties_error",
                    icon="ERROR",
                    text="",
                    icon_only=True,
                    emboss=False,
                )

    return
