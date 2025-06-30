import bpy
import sys


def musdtardui_error_print(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)
