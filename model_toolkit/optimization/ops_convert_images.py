import os
import tempfile

import bpy
import numpy as np
from bpy.props import BoolProperty, CollectionProperty, EnumProperty, IntProperty, StringProperty

from ...misc.materials import model_node_trees
from ...model_selection.active_object import (
    ModelMode,
    active_object_operator_poll,
    mustardui_active_object,
)

sizes = (1024, 2048, 4096, 8192, 16384)


def listed(item, props):
    """Whether the Image passes the size and bit depth filters"""
    return max(item.width, item.height) >= int(props.min_size) and (
        item.is_float or props.min_bits == "8"
    )


def unique_path(stem, ext):
    """Path not used by any file on disk or any Image in the file"""

    used = {os.path.normpath(bpy.path.abspath(x.filepath)) for x in bpy.data.images if x.filepath}

    path, i = stem + ext, 0
    while (full := os.path.normpath(bpy.path.abspath(path))) in used or os.path.exists(full):
        i += 1
        path = f"{stem}_{i:03d}{ext}"

    return path


class MustardUI_ConvertImages_Item(bpy.types.PropertyGroup):
    """Image found by the Convert Images tool"""

    convert: BoolProperty(default=True, name="Convert", description="Convert this Image")
    width: IntProperty()
    height: IntProperty()
    is_float: BoolProperty()
    packed: BoolProperty()


class MUSTARDUI_UL_ConvertImages_UIList(bpy.types.UIList):
    """UIList of the Images to convert"""

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row(align=True)
        row.prop(item, "convert", text="")
        row.label(text=item.name, icon="PACKAGE" if item.packed else "IMAGE_DATA")
        memory = item.width * item.height * (16 if item.is_float else 4) / 1024**2
        # Fixed width columns
        for text, width in (
            (f"{item.width} x {item.height}", 5),
            ("16/32-bit" if item.is_float else "8-bit", 4),
            (f"{memory:.0f} MB", 4),
        ):
            column = row.row()
            column.alignment = "RIGHT"
            column.ui_units_x = width
            column.label(text=text)

    def filter_items(self, context, data, propname):
        return [self.bitflag_filter_item * listed(x, data) for x in getattr(data, propname)], []


