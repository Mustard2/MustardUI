import bpy


class MUSTARDUI_UL_ClothPinEmpties_UIList(bpy.types.UIList):
    """Pin Empties of the cloth: the Empty and the radius it pins"""

    def draw_item(self, _context, layout, _data, item, _icon, _active_data, _active_prop, _index):
        row = layout.row(align=True)
        row.prop(item, "empty", text="", emboss=False, icon="EMPTY_AXIS")
        row.prop(item, "radius", text="")


def register():
    bpy.utils.register_class(MUSTARDUI_UL_ClothPinEmpties_UIList)


def unregister():
    bpy.utils.unregister_class(MUSTARDUI_UL_ClothPinEmpties_UIList)
