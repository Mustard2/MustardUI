import bpy

LAYOUT_FUNCTIONS = set(bpy.types.UILayout.bl_rna.functions.keys())
SUBLAYOUTS = {"row", "column", "box", "split", "column_flow", "grid_flow", "menu_pie"}


def operator_properties(idname):
    module, name = idname.split(".", 1)
    try:
        return getattr(getattr(bpy.ops, module), name).get_rna_type().properties
    except (AttributeError, KeyError):
        return None


def rna_property_exists(data, prop):
    if prop.startswith('["'):
        return prop[2:-2] in data.keys()
    return data.bl_rna.properties.get(prop) is not None


class FakeOperatorProperties:
    def __init__(self, layout, idname, properties):
        object.__setattr__(self, "_layout", layout)
        object.__setattr__(self, "_idname", idname)
        object.__setattr__(self, "_properties", properties)

    def __setattr__(self, name, value):
        if self._properties.get(name) is None:
            self._layout.error(f"Operator {self._idname} has no property '{name}'")


class FakeLayout:
    """UILayout stand-in that validates what the draw code references."""

    def __init__(self, drawer):
        self._drawer = drawer

    def error(self, message):
        self._drawer.errors.append(f"{self._drawer.current}: {message}")

    def check_prop(self, data, prop):
        if data is None:
            self.error(f"prop '{prop}' drawn from None")
        elif not rna_property_exists(data, prop):
            self.error(f"{data.bl_rna.identifier} has no property '{prop}'")

    def sub(self, *args, **kwargs):
        return FakeLayout(self._drawer)

    def prop(self, data, property, *args, **kwargs):
        self.check_prop(data, property)

    prop_enum = prop_menu_enum = props_enum = prop_tabs_enum = prop
    template_icon_view = prop

    def prop_search(self, data, property, search_data, search_property, *args, **kwargs):
        self.check_prop(data, property)
        self.check_prop(search_data, search_property)

    def operator(self, operator, *args, **kwargs):
        properties = operator_properties(operator)
        if properties is None:
            self.error(f"unknown operator '{operator}'")
            properties = {}
        return FakeOperatorProperties(self, operator, properties)

    def operator_menu_enum(self, operator, property, *args, **kwargs):
        properties = operator_properties(operator)
        if properties is None or properties.get(property) is None:
            self.error(f"unknown operator enum '{operator}.{property}'")

    def menu(self, menu, *args, **kwargs):
        if getattr(bpy.types, menu, None) is None:
            self.error(f"unknown menu '{menu}'")

    def panel(self, idname, *args, **kwargs):
        return FakeLayout(self._drawer), FakeLayout(self._drawer)

    def panel_prop(self, data, property, *args, **kwargs):
        self.check_prop(data, property)
        return FakeLayout(self._drawer), FakeLayout(self._drawer)

    def template_list(
        self, listtype_name, list_id, dataptr, propname, active_dataptr, active_propname, **kwargs
    ):
        self.check_prop(dataptr, propname)
        self.check_prop(active_dataptr, active_propname)
        ui_list = getattr(bpy.types, listtype_name, None)
        if ui_list is None:
            self.error(f"unknown UIList '{listtype_name}'")
        elif dataptr is not None and active_dataptr is not None:
            self._drawer.draw_ui_list(ui_list, dataptr, propname, active_dataptr, active_propname)

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        if name not in LAYOUT_FUNCTIONS:
            self.error(f"UILayout has no function '{name}'")
        if name in SUBLAYOUTS:
            return self.sub
        return lambda *args, **kwargs: None


class FakeSelf:
    """Instance stand-in for Panel/UIList/Menu classes, which Blender instantiates."""

    def __init__(self, cls, layout, **attrs):
        self._cls = cls
        self.layout = layout
        self.bl_idname = getattr(cls, "bl_idname", cls.__name__)
        for key, value in attrs.items():
            setattr(self, key, value)

    def __getattr__(self, name):
        value = getattr(self._cls, name)
        return value.__get__(self) if callable(value) and hasattr(value, "__get__") else value


class Drawer:
    def __init__(self):
        self.errors = []
        self.current = ""
        self.drawn = []

    def run(self, name, function, *args):
        self.current = name
        try:
            function(*args)
        except Exception as e:
            import traceback

            self.errors.append(f"{name}: {type(e).__name__}: {e}\n{traceback.format_exc()}")

    def draw_panel(self, cls, context):
        if hasattr(cls, "poll") and not cls.poll(context):
            return
        self.drawn.append(cls.__name__)
        panel = FakeSelf(cls, FakeLayout(self), is_popover=False, bl_label=cls.bl_label)
        if hasattr(cls, "draw_header"):
            self.run(cls.__name__ + ".draw_header", cls.draw_header, panel, context)
        self.run(cls.__name__, cls.draw, panel, context)

    def draw_ui_list(self, cls, data, propname, active_data, active_propname):
        items = getattr(data, propname)
        ui_list = FakeSelf(
            cls,
            FakeLayout(self),
            layout_type="DEFAULT",
            filter_name="",
            use_filter_show=False,
            use_filter_invert=False,
            use_filter_sort_alpha=False,
            use_filter_sort_reverse=False,
            use_filter_sort_lock=False,
            bitflag_filter_item=1 << 30,
            bitflag_item_never_show=1 << 31,
        )
        name, previous = cls.__name__, self.current
        context = bpy.context
        if "filter_items" in cls.__dict__:
            self.run(name + ".filter_items", cls.filter_items, ui_list, context, data, propname)
        if "draw_filter" in cls.__dict__:
            self.run(name + ".draw_filter", cls.draw_filter, ui_list, context, FakeLayout(self))
        for index, item in enumerate(items):
            self.run(
                name,
                cls.draw_item,
                ui_list,
                context,
                FakeLayout(self),
                data,
                item,
                0,
                active_data,
                active_propname,
                index,
            )
        self.current = previous


def addon_classes(base):
    """Registered subclasses of base defined by MustardUI."""
    found = []

    def walk(cls):
        for sub in cls.__subclasses__():
            if sub.__module__.startswith("bl_ext.user_default.MustardUI") and getattr(
                sub, "is_registered", False
            ):
                found.append(sub)
            walk(sub)

    walk(base)
    return list(dict.fromkeys(found))


def draw_all(context):
    drawer = Drawer()
    for cls in addon_classes(bpy.types.Panel):
        drawer.draw_panel(cls, context)
    return drawer
