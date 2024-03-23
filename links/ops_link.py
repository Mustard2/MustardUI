import bpy
import webbrowser


# ------------------------------------------------------------------------
#    Link (thanks to Mets3D)
# ------------------------------------------------------------------------

class MustardUI_LinkButton(bpy.types.Operator):
    """Open links in a web browser"""
    bl_idname = "mustardui.openlink"
    bl_label = "Open Link"
    bl_options = {'REGISTER'}

    url: bpy.props.StringProperty(name='URL',
                                  description="URL",
                                  default="http://blender.org/"
                                  )

    def execute(self, context):
        webbrowser.get().open_new(self.url)  # opens in default browser
        return {'FINISHED'}


def register():
    bpy.utils.register_class(MustardUI_LinkButton)


def unregister():
    bpy.utils.unregister_class(MustardUI_LinkButton)
