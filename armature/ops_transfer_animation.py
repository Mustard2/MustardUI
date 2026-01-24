import bpy


class MustardUI_Armature_TransferAnimation(bpy.types.Operator):
    """Copy all animation data and world transform from one armature to another"""
    bl_idname = "mustardui.armature_transfer_animation"
    bl_label = "Transfer Animation To Active"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        sel = context.selected_objects
        target = context.active_object

        if len(sel) != 2:
            return False

        source = sel[0] if sel[1] == target else sel[1]

        if source.type != 'ARMATURE' or target.type != 'ARMATURE':
            return False

        return True

    def execute(self, context):
        sel = context.selected_objects
        target = context.active_object

        if len(sel) != 2:
            self.report({'ERROR'}, "Select exactly two armatures")
            return {'CANCELLED'}

        source = sel[0] if sel[1] == target else sel[1]

        if source.type != 'ARMATURE' or target.type != 'ARMATURE':
            self.report({'ERROR'}, "Both objects must be armatures")
            return {'CANCELLED'}

        # Copy WORLD transform
        target.matrix_world = source.matrix_world.copy()

        # Animation data
        if not source.animation_data:
            self.report({'WARNING'}, "Source armature has no animation data")
            return {'CANCELLED'}

        if not target.animation_data:
            target.animation_data_create()

        src_ad = source.animation_data
        tgt_ad = target.animation_data

        # Clear target animation data
        tgt_ad.action = None

        while tgt_ad.nla_tracks:
            tgt_ad.nla_tracks.remove(tgt_ad.nla_tracks[0])

        # Active action
        if src_ad.action:
            tgt_ad.action = src_ad.action.copy()

        # NLA tracks
        for src_track in src_ad.nla_tracks:
            tgt_track = tgt_ad.nla_tracks.new()
            tgt_track.name = src_track.name
            tgt_track.mute = src_track.mute
            tgt_track.lock = src_track.lock

            for src_strip in src_track.strips:
                new_action = src_strip.action.copy()

                tgt_strip = tgt_track.strips.new(
                    name=src_strip.name,
                    start=int(src_strip.frame_start),
                    action=new_action
                )

                tgt_strip.frame_end = src_strip.frame_end
                tgt_strip.blend_type = src_strip.blend_type
                tgt_strip.extrapolation = src_strip.extrapolation
                tgt_strip.influence = src_strip.influence
                tgt_strip.mute = src_strip.mute
                tgt_strip.use_reverse = src_strip.use_reverse
                tgt_strip.use_sync_length = src_strip.use_sync_length

        self.report({'INFO'}, f"MustardUI - Animation transferred from '{source.name}' to '{target.name}'")
        return {'FINISHED'}


def register():
    bpy.utils.register_class(MustardUI_Armature_TransferAnimation)


def unregister():
    bpy.utils.unregister_class(MustardUI_Armature_TransferAnimation)
