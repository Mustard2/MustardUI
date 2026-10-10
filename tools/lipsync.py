import functools
import gzip
import os
import re
from collections import defaultdict
from typing import Callable, NamedTuple

import bpy
import numpy as np

from ..model_selection.active_object import (
    ModelMode,
    active_object_operator_poll,
    mustardui_active_object,
)
from ..morphs.misc import get_cp_source

# Logical visemes; the target name is the configured prefix + viseme
VISEMES = (
    "AA",
    "EE",
    "EH",
    "ER",
    "F",
    "IH",
    "IY",
    "K",
    "L",
    "M",
    "OW",
    "S",
    "SH",
    "T",
    "TH",
    "UW",
    "W",
)

# ARPABET phoneme -> logical viseme
ARPA2VIS = {
    # Vowels / diphthongs
    "AA": "AA",
    "AE": "AA",
    "AH": "AA",
    "AX": "AA",
    "AO": "OW",
    "AW": "AA",
    "AY": "AA",
    "EH": "EH",
    "ER": "ER",
    "EY": "EE",
    "IH": "IH",
    "IY": "IY",
    "OW": "OW",
    "OY": "OW",
    "UH": "UW",
    "UW": "UW",
    # Consonants
    "B": "M",
    "P": "M",
    "M": "M",
    "F": "F",
    "V": "F",
    "TH": "TH",
    "DH": "TH",
    "T": "T",
    "D": "T",
    "N": "T",
    "L": "L",
    "K": "K",
    "G": "K",
    "NG": "K",
    "S": "S",
    "Z": "S",
    "SH": "SH",
    "ZH": "SH",
    "CH": "SH",
    "JH": "SH",
    "R": "ER",
    "W": "W",
    "Y": "IY",
    "HH": "AA",
}

# Peak strength per viseme (before intensity)
PEAK = {
    "M": 1.00,
    "F": 0.90,
    "W": 0.95,
    "UW": 0.95,
    "OW": 0.90,
    "AA": 1.00,
    "EE": 0.90,
    "IY": 0.85,
    "IH": 0.70,
    "EH": 0.80,
    "ER": 0.80,
    "S": 0.65,
    "SH": 0.85,
    "TH": 0.80,
    "T": 0.55,
    "L": 0.70,
    "K": 0.55,
}
DEFAULT_PEAK = 0.80

# Phoneme durations (seconds, before speed scaling)
BASE_DUR = 0.090
PLOSIVES = {"P", "B", "T", "D", "K", "G"}
AFFRICATES = {"CH", "JH"}
FRICATIVES = {"F", "V", "TH", "DH", "S", "Z", "SH", "ZH", "HH"}
NASALS = {"M", "N", "NG"}
APPROX = {"L", "R", "W", "Y"}
DIPHTHONGS = {"AW", "AY", "EY", "OY", "OW"}
VOWELS = {
    "AA",
    "AE",
    "AH",
    "AO",
    "AW",
    "AX",
    "AY",
    "EH",
    "ER",
    "EY",
    "IH",
    "IY",
    "OW",
    "OY",
    "UH",
    "UW",
}

# Duration factors by phoneme group, the first matching one is used
DUR_FACTORS = (
    (PLOSIVES, 0.60),
    (AFFRICATES, 0.90),
    (FRICATIVES, 1.10),
    (NASALS | APPROX, 0.90),
    (DIPHTHONGS, 1.70),
    (VOWELS, 1.35),
)

WORD_GAP = 0.070
SENT_GAP = 0.240

# Smoothing resample rate in Hz (0 = scene fps) and key reduction tolerance
SMOOTH_RATE = 0
SMOOTH_TOL = 0.008

_STRESS = re.compile(r"\d+$")


# ------------------------------------------------------------------------
#    Text -> ARPABET
# ------------------------------------------------------------------------


_CMUDICT_PATH = os.path.join(os.path.dirname(__file__), "resources", "cmudict.gz")


@functools.cache
def _cmu_dict():
    """CMU Pronouncing Dictionary: word -> ARPABET phonemes"""
    with gzip.open(_CMUDICT_PATH, "rt", encoding="utf-8") as f:
        lines = (line.rstrip("\n").partition(" ") for line in f)
        return {word: phones.split() for word, _, phones in lines}


