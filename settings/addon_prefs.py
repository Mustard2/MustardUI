import bpy
from bpy.props import *
from ..model_selection.active_object import *
from .. import __package__ as base_package


class MustardUI_AddonPrefs(bpy.types.AddonPreferences):
    bl_idname = base_package

    def developer_update(self, context):
        if not self.developer:
            self.debug = False
        for arm in [x for x in bpy.data.armatures]:
            if not arm.MustardUI_enable and arm.MustardUI_created and not self.developer:
                arm.MustardUI_enable = True

    # Maintenance tools
    developer: BoolProperty(default=False,
                            name="Developer Tools",
                            description="Enable Developer Tools.\nVarious developer tools will be "
                                        "added to the UI and in the Settings panel",
                            update=developer_update)

    # Debug mode
    debug: BoolProperty(default=False,
                        name="Debug Mode",
                        description="Unlock Debug Mode.\nMore messaged will be generated in the "
                                    "console.\nEnable it only if you encounter problems, as it might "
                                    "degrade general Blender performance")

    # Experimental features
    experimental: BoolProperty(default=False,
                               name="Experimental Features",
                               description="Unlock experimental features throughout the add-on.\nNote that "
                                           "experimental features might not work properly yet, or be changed/removed "
                                           "from future versions")

    url_MustardUI = "https://github.com/Mustard2/MustardUI"
    url_MustardUI_ReportBug = "https://github.com/Mustard2/MustardUI/issues"
    url_MustardUI_Tutorial = "https://github.com/Mustard2/MustardUI/wiki/Tutorial"

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)
        col.prop(self, "developer")
        row = col.row()
        row.enabled = self.developer
        row.prop(self, "debug")
        # col.separator()
        # row2 = col.row()
        # row2.enabled = False
        # row2.prop(self, "experimental")

        if self.debug:
            layout.operator('mustardui.fix_missing_ui', icon="MOD_BUILD")

        row = layout.row(align=True)
        row.operator('mustardui.openlink', text="GitHub", icon="URL").url = self.url_MustardUI
        row.operator('mustardui.openlink', text="Tutorial",
                     icon="URL").url = self.url_MustardUI_Tutorial
        row.operator('mustardui.openlink', text="Report Bug",
                     icon="URL").url = self.url_MustardUI_ReportBug


def register():
    bpy.utils.register_class(MustardUI_AddonPrefs)


def unregister():
    bpy.utils.unregister_class(MustardUI_AddonPrefs)
