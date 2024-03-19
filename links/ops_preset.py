import bpy
from ..model_selection.active_object import *
from bpy_extras.io_utils import ExportHelper, ImportHelper
from bpy.props import *
from bpy.utils import register_class
import json


# ------------------------------------------------------------------------
#    Link presets
# ------------------------------------------------------------------------


class MustardUI_Links_Export(bpy.types.Operator, ExportHelper):
    """Export Links to json file"""
    bl_idname = 'mustardui.link_export'
    bl_label = 'Export Links'
    bl_options = {'PRESET', 'UNDO'}

    filename_ext = '.json'

    filter_glob: StringProperty(
        default='*.json',
        options={'HIDDEN'}
    )

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=1)
        addon_prefs = context.preferences.addons["MustardUI"].preferences
        return res and addon_prefs.developer

    def execute(self, context):

        res, arm = mustardui_active_object(context, config=1)

        if len(arm.MustardUI_Links) < 1:
            self.report({'WARNING'}, 'MustardUI - No link to export.')
            return {'FINISHED'}

        data = []
        for link in arm.MustardUI_Links:
            data.append({"name": link.name, "url": link.url})

        with open(self.filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        self.report({'INFO'}, 'MustardUI - Links Exported.')

        return {'FINISHED'}

    def draw(self, context):
        pass


class MustardUI_Links_Import(bpy.types.Operator, ImportHelper):
    """Import Links from json file"""
    bl_idname = 'mustardui.link_import'
    bl_label = 'Import Links'
    bl_options = {'PRESET', 'UNDO'}

    filename_ext = '.json'

    filter_glob: StringProperty(
        default='*.json',
        options={'HIDDEN'}
    )

    replace_links: BoolProperty(
        default=False,
        name="Replace links",
        description="Replace current links"
    )

    @classmethod
    def poll(cls, context):
        res, arm = mustardui_active_object(context, config=1)
        addon_prefs = context.preferences.addons["MustardUI"].preferences
        return res and addon_prefs.developer

    def execute(self, context):
        res, arm = mustardui_active_object(context, config=1)
        uilist = arm.MustardUI_Links

        n_import = 0

        try:
            if self.replace_links:
                uilist.clear()

            with open(self.filepath, "r", encoding='utf-8') as f:
                links_loaded = json.load(f)

                for link in links_loaded:
                    a = uilist.add()
                    a.name = link["name"]
                    a.url = link["url"]
                    n_import = n_import + 1

                index = len(uilist) - 1
                context.scene.mustardui_links_uilist_index = index

        except:
           self.report({'ERROR'}, 'MustardUI - Link file seems corrupted.')
           return {'FINISHED'}

        arm.update_tag()

        self.report({'INFO'}, 'MustardUI - ' + str(n_import) + ' links Imported.')

        return {'FINISHED'}


def register():
    bpy.utils.register_class(MustardUI_Links_Export)
    bpy.utils.register_class(MustardUI_Links_Import)


def unregister():
    bpy.utils.unregister_class(MustardUI_Links_Import)
    bpy.utils.unregister_class(MustardUI_Links_Export)