# Fallback speller rules (longest patterns first)
_FALLBACK_RULES = [
    ("tion", ["SH", "AH", "N"]),
    ("sion", ["ZH", "AH", "N"]),
    ("tch", ["CH"]),
    ("igh", ["AY"]),
    ("ch", ["CH"]),
    ("sh", ["SH"]),
    ("th", ["TH"]),
    ("ph", ["F"]),
    ("wh", ["W"]),
    ("ck", ["K"]),
    ("ng", ["NG"]),
    ("qu", ["K", "W"]),
    ("ee", ["IY"]),
    ("ea", ["IY"]),
    ("oo", ["UW"]),
    ("ou", ["AW"]),
    ("ow", ["OW"]),
    ("oi", ["OY"]),
    ("oy", ["OY"]),
    ("ai", ["EY"]),
    ("ay", ["EY"]),
    ("ei", ["EY"]),
    ("ey", ["EY"]),
    ("au", ["AO"]),
    ("aw", ["AO"]),
    ("ar", ["AA", "R"]),
    ("or", ["AO", "R"]),
    ("er", ["ER"]),
    ("ir", ["ER"]),
    ("ur", ["ER"]),
    ("a", ["AE"]),
    ("e", ["EH"]),
    ("i", ["IH"]),
    ("o", ["AA"]),
    ("u", ["AH"]),
    ("y", ["IH"]),
    ("b", ["B"]),
    ("d", ["D"]),
    ("f", ["F"]),
    ("g", ["G"]),
    ("h", ["HH"]),
    ("j", ["JH"]),
    ("k", ["K"]),
    ("l", ["L"]),
    ("m", ["M"]),
    ("n", ["N"]),
    ("p", ["P"]),
    ("r", ["R"]),
    ("s", ["S"]),
    ("t", ["T"]),
    ("v", ["V"]),
    ("w", ["W"]),
    ("z", ["Z"]),
    ("x", ["K", "S"]),
]


def _fallback_word(word):
    w = word.lower()
    # Drop a silent trailing 'e' (e.g. "make")
    if len(w) > 2 and w.endswith("e") and w[-2] not in "aeiou":
        w = w[:-1]
    out, i, n = [], 0, len(w)
    while i < n:
        c = w[i]
        # Soft/hard c and g depend on the next letter
        if c == "c":
            if w[i : i + 2] == "ck":
                out.append("K")
                i += 2
                continue
            nxt = w[i + 1] if i + 1 < n else ""
            out.append("S" if nxt and nxt in "eiy" else "K")
            i += 1
            continue
        if c == "g":
            nxt = w[i + 1] if i + 1 < n else ""
            out.append("JH" if nxt and nxt in "ey" else "G")
            i += 1
            continue
        for pat, ph in _FALLBACK_RULES:
            if w.startswith(pat, i):
                out.extend(ph)
                i += len(pat)
                break
        else:
            i += 1
    return out


def text_to_tokens(text):
    """Return (tokens, unknown words): ARPABET phonemes, "<WORD>" and "<SENT>" pauses"""
    # The g2p_en module, if installed
    try:
        from g2p_en import G2p

        g = G2p()(text)
    except Exception:
        g = None
    tokens = []
    if g is not None:
        for t in g:
            if t == " " or t == ",":
                tokens.append("<WORD>")
            elif t in ".!?;:":
                tokens.append("<SENT>")
            else:
                ph = _STRESS.sub("", t).upper()
                if ph in ARPA2VIS:
                    tokens.append(ph)
        return tokens, []

    cmu = _cmu_dict()
    unknown = []
    for chunk in re.findall(r"[A-Za-z']+|[.!?;:,]", text):
        if chunk in ".!?;:":
            tokens.append("<SENT>")
        elif chunk == ",":
            tokens.append("<WORD>")
        else:
            word = chunk.lower()
            phones = cmu.get(word) or cmu.get(word.strip("'"))
            if phones is None:
                # Not in the dictionary: rough spelling rules
                phones = _fallback_word(word.strip("'"))
                unknown.append(chunk)
            tokens.extend(phones)
            tokens.append("<WORD>")
    return tokens, unknown


