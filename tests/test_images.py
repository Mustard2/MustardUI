import hashlib
import importlib
import os
import tempfile

import bpy
import numpy as np
from helpers import ADDON, BlenderTestCase, build_model, configure_model

convert_images = importlib.import_module(ADDON + ".model_toolkit.optimization.ops_convert_images")


def srgb_encode(x):
    return np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(np.maximum(x, 0), 1 / 2.4) - 0.055)


def file_hash(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def raw_pixels(image):
    """Pixel values as stored in the file, without color and alpha conversions"""
    if image.packed_file is not None:
        copy = image.copy()
    else:
        copy = bpy.data.images.load(image.filepath, check_existing=False)
    copy.colorspace_settings.name = "Non-Color"
    copy.alpha_mode = "CHANNEL_PACKED"
    pixels = np.empty(len(copy.pixels), dtype=np.float32)
    copy.pixels.foreach_get(pixels)
    width, height = copy.size
    bpy.data.images.remove(copy)
    return pixels.reshape(height, width, 4)


class TestConvertImages(BlenderTestCase):
    def setUp(self):
        super().setUp()
        self.dir = tempfile.TemporaryDirectory()
        self.model = build_model()
        self.rig_settings = configure_model(self.model)
        self.tree = self.model["body"].data.materials[0].node_tree
        # Model in configuration mode, for the Model Toolkit
        bpy.ops.mustardui.configuration()

        # Random 8 x 8 blocks, with some transparent pixels
        rng = np.random.default_rng(0)
        blocks = rng.random((2, 256, 4), dtype=np.float32)
        blocks[:, ::3, 3] = 1.0
        blocks[:, 1::3, 3] = 0.5
        self.pixels = blocks.repeat(8, 0).repeat(8, 1)

    def tearDown(self):
        self.dir.cleanup()
        super().tearDown()

    def new_image(self, name, file_format, depth, colorspace="sRGB", tree=None):
        """Image file of 2048 x 16 pixels used by an Image Texture node"""
        height, width = self.pixels.shape[:2]
        image = bpy.data.images.new(name, width, height, alpha=True, float_buffer=True)
        image.colorspace_settings.name = "Non-Color"
        image.alpha_mode = "CHANNEL_PACKED"
        image.pixels.foreach_set(self.pixels.ravel())
        settings = bpy.context.scene.render.image_settings
        settings.file_format = file_format
        settings.color_depth = depth
        settings.color_mode = "RGB" if file_format == "JPEG" else "RGBA"
        path = os.path.join(self.dir.name, name)
        image.save_render(path)
        bpy.data.images.remove(image)

        image = bpy.data.images.load(path)
        image.colorspace_settings.name = colorspace
        (tree or self.tree).nodes.new("ShaderNodeTexImage").image = image
        return image

    def convert(self, *images, **kwargs):
        items = [
            {
                "name": x.name,
                "convert": True,
                "width": x.size[0],
                "height": x.size[1],
                "is_float": x.is_float,
                "file_format": x.file_format,
                "packed": x.packed_file is not None,
            }
            for x in images
        ]
        bpy.ops.mustardui.model_toolkit_convert_images(images=items, min_size="0", **kwargs)

    def node_images(self, tree=None):
        return [n.image for n in (tree or self.tree).nodes if n.type == "TEX_IMAGE"]

    def files(self):
        return {x: file_hash(os.path.join(self.dir.name, x)) for x in os.listdir(self.dir.name)}

    # 16-bit Image converted to 8-bit, saved next to the original with a new name
    def test_to_8bit(self):
        image = self.new_image("color.png", "PNG", "16")
        self.assertTrue(image.is_float)
        source = raw_pixels(image)
        before = self.files()

        self.convert(image, max_size="0")

        (new_image,) = self.node_images()
        self.assertNotIn("color.png", bpy.data.images)
        self.assertEqual(new_image.filepath, os.path.join(self.dir.name, "color_8bit.png"))
        self.assertFalse(new_image.is_float)
        self.assertEqual(new_image.colorspace_settings.name, "sRGB")
        self.assertEqual(tuple(new_image.size), (2048, 16))
        self.assertLess(np.abs(raw_pixels(new_image) - source).max(), 0.6 / 255)
        # Original file untouched
        self.assertEqual(self.files(), before | {"color_8bit.png": self.files()["color_8bit.png"]})

    # Existing files and Images are never overwritten
    def test_unique_names(self):
        image = self.new_image("color.png", "PNG", "16")
        open(os.path.join(self.dir.name, "color_8bit.png"), "wb").write(b"old")
        other = bpy.data.images.new("other", 4, 4)
        other.filepath_raw = os.path.join(self.dir.name, "color_8bit_001.png")
        before = self.files()

        self.convert(image)

        (new_image,) = self.node_images()
        self.assertEqual(new_image.filepath, os.path.join(self.dir.name, "color_8bit_002.png"))
        after = self.files()
        self.assertEqual({x: after[x] for x in before}, before)

    # Resized 16-bit Images keep their bit depth and transparent pixels colors
    def test_resize_keep_bits(self):
        for colorspace in ("sRGB", "Non-Color"):
            with self.subTest(colorspace=colorspace):
                image = self.new_image(f"{colorspace}.png", "PNG", "16", colorspace=colorspace)
                image.alpha_mode = "CHANNEL_PACKED"
                source = raw_pixels(image)

                self.convert(image, max_size="1024", to_8bit=False)

                new_image = self.node_images()[-1]
                self.assertEqual(os.path.basename(new_image.filepath), f"{colorspace}_1k.png")
                self.assertTrue(new_image.is_float)
                self.assertEqual(new_image.colorspace_settings.name, colorspace)
                self.assertEqual(new_image.alpha_mode, "CHANNEL_PACKED")
                self.assertEqual(tuple(new_image.size), (1024, 8))
                # Inner pixels of the 4 x 4 blocks
                result = raw_pixels(new_image)[1::4, 1::4]
                self.assertLess(np.abs(result - source[2::8, 2::8]).max(), 1e-3)

    # New Images saved in a subfolder, also in the path of the packed ones
    def test_subfolder(self):
        image = self.new_image("color.png", "PNG", "16")
        packed = self.new_image("packed.png", "PNG", "16")
        packed.pack()
        os.remove(packed.filepath)
        packed.filepath_raw = "//textures/packed.png"

        self.convert(image, packed, use_subfolder=True, subfolder="Converted")

        new_image, new_packed = self.node_images()
        path = os.path.join(self.dir.name, "Converted", "color_8bit.png")
        self.assertEqual(new_image.filepath, path)
        self.assertTrue(os.path.isfile(path))
        self.assertEqual(new_packed.filepath, "//textures/Converted/packed_8bit.png")
        self.assertIsNotNone(new_packed.packed_file)
        self.assertEqual(sorted(os.listdir(self.dir.name)), ["Converted", "color.png"])

    # Linear float Image converted to 8-bit is stored in sRGB
    def test_linear_to_8bit(self):
        image = self.new_image("height.exr", "OPEN_EXR", "32", colorspace="Linear Rec.709")
        source = raw_pixels(image)

        self.convert(image, max_size="0")

        (new_image,) = self.node_images()
        self.assertEqual(os.path.basename(new_image.filepath), "height_8bit.png")
        self.assertEqual(new_image.colorspace_settings.name, "sRGB")
        expected = source.copy()
        expected[..., :3] = srgb_encode(np.minimum(source[..., :3], 1.0))
        self.assertLess(np.abs(raw_pixels(new_image) - expected).max(), 0.6 / 255)

    # Packed Image in a node group is replaced by a new packed Image, without files on disk
    def test_packed(self):
        group = bpy.data.node_groups.new("Group", "ShaderNodeTree")
        self.tree.nodes.new("ShaderNodeGroup").node_tree = group
        image = self.new_image("packed.png", "PNG", "16", tree=group)
        image.pack()
        packed_data = image.packed_file.data
        os.remove(image.filepath)
        image.filepath_raw = "//textures/packed.png"
        source = raw_pixels(image)

        self.convert(image, max_size="1024")

        (new_image,) = self.node_images(group)
        self.assertEqual(new_image.name, "packed_1k_8bit.png")
        self.assertEqual(new_image.filepath, "//textures/packed_1k_8bit.png")
        self.assertEqual(new_image.packed_files[0].filepath, new_image.filepath)
        self.assertIsNotNone(new_image.packed_file)
        self.assertNotIn("packed.png", bpy.data.images)
        self.assertEqual(self.files(), {})
        self.assertEqual(tuple(new_image.size), (1024, 8))
        result = raw_pixels(new_image)[1::4, 1::4]
        self.assertLess(np.abs(result - source[2::8, 2::8]).max(), 0.6 / 255)
        self.assertNotEqual(new_image.packed_file.data, packed_data)

    # Images used elsewhere are kept, and 8-bit Images are only resized
    def test_shared_and_8bit(self):
        image = self.new_image("photo.jpg", "JPEG", "8")
        other = bpy.data.materials.new("Other")
        other.use_nodes = True
        other.node_tree.nodes.new("ShaderNodeTexImage").image = image

        self.convert(image, max_size="0")
        self.assertEqual(self.node_images(), [image])

        self.convert(image, max_size="1024")
        (new_image,) = self.node_images()
        self.assertEqual(os.path.basename(new_image.filepath), "photo_1k.jpg")
        self.assertEqual(new_image.file_format, "JPEG")
        self.assertIn(image.name, bpy.data.images)

    # Images converted to another format, JPG ones also to 8-bit
    def test_output_format(self):
        targa = self.new_image("color.tga", "TARGA", "8")
        self.convert(targa, max_size="0", output_format="KEEP")
        self.assertEqual(self.node_images(), [targa])

        source = raw_pixels(targa)
        self.convert(targa, max_size="0", output_format="PNG")
        png = self.node_images()[0]
        self.assertEqual(os.path.basename(png.filepath), "color.png")
        self.assertEqual(png.file_format, "PNG")
        self.assertLess(np.abs(raw_pixels(png) - source).max(), 1e-6)

        image = self.new_image("data.png", "PNG", "16")
        self.convert(image, max_size="0", to_8bit=False, output_format="JPEG")
        jpg = self.node_images()[-1]
        self.assertEqual(os.path.basename(jpg.filepath), "data_8bit.jpg")
        self.assertEqual(jpg.file_format, "JPEG")
        self.assertFalse(jpg.is_float)
        self.assertEqual(tuple(jpg.size), (2048, 16))

    # Size and bit depth of PNG and JPEG files read without loading the Images
    def test_header_info(self):
        images = [
            self.new_image("color16.png", "PNG", "16"),
            self.new_image("color8.png", "PNG", "8"),
            self.new_image("photo.jpg", "JPEG", "8"),
        ]
        images[1].pack()
        for image in images:
            with self.subTest(image=image.name):
                image.buffers_free()
                info = convert_images.header_info(image)
                self.assertFalse(image.has_data)
                self.assertEqual(info, (*image.size, image.is_float, image.file_format))

        self.assertIsNone(
            convert_images.header_info(self.new_image("height.exr", "OPEN_EXR", "32"))
        )
        missing = bpy.data.images.load(images[0].filepath, check_existing=False)
        missing.filepath_raw = os.path.join(self.dir.name, "missing.png")
        self.assertIsNone(convert_images.header_info(missing))

    def test_filters(self):
        props = bpy.context.window_manager.operator_properties_last(
            "mustardui.model_toolkit_convert_images"
        )
        item = props.images.add()
        item.file_format = "PNG"
        for width, is_float, min_size, min_bits, format_filter, listed in (
            (4096, False, "4096", "8", "ANY", True),
            (2048, False, "4096", "8", "ANY", False),
            (4096, False, "4096", "16", "ANY", False),
            (4096, True, "4096", "16", "ANY", True),
            (512, True, "0", "16", "ANY", True),
            (4096, False, "4096", "8", "PNG", True),
            (4096, False, "4096", "8", "JPG", False),
        ):
            item.width, item.height, item.is_float = width, 16, is_float
            props.min_size, props.min_bits = min_size, min_bits
            props.format_filter = format_filter
            self.assertEqual(convert_images.listed(item, props), listed)
