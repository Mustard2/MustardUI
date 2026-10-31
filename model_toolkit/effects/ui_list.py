import bpy

from .effect import is_effect
from .settings import EFFECTS


class MUSTARDUI_UL_ModelToolkit_UIList_SceneEffects(bpy.types.UIList):
    """Effects in the scene, with the objects they are applied to"""

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        obj = item.object
        if obj is None:
            return
        effect_icon, node_group, _ = EFFECTS[item.effect]
        modifier = obj.modifiers.get(item.modifier)
        label = obj.name
        # Numbered for the objects with more of them
        if modifier is not None:
            same = [m for m in obj.modifiers if is_effect(m, node_group)]
            if len(same) > 1:
                label += f" {same.index(modifier) + 1}"
        row = layout.row(align=True)
        row.label(text=item.effect, icon=effect_icon)
        row.label(text=label, icon="OBJECT_DATA")
        if modifier is not None:
            row.prop(modifier, "show_viewport", text="", emboss=False)
            row.prop(modifier, "show_render", text="", emboss=False)
        row.operator(
            "mustardui.model_toolkit_select_object",
            text="",
            icon="RESTRICT_SELECT_OFF",
            emboss=False,
        ).name = obj.name


def register():
    bpy.utils.register_class(MUSTARDUI_UL_ModelToolkit_UIList_SceneEffects)


def unregister():
    bpy.utils.unregister_class(MUSTARDUI_UL_ModelToolkit_UIList_SceneEffects)