# ------------------------------------------------------------------------
#    Tokens -> timed segments (seconds)
# ------------------------------------------------------------------------


def tokens_to_segments(tokens, speed):
    """List of {vis, start, end}; vis None is silence"""
    speed = max(speed, 1e-3)
    segs, t = [], 0.0
    for tok in tokens:
        if tok == "<WORD>":
            vis, dur = None, WORD_GAP / speed
        elif tok == "<SENT>":
            vis, dur = None, SENT_GAP / speed
        else:
            vis = ARPA2VIS.get(tok)
            if vis is None:
                continue
            dur = BASE_DUR / speed * next((f for g, f in DUR_FACTORS if tok in g), 1.0)
        segs.append({"vis": vis, "start": t, "end": t + dur})
        t += dur
    return segs


def parse_timed(text):
    """Parse 'label start end' lines (viseme or ARPABET label, seconds)"""
    segs = []
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        parts = re.split(r"[\s,;]+", line)
        if len(parts) < 3:
            raise ValueError(f"invalid timed line '{line}'")
        lab = parts[0].upper()
        vis = lab if lab in VISEMES else ARPA2VIS.get(_STRESS.sub("", lab))
        segs.append({"vis": vis, "start": float(parts[1]), "end": float(parts[2])})
    segs.sort(key=lambda s: s["start"])
    return segs


def parse_substitutions(text):
    """Parse 'AA:EH, IY=EE' into {viseme: substitute viseme}"""
    subs = {}
    for pair in re.split(r"[,;]+", text):
        if not pair.strip():
            continue
        m = re.fullmatch(r"\s*([A-Za-z]+)\s*[:=>]\s*([A-Za-z]+)\s*", pair)
        if not m or m[1].upper() not in VISEMES or m[2].upper() not in VISEMES:
            raise ValueError(f"invalid substitution '{pair.strip()}'")
        subs[m[1].upper()] = m[2].upper()
    return subs


# ------------------------------------------------------------------------
#    Smoothing
# ------------------------------------------------------------------------


def _rdp(pts, eps):
    """Ramer-Douglas-Peucker thinning using vertical error"""
    n = len(pts)
    if n < 3:
        return pts[:]
    keep = [False] * n
    keep[0] = keep[-1] = True
    stack = [(0, n - 1)]
    while stack:
        a, b = stack.pop()
        x0, y0 = pts[a]
        x1, y1 = pts[b]
        dx = x1 - x0
        maxd, idx = -1.0, -1
        for i in range(a + 1, b):
            x, y = pts[i]
            yi = y0 if dx == 0 else y0 + (x - x0) / dx * (y1 - y0)
            d = abs(y - yi)
            if d > maxd:
                maxd, idx = d, i
        if idx != -1 and maxd > eps:
            keep[idx] = True
            stack.append((a, idx))
            stack.append((idx, b))
    return [pts[i] for i in range(n) if keep[i]]


def _smooth_channel(ctrl, fps, smoothing_ms):
    if len(ctrl) < 2:
        return ctrl
    rate = SMOOTH_RATE if SMOOTH_RATE > 0 else fps
    step = fps / rate
    sigma = (smoothing_ms / 1000.0) * rate
    pad = max(1, int(round(3.0 * sigma)))
    x, y = np.array(ctrl, dtype=np.float64).T
    total = int(np.ceil((x[-1] - x[0]) / step)) + 1 + 2 * pad
    frames = x[0] - pad * step + np.arange(total) * step
    samples = np.interp(frames, x, y, left=0.0, right=0.0)
    # Gaussian blur, repeating the values at the ends
    if sigma > 1e-6:
        radius = max(1, int(round(sigma * 3.0)))
        kernel = np.exp(-(np.arange(-radius, radius + 1) ** 2) / (2.0 * sigma * sigma))
        samples = np.convolve(np.pad(samples, radius, mode="edge"), kernel / kernel.sum(), "valid")
    samples[samples < 1e-4] = 0.0
    return _rdp(list(zip(frames.tolist(), samples.tolist(), strict=True)), SMOOTH_TOL)