class MustardUI_ModelToolkit_ConvertImages(bpy.types.Operator):
    """List the heaviest Images of the model, and convert them to a lower resolution or bit depth.
    The converted Images are saved with new names, or packed if the original was packed"""

    bl_idname = "mustardui.model_toolkit_convert_images"
    bl_label = "Convert Images"
    bl_options = {"UNDO"}

    images: CollectionProperty(type=MustardUI_ConvertImages_Item, options={"SKIP_SAVE"})
    images_index: IntProperty(default=0, options={"SKIP_SAVE"})

    min_size: EnumProperty(
        name="Size",
        items=[("0", "Any", "Any size")]
        + [(str(s), f"{s // 1024}K or above", f"{s} x {s} or above") for s in sizes[1:]],
        default="4096",
        description="List the Images with this resolution or above",
    )
    min_bits: EnumProperty(
        name="Bit Depth",
        items=[
            ("8", "Any", "Any bit depth"),
            ("16", "16-bit or above", "Float Images, which use 4 times the memory of 8-bit ones"),
        ],
        default="8",
        description="List the Images with this bit depth or above",
    )
    max_size: EnumProperty(
        name="Resize To",
        items=[("0", "Keep", "Keep the resolution")]
        + [(str(s), f"{s // 1024}K", f"{s} x {s}") for s in sizes],
        default="2048",
        description="Downscale the Images larger than this resolution",
    )
    to_8bit: BoolProperty(
        name="Convert to 8-bit",
        default=True,
        description="Convert the 16 and 32-bit Images to 8-bit",
    )
    use_subfolder: BoolProperty(
        name="Save in Subfolder",
        default=False,
        description="Save the new Images in a subfolder of the original Images folder",
    )
    subfolder: StringProperty(
        name="Subfolder",
        default="Converted",
        description="Name of the subfolder for the new Images",
    )

    @classmethod
    def poll(cls, context):
        return active_object_operator_poll(context, config=ModelMode.MODEL_TOOLKIT)

    def invoke(self, context, event):

        res, arm = mustardui_active_object(context, config=ModelMode.MODEL_TOOLKIT)

        images = {
            node.image
            for tree in model_node_trees(arm.MustardUI_RigSettings)
            for node in tree.nodes
            if node.type == "TEX_IMAGE" and node.image is not None and node.image.source == "FILE"
        }

        found = []
        wm = context.window_manager
        wm.progress_begin(0, len(images))
        for i, image in enumerate(images):
            wm.progress_update(i)
            # Reading the size loads the Image
            loaded = image.has_data
            width, height = image.size
            if width and height:
                found.append((image, width, height, image.is_float))
            if not loaded:
                image.buffers_free()
        wm.progress_end()

        # Heaviest first
        for image, width, height, is_float in sorted(
            found, key=lambda x: -x[1] * x[2] * (4 if x[3] else 1)
        ):
            item = self.images.add()
            item.name = image.name
            item.width = width
            item.height = height
            item.is_float = is_float
            item.packed = image.packed_file is not None

        if not self.images:
            self.report({"INFO"}, "MustardUI - No Images found")
            return {"CANCELLED"}

        return wm.invoke_props_dialog(self, width=600, confirm_text="Convert")

    def convert(self, image, scene, tempdir):
        """Converted copy of the Image, or None if there is nothing to convert"""

        width, height = image.size
        max_size = int(self.max_size)
        scale = min(1.0, max_size / max(width, height)) if max_size else 1.0
        to_8bit = self.to_8bit and image.is_float
        if scale == 1.0 and not to_8bit:
            return None

        if image.is_float and not to_8bit:
            file_format, depth, ext = (
                ("OPEN_EXR", "32", ".exr")
                if image.file_format == "OPEN_EXR"
                else ("PNG", "16", ".png")
            )
        elif image.file_format == "JPEG":
            file_format, depth, ext = "JPEG", "8", ".jpg"
        else:
            file_format, depth, ext = "PNG", "8", ".png"

        # Name with the new resolution and bit depth, next to the original file
        folder, filename = os.path.split(image.filepath)
        if self.use_subfolder and self.subfolder.strip():
            folder = os.path.join(folder, self.subfolder.strip())
        suffix = f"_{max_size // 1024}k" if scale < 1.0 else ""
        suffix += "_8bit" if to_8bit else ""
        stem = os.path.splitext(filename or image.name)[0] + suffix
        path = unique_path(os.path.join(folder, stem), ext)

        # Channel Packed to keep the color of transparent pixels as they are
        work = image.copy()
        work.alpha_mode = "CHANNEL_PACKED"
        # Pixels are written as they are, except for 8-bit color Images stored in sRGB
        colorspace = image.colorspace_settings.name
        if image.colorspace_settings.is_data or depth != "8":
            work.colorspace_settings.name = "Non-Color"
        else:
            colorspace = "sRGB"
        if scale < 1.0:
            work.scale(max(1, round(width * scale)), max(1, round(height * scale)))
        if depth == "16":
            # The 16-bit PNG writer un-premultiplies float pixels
            pixels = np.empty(len(work.pixels), dtype=np.float32)
            work.pixels.foreach_get(pixels)
            pixels = pixels.reshape(-1, 4)
            pixels[:, :3] *= pixels[:, 3:]
            work.pixels.foreach_set(pixels.ravel())

        settings = scene.render.image_settings
        settings.file_format = file_format
        settings.color_depth = depth
        settings.color_mode = "RGB" if file_format == "JPEG" else "RGBA"
        settings.quality = 95

        packed = image.packed_file is not None
        # Packed Images are written to a temporary file, then packed
        if packed:
            filepath = os.path.join(tempdir, os.path.basename(path))
        else:
            filepath = bpy.path.abspath(path)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
        try:
            work.save_render(filepath, scene=scene)
        finally:
            bpy.data.images.remove(work)

        new_image = bpy.data.images.load(filepath, check_existing=False)
        new_image.name = os.path.basename(path)
        new_image.alpha_mode = image.alpha_mode
        new_image.colorspace_settings.name = colorspace

        if packed:
            new_image.pack()
            new_image.packed_files[0].filepath = path
        new_image.filepath_raw = path

        return new_image

    def execute(self, context):

        res, arm = mustardui_active_object(context, config=ModelMode.MODEL_TOOLKIT)

        images = [
            bpy.data.images[x.name]
            for x in self.images
            if x.convert and listed(x, self) and x.name in bpy.data.images
        ]

        # Temporary Scene with the output settings, to save without the scene look
        scene = bpy.data.scenes.new("MustardUI Convert Images")
        scene.display_settings.display_device = "sRGB"
        scene.view_settings.view_transform = "Standard"

        converted = {}
        wm = context.window_manager
        wm.progress_begin(0, len(images))
        try:
            with tempfile.TemporaryDirectory() as tempdir:
                for i, image in enumerate(images):
                    wm.progress_update(i)
                    new_image = self.convert(image, scene, tempdir)
                    if new_image is not None:
                        converted[image] = new_image
        except (OSError, RuntimeError) as e:
            self.report({"ERROR"}, f"MustardUI - Can not convert the Images: {e}")
        finally:
            bpy.data.scenes.remove(scene)
            wm.progress_end()

        for tree in model_node_trees(arm.MustardUI_RigSettings):
            for node in tree.nodes:
                if node.type == "TEX_IMAGE" and node.image in converted:
                    node.image = converted[node.image]

        for image in converted:
            if not image.users:
                bpy.data.images.remove(image)

        self.report({"INFO"}, f"MustardUI - {len(converted)} Images converted")

        return {"FINISHED"}

    def draw(self, context):

        layout = self.layout

        row = layout.row()
        row.prop(self, "min_size")
        row.prop(self, "min_bits")

        layout.template_list(
            "MUSTARDUI_UL_ConvertImages_UIList",
            "",
            self,
            "images",
            self,
            "images_index",
        )

        row = layout.row()
        row.prop(self, "max_size")
        row.prop(self, "to_8bit")

        row = layout.row()
        row.prop(self, "use_subfolder")
        sub = row.row()
        sub.enabled = self.use_subfolder
        sub.prop(self, "subfolder", text="")


def register():
    bpy.utils.register_class(MustardUI_ConvertImages_Item)
    bpy.utils.register_class(MUSTARDUI_UL_ConvertImages_UIList)
    bpy.utils.register_class(MustardUI_ModelToolkit_ConvertImages)


def unregister():
    bpy.utils.unregister_class(MustardUI_ModelToolkit_ConvertImages)
    bpy.utils.unregister_class(MUSTARDUI_UL_ConvertImages_UIList)
    bpy.utils.unregister_class(MustardUI_ConvertImages_Item)
