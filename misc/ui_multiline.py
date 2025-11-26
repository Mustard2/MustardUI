import bpy
import textwrap


def label_multiline(context, text, parent, icon, pix=7):
    chars = int(context.region.width / pix)  # 7 pix on 1 character
    wrapper = textwrap.TextWrapper(width=chars)
    text_lines = wrapper.wrap(text=text)
    if icon in ["", "NONE"]:
        for i, text_line in enumerate(text_lines):
            parent.label(text=text_line)
    else:
        for i, text_line in enumerate(text_lines):
            if not i:
                parent.label(text=text_line, icon=icon)
            else:
                parent.label(text=text_line, icon="BLANK1")