# ------------------------------------------------------------------------
#    Blender helpers
# ------------------------------------------------------------------------


def _action_fcurves(id_data):
    ad = id_data.animation_data
    if not ad or not ad.action:
        return None
    # Slotted actions (4.4+), then legacy
    try:
        from bpy_extras import anim_utils

        slot = getattr(ad, "action_slot", None)
        get_cbag = getattr(anim_utils, "action_get_channelbag_for_slot", None)
        if slot is not None and get_cbag is not None:
            cbag = get_cbag(ad.action, slot)
            return cbag.fcurves if cbag is not None else None
    except ImportError:
        pass
    return getattr(ad.action, "fcurves", None)


def can_create_action(tools_settings):
    """New Action is not allowed on the Armature Object, whose Action holds the pose"""
    return not (
        tools_settings.lipsync_driver_type == "MORPH"
        and tools_settings.lipsync_source == "ARMATURE_OBJ"
    )


def _action_name(tools_settings):
    if tools_settings.lipsync_input == "TEXT":
        # The words of the phrase in CamelCase
        words = re.findall(r"[A-Za-z0-9']+", tools_settings.lipsync_text or "")
        return "".join(w[0].upper() + w[1:] for w in words) or "LipSync"
    if tools_settings.lipsync_input == "TIMED":
        return os.path.splitext(tools_settings.lipsync_timed_text.name)[0]
    return "LipSync"


class _Target(NamedTuple):
    """Datablock animated by the lip sync, with its visemes"""

    anim_id: bpy.types.ID
    exists: Callable
    set_key: Callable
    data_path: Callable
    label: str


