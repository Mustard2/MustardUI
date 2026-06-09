# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

MustardUI is a **Blender Extension** (add-on) that generates an intuitive UI panel for human character models. It is pure Python using the `bpy` API; there is no separate build step — Blender loads the package directly. Target runtime is Blender **4.2.0+** (CI tests against 4.2, 4.5, and 5.1) on Python **3.12**.

## Commands

There is no compile/build for local development. Quality gates are enforced by Ruff (the only thing CI's `lint` job runs before the Blender build):

```bash
ruff check .            # lint (E, F, and I/isort rules — see pyproject.toml)
ruff format --check .   # verify formatting
ruff format .           # apply formatting
```

Both must pass; the Blender build matrix only runs after the lint job succeeds. `armature/external/mhx` is excluded from Ruff (vendored code).

To run the add-on, install the package as a Blender Extension in Blender itself — do **not** zip/distribute from a working checkout for end users (releases come from the Releases page / extensions.blender.org).

## Architecture

### Module = feature package, all wired through `register()`/`unregister()`

The top-level `__init__.py` imports every feature package (`outfits`, `hair`, `armature`, `physics`, `morphs`, `menu`, `settings`, etc.) and calls each one's `register()` in order, `unregister()` in reverse. **Every package and most sub-modules expose `register()`/`unregister()`** that call `bpy.utils.register_class()` on the Blender classes they define. When you add an operator, panel, or PropertyGroup, you must register it in the owning module's `register()` and tear it down in `unregister()` (reverse order), then ensure the package `__init__.py` includes that sub-module. Registration order matters — a module's data must be registered before another module references it.

### Where state lives: the Armature datablock

MustardUI attaches almost all model configuration to the model's **Armature data** (`bpy.types.Armature`), not to scene/object/window. Each feature group registers a PointerProperty there, e.g.:

- `Armature.MustardUI_RigSettings` (`settings/rig.py`) — outfits, hair, body collections, the core model config
- `Armature.MustardUI_MorphsSettings`, `MustardUI_PhysicsSettings`, `MustardUI_ToolsSettings`, `MustardUI_SimplifySettings`
- `Armature.MustardUI_enable` / `MustardUI_created` — whether the model is in user mode and whether it has ever been configured

Session-level (non-persistent UI) state lives on `Scene.MustardUI_Settings` (`settings/addon.py`), e.g. `viewport_model_selection` and the manually selected model armature. Addon-wide preferences are in `settings/addon_prefs.py`.

### Resolving "which model are we acting on": `mustardui_active_object`

`model_selection/active_object.py` is the single source of truth for figuring out the active model armature. **Operators and panels should call `mustardui_active_object(context, config=...)` rather than reaching into `context.active_object` directly.** It returns `(poll_result, armature)` and handles two selection modes (viewport-active-object vs. a panel-selected armature, including resolving a mesh to its armature via parent / armature modifier / Child Of constraint).

The `config` argument encodes both the mode and the poll meaning of the boolean:
- `config=0` — user mode; poll true when the model UI is enabled (`MustardUI_enable`)
- `config=1` — configuration mode; poll true when the model UI is **not** yet enabled (i.e. being configured)
- `config=2` — quick-setup mode (uninitialized armature)
- `config=-1` — return the armature regardless of state

Use `active_object_operator_poll(context, config=...)` in an operator's `poll()` classmethod for the standard gate (see any `ops_*.py`).

### Per-feature file naming conventions

Within a feature package, files follow consistent prefixes — match them when adding code:
- `ops_*.py` — one Blender `Operator` per file (sometimes a small group), `class MustardUI_<Verb><Noun>`, `bl_idname = "mustardui.<snake_case>"`, `bl_options = {"UNDO"}`
- `menu*.py` / `ui_list*.py` — `Panel` / `UIList` drawing code (the `menu/` top-level package assembles the full N-panel UI; per-feature `menu.py` draws that feature's section)
- `settings.py` / `settings_item.py` / `definitions.py` — the `PropertyGroup` data models for that feature
- User-facing operator messages are prefixed `"MustardUI - ..."` via `self.report(...)`

### Configuration vs. user mode

The add-on has two faces: a **Configuration** UI (model creators build the panel with no code) and the **user** UI. Many operators are config-only and gate on `config=1`. Keep this split in mind — a feature usually has both a configure-side panel (`menu/menu_configure_*.py`) and a user-side panel.

## Conventions & contribution rules

- `main` must stay **linear** — PRs are merged with **Squash and Merge**, no merge commits (see `Contributing.md`).
- Version lives in three places that must stay in sync on release: `blender_manifest.toml` (`version`), `__init__.py` (`bl_info["version"]` tuple), and the git branch name (e.g. `2026.6.0`).
- Do not post NSFW Blender files/images/videos in Issues or PRs.
- Creator-facing tools live in `tools_creators/` (physics cages, bone physics, Spline IK rigs, etc.); end-user animator tools in `tools/`.