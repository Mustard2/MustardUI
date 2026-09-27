# Run inside Blender, with the add-on linked as extension user_default/MustardUI:
# blender --background --factory-startup --python-exit-code 1 --python tests/run.py [-- -k pattern]
import os
import sys
import unittest

import addon_utils
import bpy

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TESTS_DIR)

from helpers import ADDON  # noqa: E402


def main():
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []

    print(f"MustardUI tests - Blender {bpy.app.version_string}")
    if addon_utils.enable(ADDON, default_set=True, handle_error=None) is None:
        raise RuntimeError(f"Could not enable {ADDON}")

    loader = unittest.TestLoader()
    if "-k" in argv:
        loader.testNamePatterns = [f"*{argv[argv.index('-k') + 1]}*"]
    suite = loader.discover(TESTS_DIR, pattern="test_*.py", top_level_dir=TESTS_DIR)
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=2).run(suite)

    addon_utils.disable(ADDON, default_set=True, handle_error=None)

    if result.testsRun == 0 or not result.wasSuccessful():
        raise SystemExit(1)


main()