class MustardUI_Tools_LipSync(bpy.types.Operator):
    """Create a viseme lip sync animation from text, ARPABET or timed segments.
    Timing is in seconds, so the animation is independent of the frame rate"""

    bl_idname = "mustardui.tools_lipsync"
    bl_label = "Generate Lip Sync"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return active_object_operator_poll(context, config=ModelMode.USER)

    def _target(self, rig_settings, tools_settings):
        if tools_settings.lipsync_driver_type == "SHAPE_KEY":
            obj = rig_settings.model_body
            if obj is None or obj.type != "MESH" or not obj.data.shape_keys:
                raise RuntimeError("the model body has no shape keys")
            kbs = obj.data.shape_keys.key_blocks

            def set_key(name, frame, value):
                kbs[name].value = max(0.0, value)
                kbs[name].keyframe_insert("value", frame=frame)

            return _Target(
                obj.data.shape_keys,
                lambda name: name in kbs,
                set_key,
                lambda name: f'key_blocks["{name}"].value',
                obj.name,
            )

        # Body is optional, so the source may be missing
        try:
            owner = get_cp_source(tools_settings.lipsync_source, rig_settings)
        except AttributeError:
            owner = None
        if owner is None:
            raise RuntimeError("the custom properties source is not set")

        def set_key(name, frame, value):
            owner[name] = float(max(0.0, value))
            owner.keyframe_insert(data_path=f'["{name}"]', frame=frame)

        return _Target(
            owner,
            lambda name: name in owner.keys(),
            set_key,
            lambda name: f'["{name}"]',
            owner.name,
        )

    def _segments(self, tools_settings):
        mode = tools_settings.lipsync_input
        if mode == "TIMED":
            if tools_settings.lipsync_timed_text is None:
                raise RuntimeError("select a Text with the timed segments")
            return parse_timed(tools_settings.lipsync_timed_text.as_string()), []
        if mode == "ARPABET":
            toks = [_STRESS.sub("", t).upper() for t in tools_settings.lipsync_arpabet.split()]
            return tokens_to_segments(toks, tools_settings.lipsync_speed), []
        tokens, unknown = text_to_tokens(tools_settings.lipsync_text)
        return tokens_to_segments(tokens, tools_settings.lipsync_speed), unknown

    def execute(self, context):

        poll, arm = mustardui_active_object(context, config=ModelMode.USER)
        rig_settings = arm.MustardUI_RigSettings
        tools_settings = arm.MustardUI_ToolsSettings
        scene = context.scene

        try:
            tgt = self._target(rig_settings, tools_settings)
            subs = parse_substitutions(tools_settings.lipsync_substitutions)
            segs, unknown = self._segments(tools_settings)
        except (RuntimeError, ValueError) as e:
            self.report({"ERROR"}, f"MustardUI - Lip Sync: {e}")
            return {"CANCELLED"}

        if not segs:
            self.report({"ERROR"}, "MustardUI - Lip Sync: nothing to animate")
            return {"CANCELLED"}

        prefix = tools_settings.lipsync_prefix
        missing = [v for v in VISEMES if not tgt.exists(prefix + subs.get(v, v))]

        start_frame = scene.frame_current
        fps = scene.render.fps / scene.render.fps_base
        intensity = tools_settings.lipsync_intensity

        def to_frame(t):
            return round(start_frame + t * fps, 4)

        # Crossfade: peak at own center, 0 at neighbor centers
        centers = [(s["start"] + s["end"]) * 0.5 for s in segs]
        n = len(segs)
        channels = defaultdict(dict)

        def put(name, frame, val):
            channels[name][frame] = max(channels[name].get(frame, -1.0), val)

        for i, s in enumerate(segs):
            vis = s["vis"]
            if vis is None:
                continue
            name = prefix + subs.get(vis, vis)
            if not tgt.exists(name):
                continue
            put(name, to_frame(centers[i]), PEAK.get(vis, DEFAULT_PEAK) * intensity)
            put(name, to_frame(centers[i - 1] if i > 0 else s["start"]), 0.0)
            put(name, to_frame(centers[i + 1] if i < n - 1 else s["end"]), 0.0)

        if not channels:
            self.report(
                {"ERROR"},
                f"MustardUI - Lip Sync: no viseme found with prefix '{prefix}' on '{tgt.label}'",
            )
            return {"CANCELLED"}

        anim_id = tgt.anim_id
        ad = anim_id.animation_data
        our_paths = {tgt.data_path(nm) for nm in channels}
        had_action = bool(ad and ad.action)
        if had_action and tools_settings.lipsync_new_action and can_create_action(tools_settings):
            ad.action = None
            had_action = False
        elif had_action:
            fcurves = _action_fcurves(anim_id)
            if fcurves is not None:
                for fc in [fc for fc in fcurves if fc.data_path in our_paths]:
                    fcurves.remove(fc)

        smoothing = tools_settings.lipsync_smoothing
        for name, kd in channels.items():
            pts = sorted(kd.items())
            if smoothing > 0:
                pts = _smooth_channel(pts, fps, smoothing)
            # Nothing before the playhead
            for f, v in pts:
                if f >= start_frame - 1e-6:
                    tgt.set_key(name, round(f, 4), v)

        act = anim_id.animation_data.action
        if not had_action:
            act.name = _action_name(tools_settings)
            act.use_fake_user = True

        interpolation = tools_settings.lipsync_interpolation
        for fc in _action_fcurves(anim_id) or []:
            if fc.data_path not in our_paths:
                continue
            for kp in fc.keyframe_points:
                kp.interpolation = interpolation
                if interpolation == "BEZIER":
                    kp.handle_left_type = "AUTO_CLAMPED"
                    kp.handle_right_type = "AUTO_CLAMPED"
            fc.update()

        end_frame = int(to_frame(segs[-1]["end"])) + 1

        print(f"MustardUI - Lip Sync: {segs[-1]['end']:.2f}s, frames {start_frame}-{end_frame}")
        if unknown:
            words = ", ".join(dict.fromkeys(unknown))
            print(f"MustardUI - Lip Sync: not in dictionary, spelled roughly: {words}")
        message = f"MustardUI - Lip Sync '{act.name}' created"
        if missing:
            print(f"MustardUI - Lip Sync: visemes not found: {', '.join(missing)}")
            message += f", {len(missing)} visemes not found (details in the console)"
        self.report({"WARNING"} if missing else {"INFO"}, message)

        return {"FINISHED"}


def register():
    bpy.utils.register_class(MustardUI_Tools_LipSync)


def unregister():
    bpy.utils.unregister_class(MustardUI_Tools_LipSync)
