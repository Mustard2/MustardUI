"""Cloth Physics: colored Vertex Block Descent mass-spring solver on Blender compute shaders."""

import time

import bpy
import gpu
import numpy as np
from mathutils.bvhtree import BVHTree

W = 1024  # texture width; element i lives at (i % W, i // W)
GROUP = 64
RESULT_GROUP = RESULT_MOD = "MustardUI Cloth Result"
# Prototype names, picked up from older files
OLD_NAMES = {"MustardCloth Result": RESULT_MOD, "GPU Cloth Result": RESULT_MOD}
OLD_HELPERS = (".MustardCloth - ", ".GPU Cloth - ")

COMMON = """
ivec2 px(int i) { return ivec2(i & 1023, i >> 10); }
mat3 outer(vec3 a) { return mat3(a * a.x, a * a.y, a * a.z); }
int cellhash(ivec3 c) { return ((c.x * 73856093) ^ (c.y * 19349663) ^ (c.z * 83492791)) & 1048575; }
"""

PREDICT = (
    COMMON
    + """
/* Collider vertex between the previous (s_bv0) and the current frame (s_bv) */
vec3 body_at(int v, float t) {
  return mix(texelFetch(s_bv0, px(v), 0).xyz, texelFetch(s_bv, px(v), 0).xyz, t);
}

/* Closest point on a triangle (Ericson) */
vec3 closest_on_triangle(vec3 x, vec3 a, vec3 b, vec3 c) {
  vec3 ab = b - a, ac = c - a, ap = x - a;
  float d1 = dot(ab, ap), d2 = dot(ac, ap);
  if (d1 <= 0.0 && d2 <= 0.0) return a;
  vec3 bp = x - b;
  float d3 = dot(ab, bp), d4 = dot(ac, bp);
  if (d3 >= 0.0 && d4 <= d3) return b;
  vec3 cp = x - c;
  float d5 = dot(ab, cp), d6 = dot(ac, cp);
  if (d6 >= 0.0 && d5 <= d6) return c;
  float vc = d1 * d4 - d3 * d2, vb = d5 * d2 - d1 * d6, va = d3 * d6 - d5 * d4;
  if (vc <= 0.0 && d1 >= 0.0 && d3 <= 0.0) return a + ab * (d1 / (d1 - d3));
  if (vb <= 0.0 && d2 >= 0.0 && d6 <= 0.0) return a + ac * (d2 / (d2 - d6));
  if (va <= 0.0 && (d4 - d3) >= 0.0 && (d5 - d6) >= 0.0)
    return b + (c - b) * ((d4 - d3) / ((d4 - d3) + (d5 - d6)));
  float s = 1.0 / (va + vb + vc);
  return a + ab * (vb * s) + ac * (vc * s);
}

/* Barycentric coordinates of a point of the triangle */
vec3 barycentric(vec3 q, vec3 a, vec3 b, vec3 c) {
  vec3 v0 = b - a, v1 = c - a, v2 = q - a;
  float d00 = dot(v0, v0), d01 = dot(v0, v1), d11 = dot(v1, v1);
  float d20 = dot(v2, v0), d21 = dot(v2, v1);
  float den = max(d00 * d11 - d01 * d01, 1e-20);
  float v = (d11 * d20 - d01 * d21) / den, w = (d00 * d21 - d01 * d20) / den;
  return vec3(1.0 - v - w, v, w);
}

/* Frame of a triangle: edge direction, in-plane perpendicular, outward normal */
mat3 triangle_frame(vec3 a, vec3 b, vec3 c) {
  vec3 nf = normalize(cross(b - a, c - a)), e1 = normalize(b - a);
  return mat3(e1, cross(nf, e1), nf);
}

/* Plane of a tracked contact at time t; its normal turns with the triangle's frame */
vec4 tracked_plane(vec4 track, vec4 local_n, float t) {
  if (track.x == 0.0) return vec4(0.0);
  vec4 tri = texelFetch(s_tris, px(int(track.x) - 1), 0);
  vec3 a = body_at(int(tri.x), t), b = body_at(int(tri.y), t), c = body_at(int(tri.z), t);
  vec3 q = a * (1.0 - track.y - track.z) + b * track.y + c * track.z;
  vec3 n = normalize(triangle_frame(a, b, c) * local_n.xyz);
  return vec4(n, dot(n, q));
}

void main() {
  int i = int(gl_GlobalInvocationID.x);
  if (i >= n) return;
  ivec2 p = px(i);
  vec3 x = imageLoad(img_x, p).xyz;
  vec4 vel = imageLoad(img_v, p);
  vec4 at = texelFetch(s_attach, p, 0);
  float thickness = texelFetch(s_info, p, 0).w;
  float gl = length(gravity.xyz);
  if (h > 0.0) {
    /* Velocity of the previous substep (x0 = its start): inelastic contact, friction, damping */
    vec3 v = (x - imageLoad(img_x0, p).xyz) / h;
    vec4 mat = texelFetch(s_mat, p, 0);  /* friction, damping per second */
    vec4 planes[2] = vec4[2](imageLoad(img_c, p), imageLoad(img_c2, p));
    for (int k = 0; k < 2; k++) {
      vec4 c = planes[k];
      if (any(notEqual(c.xyz, vec3(0.0))) && dot(c.xyz, x) - c.w - thickness < 0.001) {
        /* Inelastic: the penalty push-back must not become a rebound */
        float vn = dot(v, c.xyz);
        v = (v - vn * c.xyz) * max(0.0, 1.0 - mat.x) + min(vn, 0.0) * c.xyz;
      }
    }
    v *= exp(-mat.y * h);
    /* Air drag across the surface (quadratic, implicit) */
    vec4 c = texelFetch(s_fn, p, 0);
    if (air > 0.0 && c.x >= 0.0) {
      vec3 a = cross(imageLoad(img_x, px(int(c.x))).xyz - x,
                     imageLoad(img_x, px(int(c.y))).xyz - x);
      vec3 b = cross(imageLoad(img_x, px(int(c.z))).xyz - x,
                     imageLoad(img_x, px(int(c.w))).xyz - x);
      vec3 nrm = a / max(length(a), 1e-20) + b / max(length(b), 1e-20);
      nrm /= max(length(nrm), 1e-20);
      float vn = dot(v, nrm);
      v -= vn * nrm * (1.0 - 1.0 / (1.0 + air * abs(vn) * h));
    }
    /* Acceleration along gravity, for the adaptive initial guess */
    float ag = gl > 0.0 ? clamp(dot(v - vel.xyz, gravity.xyz / gl) / h, 0.0, gl) : 0.0;
    vel = vec4(v, ag);
    imageStore(img_v, p, vel);
  }
  vec3 v = vel.xyz;
  vec3 y = x + h * v + h * h * gravity.xyz;
  if (at.w < 0.0) y = at.xyz;

  /* Contacts ride their triangles; searched again once moved redetect (3: only free vertices),
     all if colliders moved */
  bool moved = distance(x, imageLoad(img_xd, p).xyz) > redetect;
  bool free = imageLoad(img_ct, px(4 * i)).x == 0.0;
  /* Cloths with Collision off (mat.w 0) keep no contacts */
  bool collide = texelFetch(s_mat, p, 0).w > 0.5;
  bool search = collide && (detect == 2 || (moved && (detect == 1 || (detect == 3 && free))));
  bool none = search || !collide;
  vec4 track1 = none ? vec4(0.0) : imageLoad(img_ct, px(4 * i));
  vec4 track2 = none ? vec4(0.0) : imageLoad(img_ct, px(4 * i + 2));
  vec4 local1 = none ? vec4(0.0) : imageLoad(img_ct, px(4 * i + 1));
  vec4 local2 = none ? vec4(0.0) : imageLoad(img_ct, px(4 * i + 3));
  if (search) {
    imageStore(img_xd, p, vec4(x, 0.0));
    ivec3 c0 = ivec3(floor((x - grid_origin.xyz) / grid_origin.w));
    float best = radius, best2 = radius;
    vec3 n1 = vec3(0.0);
    /* Triangles binned by their bounds in cells >= the radius: search the 27 around */
    for (int cn = 0; cn < 27; cn++) {
      ivec3 c = c0 + ivec3(cn % 3, (cn / 3) % 3, cn / 9) - 1;
      if (any(lessThan(c, ivec3(0))) || any(greaterThanEqual(c, grid_dims.xyz))) continue;
      vec4 cell = texelFetch(s_cell, px((c.z * grid_dims.y + c.y) * grid_dims.x + c.x), 0);
      for (int k = 0; k < int(cell.y); k++) {
        vec4 t = texelFetch(s_clist, px(int(cell.x) + k), 0);
        vec4 sphere = texelFetch(s_ts, px(int(t.w)), 0);
        if (distance(x, sphere.xyz) - sphere.w >= best2) continue;
        vec3 a = body_at(int(t.x), blend0), b = body_at(int(t.y), blend0);
        vec3 cc = body_at(int(t.z), blend0);
        vec3 q = closest_on_triangle(x, a, b, cc);
        /* Two nearest planes facing different ways: a vertex in a valley touches both sides */
        float dist = length(x - q);
        if (dist < best2) {
          mat3 frame = triangle_frame(a, b, cc);
          vec3 nrm = (dot(x - q, frame[2]) >= 0.0 && dist > 1e-6) ? (x - q) / dist : frame[2];
          vec3 bary = barycentric(q, a, b, cc);
          vec4 track = vec4(t.w + 1.0, bary.y, bary.z, 0.0);
          vec4 local_n = vec4(transpose(frame) * nrm, 0.0);
          bool other = dot(nrm, n1) < 0.9;
          if (dist < best) {
            if (other) { track2 = track1; local2 = local1; best2 = best; }
            track1 = track;
            local1 = local_n;
            n1 = nrm;
            best = dist;
          }
          else if (other) { track2 = track; local2 = local_n; best2 = dist; }
        }
      }
    }
    imageStore(img_ct, px(4 * i), track1);
    imageStore(img_ct, px(4 * i + 1), local1);
    imageStore(img_ct, px(4 * i + 2), track2);
    imageStore(img_ct, px(4 * i + 3), local2);
  }
  /* Planes at the end of this substep */
  vec4 contact = tracked_plane(track1, local1, blend1);
  vec4 contact2 = tracked_plane(track2, local2, blend1);
  /* Start at the inertial target, outside the contact planes (adaptive: VBD initial guess) */
  vec3 x1 = (at.w < 0.0 || adaptive == 0 || gl == 0.0)
    ? y : x + h * v + h * h * vel.w * gravity.xyz / gl;
  vec4 planes[2] = vec4[2](contact, contact2);
  for (int k = 0; k < 2 && at.w >= 0.0 && project_init != 0; k++) {
    float g = dot(planes[k].xyz, x1) - planes[k].w - thickness;
    if (any(notEqual(planes[k].xyz, vec3(0.0))) && g < 0.0) x1 -= g * planes[k].xyz;
  }
  imageStore(img_x0, p, vec4(x, 0.0));
  imageStore(img_y, p, vec4(y, 0.0));
  imageStore(img_c, p, contact);
  imageStore(img_c2, p, contact2);
  imageStore(img_x, p, vec4(x1, 0.0));
}
"""
)

SOLVE = (
    COMMON
    + """
void main() {
  int g = int(gl_GlobalInvocationID.x);
  if (g >= count) return;
  int i = offset + g;
  ivec2 p = px(i);
  vec4 at = texelFetch(s_attach, p, 0);
  if (at.w < 0.0) return;
  vec4 info = texelFetch(s_info, p, 0);
  vec3 x = imageLoad(img_x, p).xyz;
  vec3 y = texelFetch(s_y, p, 0).xyz;
  float mh = info.z / (h * h);
  vec3 f = -mh * (x - y);
  mat3 H = mat3(mh);
  int start = int(info.x);
  float k_sum = 0.0;
  for (int k = 0; k < int(info.y); k++) {
    vec4 e = texelFetch(s_adj, px(start + k), 0);
    k_sum += e.y > 0.0 ? e.z : 0.0;  /* sewing springs left out: they held the seams open */
    vec3 d = x - imageLoad(img_x, px(int(e.x))).xyz;
    float l = length(d);
    if (l < 1e-9) continue;
    vec3 u = d / l;
    /* Sewing springs (rest 0) pull with at most sew_force */
    float ks = e.y == 0.0 ? min(e.z, sew_force / l) : e.z;
    f -= ks * (l - e.y) * u;
    mat3 uu = outer(u);
    H += ks * uu + ks * max(0.0, 1.0 - e.y / l) * (mat3(1.0) - uu);
  }
  if (at.w > 0.0) {
    f -= at.w * (x - at.xyz);
    H += mat3(at.w);
  }
  /* Self-collision: listed cloth vertices kept at their target distance */
  vec4 q0 = self_k > 0.0 ? texelFetch(s_nb, px(4 * i), 0) : vec4(-1.0);
  for (int s = 0; s < 2 && q0.x >= 0.0; s++) {
    vec4 q = s == 0 ? q0 : texelFetch(s_nb, px(4 * i + 1), 0);
    vec4 tq = texelFetch(s_nb, px(4 * i + 2 + s), 0);
    if (q.x < 0.0) break;
    for (int m = 0; m < 4; m++) {
      int j = int(q[m]);
      if (j < 0) break;
      vec3 d = x - imageLoad(img_x, px(j)).xyz;
      float l = length(d);
      float target = tq[m];
      if (l < target && l > 1e-9) {
        vec3 u = d / l;
        f += self_k * (target - l) * u;
        H += self_k * outer(u);
      }
    }
  }
  vec4 planes[2] = vec4[2](texelFetch(s_c, p, 0), texelFetch(s_c2, p, 0));
  for (int k = 0; k < 2; k++) {
    vec4 c = planes[k];
    float gap = dot(c.xyz, x) - c.w - info.w;
    if (any(notEqual(c.xyz, vec3(0.0))) && gap < 0.0) {
      f -= contact_k * gap * c.xyz;
      H += contact_k * outer(c.xyz);
    }
  }
  /* Slack springs leave H nearly singular (tiny edges, strings): regularize */
  H += mat3(regularize * k_sum);
  /* 3x3 solve by the adjugate (H is symmetric positive definite). */
  vec3 c0 = cross(H[1], H[2]), c1 = cross(H[2], H[0]), c2 = cross(H[0], H[1]);
  float det = dot(H[0], c0);
  vec3 dx = abs(det) < 1e-20 ? vec3(0.0) : vec3(dot(c0, f), dot(c1, f), dot(c2, f)) / det;
  float len = length(dx);
  if (len > max_step) dx *= max_step / len;
  /* Chebyshev acceleration (Wang 2015): extrapolate from the iterate before the previous one */
  vec3 x_new = x + dx;
  if (omega != 1.0) x_new = omega * (x_new - imageLoad(img_xp, p).xyz) + imageLoad(img_xp, p).xyz;
  imageStore(img_xp, p, vec4(x, 0.0));
  /* Dragged vertices never end inside a contact plane, however hard the drag pulls */
  x = x_new;
  for (int k = 0; k < 2 && at.w > 5000.0; k++) {
    float gap = dot(planes[k].xyz, x) - planes[k].w - info.w;
    if (any(notEqual(planes[k].xyz, vec3(0.0))) && gap < 0.0) x -= gap * planes[k].xyz;
  }
  imageStore(img_x, p, vec4(x, 0.0));
}
"""
)

HASH = (
    COMMON
    + """
void main() {
  int i = int(gl_GlobalInvocationID.x);
  if (i >= n2) return;
  vec4 key = vec4(1e9, -1.0, 0.0, 0.0);
  if (i < n) {
    ivec3 c = ivec3(floor(imageLoad(img_x, px(i)).xyz / cell));
    key = vec4(float(cellhash(c)), float(i), 0.0, 0.0);
  }
  imageStore(img_keys, px(i), key);
}
"""
)

SORT = (
    COMMON
    + """
/* One bitonic compare-exchange pass over the (hash, vertex) keys */
void main() {
  int i = int(gl_GlobalInvocationID.x);
  int l = i ^ j;
  if (i >= n2 || l <= i) return;
  vec4 a = imageLoad(img_keys, px(i)), b = imageLoad(img_keys, px(l));
  if ((a.x > b.x) == ((i & k) == 0)) {
    imageStore(img_keys, px(i), b);
    imageStore(img_keys, px(l), a);
  }
}
"""
)

SELF_DETECT = (
    COMMON
    + """
/* The 8 cloth vertices nearest to their target spacing, from the 27 hashed cells around */
void main() {
  int i = int(gl_GlobalInvocationID.x);
  if (i >= n) return;
  vec3 x = texelFetch(s_x, px(i), 0).xyz;
  vec4 rest = texelFetch(s_rest, px(i), 0);
  float score[8], targets[8];
  int ids[8];
  for (int m = 0; m < 8; m++) { score[m] = 1e9; ids[m] = -1; targets[m] = 0.0; }
  ivec3 c0 = ivec3(floor(x / cell));
  for (int cn = 0; cn < 27; cn++) {
    float key = float(cellhash(c0 + ivec3(cn % 3, (cn / 3) % 3, cn / 9) - 1));
    int lo = 0, hi = n2;
    while (lo < hi) {
      int mid = (lo + hi) >> 1;
      if (texelFetch(s_keys, px(mid), 0).x < key) lo = mid + 1; else hi = mid;
    }
    for (int e = lo; e < n2; e++) {
      vec4 kv = texelFetch(s_keys, px(e), 0);
      if (kv.x != key) break;
      int j = int(kv.y);
      vec3 xj = texelFetch(s_x, px(j), 0).xyz;
      float d = distance(x, xj);
      vec4 rest_j = texelFetch(s_rest, px(j), 0);
      /* Seam vertices (w = 1) do not repel each other: sewing closes the seam */
      if (j == i || d > cell || rest.w + rest_j.w > 1.5) continue;
      /* Crossed layers: no repulsion near the triangle each crossed */
      vec4 ti = texelFetch(s_tangle, px(i), 0), tj = texelFetch(s_tangle, px(j), 0);
      float reach = 3.0 * texelFetch(s_mat, px(i), 0).z;
      bool near_i = ti.w > 0.0 && distance(rest_j.xyz, ti.xyz) < reach;
      if (near_i || (tj.w > 0.0 && distance(rest.xyz, tj.xyz) < reach)) continue;
      /* At least each vertex's own radius (self_edge x its edges) */
      float radius = max(texelFetch(s_mat, px(i), 0).z, texelFetch(s_mat, px(j), 0).z);
      radius = max(self_radius, radius);
      float target = min(radius, self_rest * distance(rest.xyz, rest_j.xyz));
      float sc = d - target;
      /* Only pairs that can close within the frame's margin */
      if (sc > margin) continue;
      int worst = 0;
      bool dup = false;
      for (int m = 0; m < 8; m++) {
        dup = dup || ids[m] == j;
        if (score[m] > score[worst]) worst = m;
      }
      if (!dup && sc < score[worst]) { score[worst] = sc; ids[worst] = j; targets[worst] = target; }
    }
  }
  /* Compact: listed pairs first, the solve stops at the first -1; targets beside them */
  int c = 0;
  for (int m = 0; m < 8; m++) {
    if (ids[m] < 0) continue;
    ids[c] = ids[m];
    targets[c] = targets[m];
    c++;
  }
  for (int m = c; m < 8; m++) ids[m] = -1;
  imageStore(img_nb, px(4 * i), vec4(ids[0], ids[1], ids[2], ids[3]));
  imageStore(img_nb, px(4 * i + 1), vec4(ids[4], ids[5], ids[6], ids[7]));
  imageStore(img_nb, px(4 * i + 2), vec4(targets[0], targets[1], targets[2], targets[3]));
  imageStore(img_nb, px(4 * i + 3), vec4(targets[4], targets[5], targets[6], targets[7]));
}
"""
)


def gpu_available():
    """A GPU context with compute shaders and the 8 storage images the solver binds"""
    try:
        caps = gpu.capabilities
        return (
            caps.compute_shader_support_get()
            and caps.shader_image_load_store_support_get()
            and caps.max_images_get() >= 8
        )
    except (SystemError, AttributeError):  # no GPU context (background without gpu.init)
        return False


def _shader(source, images, samplers, constants):
    info = gpu.types.GPUShaderCreateInfo()
    for slot, name in enumerate(images):
        info.image(slot, "RGBA32F", "FLOAT_2D", name, qualifiers={"READ", "WRITE"})
    for slot, name in enumerate(samplers):
        info.sampler(slot, "FLOAT_2D", name)
    for kind, name in constants:
        info.push_constant(kind, name)
    info.local_group_size(GROUP, 1)
    info.compute_source(source)
    return gpu.shader.create_from_info(info)


def _texture(rows):
    """(n, k<=4) array -> RGBA32F texture of W-wide rows."""
    n = max(len(rows), 1)
    data = np.zeros((-(-n // W) * W, 4), np.float32)
    data[: len(rows), : rows.shape[1]] = rows
    return gpu.types.GPUTexture(
        (W, len(data) // W),
        format="RGBA32F",
        data=gpu.types.Buffer("FLOAT", data.size, data.ravel()),
    )


def _groups(n):
    return max(1, -(-n // GROUP))


class Solver:
    """Mass-spring cloth (stretch, shear, bend springs) with body contact planes, all on the GPU."""

    def __init__(self, pos, edges, polys, pins, params, groups=None):
        """groups: (first vertex, count, fabric params) of each cloth, default one cloth"""
        self.params = params
        n = len(pos)
        self.n = n
        self.groups = groups or [(0, n, params)]
        self.group = np.repeat(np.arange(len(self.groups)), [c for _, c, _ in self.groups])

        loop_start, loop_total, loop_verts = polys

        # Lumped mass from polygon areas
        corners = pos[loop_verts]
        area = np.zeros(len(loop_start))
        for k in range(1, loop_total.max() - 1):
            ok = loop_total > k + 1
            a, b, c = (
                corners[loop_start[ok]],
                corners[loop_start[ok] + k],
                corners[loop_start[ok] + k + 1],
            )
            area[ok] += 0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1)
        self.vert_area = np.zeros(n)
        np.add.at(self.vert_area, loop_verts, np.repeat(area / loop_total, loop_total))

        # Loose edges are sewing springs (rest length 0) when sewing is on, like Blender's cloth
        nxt = np.arange(len(loop_verts)) + 1
        last = loop_start + loop_total - 1
        nxt[last] = loop_start
        face_edges = np.unique(np.sort(np.stack([loop_verts, loop_verts[nxt]], 1), 1), axis=0)
        edges = np.sort(edges, 1)
        loose = edges[
            ~np.isin(edges[:, 0] * n + edges[:, 1], face_edges[:, 0] * n + face_edges[:, 1])
        ]
        sewing = np.array([g["sewing"] for _, _, g in self.groups], bool)[self.group]
        sewn = sewing[loose[:, 0]] & sewing[loose[:, 1]]
        sew = loose[sewn]
        stretch = np.concatenate([face_edges, loose[~sewn]])

        # Springs: edges (stretch), quad diagonals (shear), straight skip-one pairs (bend)
        quads = loop_start[loop_total == 4]
        shear = np.concatenate(
            [loop_verts[quads[:, None] + [0, 2]], loop_verts[quads[:, None] + [1, 3]]]
        )
        nbrs = [[] for _ in range(n)]
        for a, b in face_edges:
            nbrs[a].append(b)
            nbrs[b].append(a)
        bend = []
        for b, ns in enumerate(nbrs):
            for ia in range(len(ns)):
                for ic in range(ia + 1, len(ns)):
                    da, dc = pos[ns[ia]] - pos[b], pos[ns[ic]] - pos[b]
                    if np.dot(da, dc) < -0.8 * np.linalg.norm(da) * np.linalg.norm(dc):
                        bend.append((ns[ia], ns[ic]))
        bend = np.array(bend, np.int64).reshape(-1, 2)
        pairs = [stretch, shear, bend, sew]
        kinds = np.concatenate([np.full(len(p), k) for k, p in enumerate(pairs)])
        pairs = np.sort(np.concatenate(pairs), axis=1)
        _, first = np.unique(pairs, axis=0, return_index=True)
        self.springs, self.kinds = pairs[first], kinds[first]
        self.rest = np.linalg.norm(pos[self.springs[:, 0]] - pos[self.springs[:, 1]], axis=1)
        self.rest[self.kinds == 3] = 0.0
        # Self-collision radius of each vertex: self_edge x the mean length of its edges
        e, length = self.springs[self.kinds == 0], self.rest[self.kinds == 0]
        count = np.maximum(np.bincount(e.ravel(), minlength=n), 1)
        self.edge_radius = (
            params["self_edge"]
            * (np.bincount(e[:, 0], length, n) + np.bincount(e[:, 1], length, n))
            / count
        )
        self.sewn = len(sew)

        # Greedy coloring into contiguous slot ranges; bend springs stay out (weak, races harmless)
        adj = [[] for _ in range(n)]
        colored = np.isin(self.kinds, [0, 3] if params["color_shear"] == 0 else [0, 1, 3]) | (
            params["color_bend"] > 0
        )
        for a, b in self.springs[colored]:
            adj[a].append(b)
            adj[b].append(a)

        def greedy(vertices):
            color = np.full(n, -1)
            for v in vertices:
                used = {color[u] for u in adj[v]}
                c = 0
                while c in used:
                    c += 1
                color[v] = c
            return color

        # Iterated greedy (Culberson): recoloring classes in reverse never adds colors
        color = greedy(np.argsort([-len(a) for a in adj], kind="stable"))
        for _ in range(params["recolor"]):
            new = greedy(np.argsort(-color, kind="stable"))
            if new.max() > color.max():
                break
            color = new
        # Small classes past max_colors join the last one (their few neighbors race)
        color = np.minimum(color, params["max_colors"] - 1)
        order = np.argsort(color, kind="stable")
        self.order = order  # slot -> vertex
        self.slot = np.empty(n, np.int64)
        self.slot[order] = np.arange(n)
        counts = np.bincount(color)
        self.colors = list(
            zip(
                np.concatenate([[0], np.cumsum(counts)[:-1]]).tolist(), counts.tolist(), strict=True
            )
        )

        # Adjacency (CSR in slot order): neighbor slot, rest length, kind
        a, b = self.slot[self.springs[:, 0]], self.slot[self.springs[:, 1]]
        src = np.concatenate([a, b])
        dst = np.concatenate([b, a])
        sort = np.argsort(src, kind="stable")
        self.adj_src = src[sort]
        self.adj_dst = dst[sort]
        self.adj_rest = np.tile(self.rest, 2)[sort]
        self.adj_kind = np.tile(self.kinds, 2)[sort]
        self.adj_start = np.searchsorted(self.adj_src, np.arange(n))
        self.adj_count = np.bincount(self.adj_src, minlength=n)

        self.follow_target = pos.copy()
        self.follow_active = False
        self.group_pins = pins.copy()
        self.pins = pins.copy()  # per vertex, fixed at pin_pos
        self.pin_pos = pos.copy()
        self.drag = None  # (vertex indices, targets, stiffness)

        self.predict = _shader(
            PREDICT,
            ["img_x", "img_v", "img_x0", "img_y", "img_c", "img_c2", "img_xd", "img_ct"],
            [
                "s_attach",
                "s_info",
                "s_bv",
                "s_bv0",
                "s_tris",
                "s_cell",
                "s_clist",
                "s_ts",
                "s_mat",
                "s_fn",
            ],
            [
                ("INT", "n"),
                ("INT", "detect"),
                ("FLOAT", "h"),
                ("FLOAT", "radius"),
                ("FLOAT", "redetect"),
                ("FLOAT", "blend0"),
                ("FLOAT", "blend1"),
                ("INT", "adaptive"),
                ("INT", "project_init"),
                ("FLOAT", "air"),
                ("VEC4", "gravity"),
                ("VEC4", "grid_origin"),
                ("IVEC4", "grid_dims"),
            ],
        )
        self.solve = _shader(
            SOLVE,
            ["img_x", "img_xp"],
            ["s_attach", "s_info", "s_adj", "s_y", "s_c", "s_c2", "s_nb"],
            [
                ("INT", "offset"),
                ("INT", "count"),
                ("FLOAT", "h"),
                ("FLOAT", "contact_k"),
                ("FLOAT", "max_step"),
                ("FLOAT", "regularize"),
                ("FLOAT", "sew_force"),
                ("FLOAT", "self_k"),
                ("FLOAT", "omega"),
            ],
        )
        self.hash = _shader(
            HASH, ["img_x", "img_keys"], [], [("INT", "n"), ("INT", "n2"), ("FLOAT", "cell")]
        )
        self.sort = _shader(SORT, ["img_keys"], [], [("INT", "n2"), ("INT", "j"), ("INT", "k")])
        self.self_detect = _shader(
            SELF_DETECT,
            ["img_nb"],
            ["s_x", "s_keys", "s_rest", "s_mat", "s_tangle"],
            [
                ("INT", "n"),
                ("INT", "n2"),
                ("FLOAT", "cell"),
                ("FLOAT", "self_radius"),
                ("FLOAT", "self_rest"),
                ("FLOAT", "margin"),
            ],
        )
        self.n2 = 1 << max(1, (n - 1).bit_length())
        zero = np.zeros((n, 4), np.float32)
        self.tex = {k: _texture(zero) for k in ("v", "x0", "y", "c", "c2", "xd", "xp")}
        self.tex["keys"] = _texture(np.zeros((self.n2, 4), np.float32))
        self.tex["nb"] = _texture(np.full((4 * n, 4), -1.0, np.float32))
        # Each vertex's next and previous corners in its first and last face (slots), -1 none
        k = np.arange(len(loop_verts))
        first = np.repeat(loop_start, loop_total)
        last = first + np.repeat(loop_total, loop_total) - 1
        corners = np.column_stack(
            [
                loop_verts[np.where(k == last, first, k + 1)],
                loop_verts[np.where(k == first, last, k - 1)],
            ]
        )
        fn = np.full((n, 4), -1, np.int64)
        fn[loop_verts[::-1], :2] = corners[::-1]
        fn[loop_verts, 2:] = corners
        self.tex["fn"] = _texture(
            np.where(fn >= 0, self.slot[np.maximum(fn, 0)], -1)[self.order].astype(np.float32)
        )
        self.tex["ct"] = _texture(np.zeros((4 * n, 4), np.float32))
        seam = np.zeros(n)
        seam[sew.ravel()] = 1.0
        self.rest_pos = pos
        self.tex["rest"] = _texture(np.column_stack([pos, seam])[self.order])
        # Triangles for the crossing check, frames each vertex stays untangling
        tri = [
            np.column_stack(
                [loop_verts[loop_start], loop_verts[loop_start + k], loop_verts[loop_start + k + 1]]
            )[loop_total > k + 1]
            for k in range(1, loop_total.max() - 1)
        ]
        self.tris = np.concatenate(tri) if tri else np.zeros((0, 3), int)
        self.tangled, self.partner = np.zeros(n, int), np.zeros((n, 3))
        self.crossed_for, self.stuck = np.zeros(n, int), np.zeros(n, bool)
        self.self_every = params[
            "self_every"
        ]  # substeps between list refreshes, set from the motion each frame
        self.tex["tangle"] = _texture(np.zeros((n, 4), np.float32))
        self.set_positions(pos)
        self.thickness = np.zeros(n)
        self.upload_params()
        self.upload_attach()
        self.body = None

    def set_positions(self, pos):
        """Positions at rest: x0 = x, the next substep reads a zero velocity"""
        self.tex["x"] = _texture(pos[self.order])
        self.tex["x0"] = _texture(pos[self.order])
        self.tex["v"] = _texture(np.zeros((self.n, 4), np.float32))

    def fabric(self, key):
        """Per-vertex value of a fabric parameter of each cloth"""
        return np.array([g[key] for _, _, g in self.groups], np.float64)[self.group]

    def upload_params(self):
        table = np.array(
            [[g[k] for k in ("stretch", "shear", "bend", "sew_k")] for _, _, g in self.groups]
        )
        k = table[self.group[self.order[self.adj_src]], self.adj_kind]
        self.adj_k = k
        self.tex["adj"] = _texture(np.stack([self.adj_dst, self.adj_rest, k], axis=1))
        mass = (self.vert_area * self.fabric("density"))[self.order]
        info = np.stack([self.adj_start, self.adj_count, mass, self.thickness[self.order]], axis=1)
        self.tex["info"] = _texture(info)
        fabric = [self.fabric(k) for k in ("friction", "damping")]
        mat = np.stack([*fabric, self.edge_radius, self.fabric("collision")], axis=1)
        self.tex["mat"] = _texture(mat[self.order])

    def boost_bending(self, boost=None):
        """Bending stiffness times boost (per vertex, None = none)"""
        k = self.adj_k
        if boost is not None:
            k = k * np.where(self.adj_kind == 2, boost[self.order[self.adj_src]], 1.0)
        self.tex["adj"] = _texture(np.stack([self.adj_dst, self.adj_rest, k], axis=1))

    def upload_attach(self):
        at = np.zeros((self.n, 4), np.float32)
        # Follow Body (playback only): weak springs toward the skinned shape
        k = self.fabric("follow") * 1000.0
        if self.follow_active and np.any(k > 0):
            at[:, :3] = self.follow_target
            at[:, 3] = k
        at[self.pins, :3] = self.pin_pos[self.pins]
        at[self.pins, 3] = -1.0
        if self.drag is not None:
            idx, targets, k = self.drag
            free = ~self.pins[idx]
            at[idx[free], :3] = targets[free]
            at[idx[free], 3] = k[free]
        self.tex["attach"] = _texture(at[self.order])

    def fit_thickness(self, pos):
        """Per-vertex thickness: the rest gap to the body, clamped to [min_thickness, thickness]."""
        p = self.params
        self.thickness[:] = 0.0
        self.upload_params()
        self.set_positions(pos)
        self.dispatch_predict(0.0, detect=2)
        buf = self.tex["c"].read()
        buf.dimensions = buf.dimensions[0] * buf.dimensions[1] * 4
        c = np.asarray(buf).reshape(-1, 4)[self.slot]
        hit = np.any(c[:, :3] != 0, axis=1)
        gap = np.einsum("ij,ij->i", c[:, :3], pos) - c[:, 3]
        self.thickness[:] = self.fabric("thickness")
        fit = hit & (self.fabric("auto_fit") > 0)
        self.thickness[fit] = np.clip(gap[fit], p["min_thickness"], self.thickness[fit])
        self.upload_params()
        self.set_positions(pos)

    def set_body(self, verts, tris, bounds, prev=None):
        """Collider triangles near bounds (min, max), binned at prev (moving colliders) in cells"""
        p = self.params
        prev = verts if prev is None else prev
        r = p["thickness"] + p["detect"]
        tv = prev[tris]
        tmin, tmax = tv.min(1), tv.max(1)
        near = np.all((tmax >= bounds[0]) & (tmin <= bounds[1]), axis=1)
        # Tracked contacts keep global triangle indices: rebinning must not renumber them
        self.all_tris = tris
        ids = np.flatnonzero(near)
        tris, tv, tmin, tmax = tris[near], tv[near], tmin[near], tmax[near]
        self.bounds = bounds
        if not len(tris):  # nothing to collide with: one empty cell
            tris, tv, ids = (
                np.zeros((1, 3), np.int64),
                np.full((1, 3, 3), 1e9),
                np.zeros(1, np.int64),
            )
            tmin = tmax = tv[:, 0]
        origin = tmin.min(0)
        extent = tmax.max(0) - origin
        # Cells keep a slack: triangles that moved less stay valid in their bins
        cs = max(p["cell"], r + p["bin_slack"], extent.max() / 256)
        dims = np.floor(extent / cs).astype(np.int64) + 1
        i0 = np.floor((tmin - origin) / cs).astype(np.int64)
        span = np.floor((tmax - origin) / cs).astype(np.int64) - i0 + 1
        counts = span.prod(1)
        tri = np.repeat(np.arange(len(tris)), counts)
        k = np.arange(counts.sum()) - np.repeat(np.cumsum(counts) - counts, counts)
        sx, sy = span[tri, 0], span[tri, 1]
        cx, cy, cz = i0[tri, 0] + k % sx, i0[tri, 1] + (k // sx) % sy, i0[tri, 2] + k // (sx * sy)
        cell = ((cz * dims[1] + cy) * dims[0] + cx).astype(np.int32)
        order = np.argsort(
            cell
        )  # grouping by cell is enough: the order inside a cell does not matter
        ncell = int(dims.prod())
        cnt = np.bincount(cell, minlength=ncell)
        self.tex["clist"] = _texture(np.column_stack([tris, ids])[tri[order]].astype(np.float32))
        self.tex["tris"] = _texture(self.all_tris.astype(np.float32))
        self.near_ids = ids
        self.upload_body(verts, prev)
        self.tex["cell"] = _texture(
            np.stack([np.cumsum(cnt) - cnt, cnt], axis=1).astype(np.float32)
        )
        self.body = (origin, cs, dims)
        self.cell_load = (cnt.max(), cnt[cnt > 0].mean())
        self.binned = (prev.copy(), np.unique(tris), len(verts))

    def upload_body(self, verts, prev):
        """Collider positions now and at the previous frame, spheres bounding each triangle"""
        self.tex["bv"] = _texture(verts.astype(np.float32))
        self.tex["bv0"] = _texture(prev.astype(np.float32))
        tv = prev[self.all_tris[self.near_ids]]
        center = tv.mean(1)
        spheres = np.zeros((len(self.all_tris), 4), np.float32)
        spheres[self.near_ids] = np.column_stack(
            [center, np.linalg.norm(tv - center[:, None], axis=2).max(1)]
        )
        self.tex["ts"] = _texture(spheres)

    def move_body(self, verts, prev):
        """New collider positions without rebinning, if the triangles moved less than the slack"""
        old, used, n = self.binned
        if (
            len(verts) != n
            or len(prev) != n
            or np.abs(prev[used] - old[used]).max() >= self.params["bin_slack"]
        ):
            return False
        self.upload_body(verts, prev)
        return True

    def read_tex(self, name):
        """xyz of a per-vertex texture, in vertex order"""
        buf = self.tex[name].read()
        buf.dimensions = buf.dimensions[0] * buf.dimensions[1] * 4
        return np.asarray(buf).reshape(-1, 4)[self.slot, :3].astype(np.float64)

    def dispatch_predict(self, h, detect, blend=(1.0, 1.0)):
        """detect: 0 keeps the contacts, 1 searches where moved, 2 all, 3 where moved and free"""
        p, t = self.params, self.tex
        origin, cs, dims = self.body
        sh = self.predict
        sh.bind()
        for name in ("x", "v", "x0", "y", "c", "c2", "xd", "ct"):
            sh.image(f"img_{name}", t[name])
        for name in ("attach", "info", "bv", "bv0", "tris", "cell", "clist", "ts", "mat", "fn"):
            sh.uniform_sampler(f"s_{name}", t[name])
        sh.uniform_int("n", self.n)
        sh.uniform_int("detect", detect)
        sh.uniform_float("h", h)
        sh.uniform_float("radius", p["thickness"] + p["detect"])
        sh.uniform_float("redetect", p["redetect"])
        sh.uniform_float("blend0", blend[0])
        sh.uniform_float("blend1", blend[1])
        sh.uniform_float("gravity", (0.0, 0.0, -9.81 * p["gravity"], 0.0))
        sh.uniform_int("adaptive", p["adaptive_init"])
        sh.uniform_int("project_init", p["project_init"])
        sh.uniform_float("air", p["air"])
        sh.uniform_float("grid_origin", (*origin, cs))
        sh.uniform_int("grid_dims", (*dims.tolist(), 0))
        gpu.compute.dispatch(sh, _groups(self.n), 1, 1)

    def step(self, dt, detect=False):
        """One frame; detect forces a full contact search (the colliders moved)."""
        p = self.params
        t = self.tex
        h = dt / p["substeps"]
        for sub in range(p["substeps"]):
            # Lists every self_every substeps from the frame's sorted cells (sorting costs most)
            if p["self_k"] > 0 and sub % self.self_every == 0:
                self.find_self_contacts(sort=sub == 0 or p["self_sort"])
            # The collider moves from the previous frame (bv0) to this one (bv) over the substeps
            blend = (sub / p["substeps"], (sub + 1) / p["substeps"])
            # Moved vertices search every detect_every substeps; colliders moved: one full search,
            # then only free vertices (contacts ride the moving triangles, cloth falling onto them)
            every = sub % p["detect_every"] == 0
            mode = (2 if sub == 0 else 3 * every) if detect else int(every)
            self.dispatch_predict(h, mode, blend)

            sh = self.solve
            sh.bind()
            sh.image("img_x", t["x"])
            sh.image("img_xp", t["xp"])
            for name in ("attach", "info", "adj", "y", "c", "c2", "nb"):
                sh.uniform_sampler(f"s_{name}", t[name])
            sh.uniform_float("h", h)
            sh.uniform_float("contact_k", p["contact"])
            sh.uniform_float("max_step", p["max_step"])
            sh.uniform_float("regularize", p["regularize"])
            sh.uniform_float("sew_force", p["sew_force"])
            sh.uniform_float("self_k", p["self_k"])
            rho2, omega = p["chebyshev"] ** 2, 1.0
            for it in range(p["iterations"]):
                # Chebyshev weights: 1, 2 / (2 - rho^2), then 4 / (4 - rho^2 omega)
                if rho2:
                    omega = (
                        1.0 if it == 0 else 2 / (2 - rho2) if it == 1 else 4 / (4 - rho2 * omega)
                    )
                sh.uniform_float("omega", omega)
                for offset, count in self.colors:
                    sh.uniform_int("offset", offset)
                    sh.uniform_int("count", count)
                    gpu.compute.dispatch(sh, _groups(count), 1, 1)

    def read_lists(self):
        """Self-contact lists (slot order): 8 ids, 8 targets per vertex"""
        buf = self.tex["nb"].read()
        buf.dimensions = buf.dimensions[0] * buf.dimensions[1] * 4
        return np.asarray(buf).reshape(-1, 4)[: 4 * self.n].reshape(self.n, 16).copy()

    def untangle(self, pos, nb, still=True):
        """Crossing triangles stop repelling each other until the cloth pulls them back through"""
        frames = self.params["untangle"]
        # Only around listed pairs pressed to their target, and vertices already untangling
        ids = nb[:, :8].astype(int)
        x = pos[self.order]
        close = (ids >= 0) & (
            np.linalg.norm(x[np.maximum(ids, 0)] - x[:, None], axis=2) < 1.1 * nb[:, 8:16]
        )
        near = np.zeros(self.n, bool)
        near[self.order[np.flatnonzero(close.any(1))]] = True
        near[self.order[ids[close]]] = True
        near |= self.tangled > 0
        tris = self.tris[near[self.tris].any(1) & ~self.stuck[self.tris].any(1)]
        bvh = BVHTree.FromPolygons(pos.tolist(), tris.tolist(), all_triangles=True)
        pairs = np.array(bvh.overlap(bvh), int).reshape(-1, 2)
        t = tris[pairs]
        t = t[~(t[:, 0, :, None] == t[:, 1, None, :]).any((1, 2))]
        # Crossed for over a second of stillness (modelled so, or held by the body): left
        hit = np.zeros(self.n, bool)
        hit[t.ravel()] = True
        self.crossed_for = np.where(hit, self.crossed_for + still, 0)
        self.stuck |= self.crossed_for > 30
        t = t[~self.stuck[t].any((1, 2))]
        before = self.tangled > 0
        self.tangled = np.maximum(self.tangled - 1, 0)
        # Each crossing vertex ignores only the area (rest) of the triangle it crossed
        for a, b in ((0, 1), (1, 0)):
            self.partner[t[:, a].ravel()] = np.repeat(self.rest_pos[t[:, b]].mean(1), 3, axis=0)
        self.tangled[t.ravel()] = frames
        flag = self.tangled > 0
        if np.any(flag) or np.any(before):
            self.tex["tangle"] = _texture(np.column_stack([self.partner, flag])[self.order])

    def find_self_contacts(self, sort=True):
        """Hash the vertices into cells, sort them (bitonic), list each one's nearest others"""
        p, t, n2 = self.params, self.tex, self.n2
        cell = max(p["self_radius"], self.edge_radius.max()) + p["self_margin"]
        if sort:
            sh = self.hash
            sh.bind()
            sh.image("img_x", t["x"])
            sh.image("img_keys", t["keys"])
            sh.uniform_int("n", self.n)
            sh.uniform_int("n2", n2)
            sh.uniform_float("cell", cell)
            gpu.compute.dispatch(sh, _groups(n2), 1, 1)
            sh = self.sort
            sh.bind()
            sh.image("img_keys", t["keys"])
            sh.uniform_int("n2", n2)
            k = 2
            while k <= n2:
                j = k // 2
                while j:
                    sh.uniform_int("j", j)
                    sh.uniform_int("k", k)
                    gpu.compute.dispatch(sh, _groups(n2), 1, 1)
                    j //= 2
                k *= 2
        sh = self.self_detect
        sh.bind()
        sh.image("img_nb", t["nb"])
        for name in ("x", "keys", "rest", "mat", "tangle"):
            sh.uniform_sampler(f"s_{name}", t[name])
        sh.uniform_int("n", self.n)
        sh.uniform_int("n2", n2)
        sh.uniform_float("cell", cell)
        sh.uniform_float("self_radius", p["self_radius"])
        sh.uniform_float("self_rest", p["self_rest"])
        sh.uniform_float("margin", p["self_margin"])
        gpu.compute.dispatch(sh, _groups(self.n), 1, 1)

    def read(self):
        """World positions in vertex order."""
        buf = self.tex["x"].read()
        buf.dimensions = buf.dimensions[0] * buf.dimensions[1] * 4
        return np.asarray(buf).reshape(-1, 4)[self.slot, :3].astype(np.float64)


DEFAULTS = {
    "substeps": 64,
    "iterations": 6,
    "stretch": 1.0e4,  # N/m
    "shear": 100.0,
    "bend": 300.0,
    "density": 0.15,  # kg/m2
    "thickness": 0.004,  # m
    "min_thickness": 0.0005,  # m, floor of the fitted per-vertex thickness
    "auto_fit": 1,  # fit the thickness to the rest gap to the body
    "margin": 0.1,  # m around the cloth for collider triangles
    "bin_slack": 0.002,  # m a collider triangle moves before it is rebinned
    "detect": 0.01,  # m beyond thickness to look for contacts
    "redetect": 0.005,  # m a vertex moves before its contact is searched again
    "detect_every": 8,  # substeps between those searches
    "cell": 0.01,  # m, collider grid cell (at least the search radius)
    "contact": 1.0e4,  # N/m
    "friction": 0.3,
    "damping": 1.0,  # 1/s
    "smooth_display": 1,  # Interactive Mode shows 1/4, 1/2, 1/4 of 3 frames
    "air": 0.0,  # 1/m, quadratic drag across the surface (slows the whole cloth)
    "gravity": 1.0,
    "max_step": 0.02,  # m per vertex update
    "regularize": 1.0,  # Hessian diagonal added, x the summed spring stiffness
    "self_k": 1.0e4,  # N/m, 0 turns self-collision off
    "self_radius": 0.003,  # m kept between cloth vertices at least
    "self_rest": 0.5,  # pairs modelled closer keep this fraction of their distance
    "self_margin": 0.005,  # m of motion per frame the self-contact lists cover
    "self_edge": 1.2,  # self radius at least this x the mean edge (0.71: slips through)
    "untangle": 1,  # frames crossing vertices skip repulsion near the other, 0 off
    "self_every": 8,  # substeps between self-contact list refreshes at most
    "self_sort": 0,  # sort the cells again at each refresh, not once a frame
    "adaptive_init": 0,  # VBD adaptive start: hanging cloth never settles
    "project_init": 1,  # start the iterations outside the contact planes
    "chebyshev": 0.8,  # spectral radius for Chebyshev acceleration, 0 off
    "color_bend": 0,
    "recolor": 10,  # iterated greedy passes to reduce the colors
    "max_colors": 2,  # classes past it join the last one: a dispatch per color
    "color_shear": 0,  # shear springs in the coloring
    "sewing": 0,  # loose edges pull their vertices together
    "follow": 0.0,  # Follow Body: springs toward the skinned shape, x 1000 N/m
    "collision": 1,  # with the colliders, 0 off
    "sew_k": 1.0e3,  # N/m once a seam is closed
    "sew_force": 1.0,  # N per sewing edge at most: strong pulls crumple the cloth
}


# ---------------------------------------------------------------- Blender glue


def mesh_arrays(me, matrix):
    n = len(me.vertices)
    co = np.empty(n * 3)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3) @ np.array(matrix)[:3, :3].T + np.array(matrix)[:3, 3]
    edges = np.empty(len(me.edges) * 2, np.int64)
    me.edges.foreach_get("vertices", edges)
    loop_start = np.empty(len(me.polygons), np.int64)
    loop_total = np.empty(len(me.polygons), np.int64)
    me.polygons.foreach_get("loop_start", loop_start)
    me.polygons.foreach_get("loop_total", loop_total)
    loop_verts = np.empty(len(me.loops), np.int64)
    me.loops.foreach_get("vertex_index", loop_verts)
    return co, edges.reshape(-1, 2), (loop_start, loop_total, loop_verts)


TOPOLOGY = {}  # collider name -> (vertex count, loop triangles)


def collider_arrays(objects, depsgraph):
    verts, tris, base = [], [], 0
    for ob in objects:
        ev = ob.evaluated_get(depsgraph)
        n = len(ev.data.vertices)
        known = TOPOLOGY.get(ob.name)
        if known is not None and known[0] == n and isinstance(ev.data, bpy.types.Mesh):
            co = np.empty(n * 3)
            ev.data.vertices.foreach_get("co", co)
            m = np.array(ev.matrix_world)
            verts.append(co.reshape(-1, 3) @ m[:3, :3].T + m[:3, 3])
            tris.append(known[1] + base)
            base += n
            continue
        ev = ob.evaluated_get(depsgraph)
        me = ev.to_mesh()
        me.calc_loop_triangles()
        co = np.empty(len(me.vertices) * 3)
        me.vertices.foreach_get("co", co)
        m = np.array(ev.matrix_world)
        verts.append(co.reshape(-1, 3) @ m[:3, :3].T + m[:3, 3])
        t = np.empty(len(me.loop_triangles) * 3, np.int64)
        me.loop_triangles.foreach_get("vertices", t)
        TOPOLOGY[ob.name] = (len(me.vertices), t.reshape(-1, 3))
        tris.append(t.reshape(-1, 3) + base)
        base += len(me.vertices)
        ev.to_mesh_clear()
    if not objects:
        return np.zeros((0, 3)), np.zeros((0, 3), np.int64)
    return np.concatenate(verts), np.concatenate(tris)


def result_node_group():
    ng = bpy.data.node_groups.get(RESULT_GROUP)
    if ng:
        return ng
    ng = bpy.data.node_groups.new(RESULT_GROUP, "GeometryNodeTree")
    ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    ng.interface.new_socket("Simulation", in_out="INPUT", socket_type="NodeSocketObject")
    ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    N, L = ng.nodes, ng.links
    gi, go = N.new("NodeGroupInput"), N.new("NodeGroupOutput")
    info = N.new("GeometryNodeObjectInfo")
    info.transform_space = "ORIGINAL"
    sample = N.new("GeometryNodeSampleIndex")
    sample.data_type = "FLOAT_VECTOR"
    setpos = N.new("GeometryNodeSetPosition")
    size_self, size_sim = (
        N.new("GeometryNodeAttributeDomainSize"),
        N.new("GeometryNodeAttributeDomainSize"),
    )
    equal = N.new("FunctionNodeCompare")
    equal.data_type, equal.operation = "INT", "EQUAL"
    switch = N.new("GeometryNodeSwitch")
    switch.input_type = "GEOMETRY"
    L.new(gi.outputs[1], info.inputs["Object"])
    L.new(info.outputs["Geometry"], sample.inputs["Geometry"])
    L.new(N.new("GeometryNodeInputPosition").outputs[0], sample.inputs["Value"])
    L.new(N.new("GeometryNodeInputIndex").outputs[0], sample.inputs["Index"])
    L.new(gi.outputs[0], setpos.inputs["Geometry"])
    L.new(sample.outputs[0], setpos.inputs["Position"])
    L.new(gi.outputs[0], size_self.inputs[0])
    L.new(info.outputs["Geometry"], size_sim.inputs[0])
    L.new(size_self.outputs["Point Count"], equal.inputs["A"])
    L.new(size_sim.outputs["Point Count"], equal.inputs["B"])
    L.new(equal.outputs[0], switch.inputs["Switch"])
    L.new(gi.outputs[0], switch.inputs["False"])
    L.new(setpos.outputs[0], switch.inputs["True"])
    L.new(switch.outputs[0], go.inputs[0])
    return ng


def helper_name(obj):
    return f".MustardUI Cloth - {obj.name}"


def evaluated_up_to(context, obj, mod):
    """Mesh evaluated up to the modifier: (world positions, edges, polys), object, mesh"""
    after = list(obj.modifiers)[list(obj.modifiers).index(mod) :]
    shown = [m.show_viewport for m in after]
    for m in after:
        m.show_viewport = False
    ev = obj.evaluated_get(context.evaluated_depsgraph_get())
    me = ev.to_mesh()
    arrays = mesh_arrays(me, obj.matrix_world)
    for m, show in zip(after, shown, strict=True):
        m.show_viewport = show
    return arrays, ev, me


def rename_old(obj):
    """Modifier, node group and helper of the prototype's names take the current ones"""
    for old, new in OLD_NAMES.items():
        mod = obj.modifiers.get(old)
        if mod and not obj.modifiers.get(new):
            mod.name = new
        group = bpy.data.node_groups.get(old)
        if group and not bpy.data.node_groups.get(new):
            group.name = new
    for prefix in OLD_HELPERS:
        helper = bpy.data.objects.get(prefix + obj.name)
        if helper and not bpy.data.objects.get(helper_name(obj)):
            helper.name = helper.data.name = helper_name(obj)


def place_result_modifier(obj, sim_mesh):
    """Result modifier before the first Subdivision (CAGE) or after the last one (SUBDIVIDED)"""
    rename_old(obj)
    mod = obj.modifiers.get(RESULT_MOD)
    if mod is None:
        mod = obj.modifiers.new(RESULT_MOD, "NODES")
        mod.node_group = result_node_group()
    mods = [m for m in obj.modifiers if m != mod]
    subsurf = [i for i, m in enumerate(mods) if m.type in {"SUBSURF", "MULTIRES"}]
    index = len(mods) if not subsurf else subsurf[0] if sim_mesh == "CAGE" else subsurf[-1] + 1
    obj.modifiers.move(list(obj.modifiers).index(mod), index)
    return mod


# Collider modifiers deforming it beyond its Armature, e.g. MustardUI physics cages (Surface Deform)
BODY_DEFORMERS = {"SURFACE_DEFORM", "MESH_DEFORM", "LATTICE", "HOOK", "CLOTH", "SOFT_BODY"}

SIMS = {}  # cloth object name -> Cloth, all simulated together in WORLD
WORLD = {"world": None}


class Cloth:
    """One cloth object: its simulation mesh, helper mesh for the Result modifier, pins"""

    def __init__(self, context, obj, pin_group, fabric, target=None, sim_mesh="CAGE"):
        self.obj_name = obj.name
        self.fabric = fabric
        self.target = target.name if target else None
        mod = place_result_modifier(obj, sim_mesh)
        if sim_mesh == "SUBDIVIDED":
            # Render levels must match or the Result modifier skips the render
            for m in obj.modifiers:
                if m.type == "SUBSURF":
                    m.render_levels = m.levels
        mod.show_viewport = mod.show_render = True
        (self.rest, self.edges, self.polys), ev, me = evaluated_up_to(context, obj, mod)
        self.pins = np.zeros(len(self.rest), bool)
        gi = obj.vertex_groups[pin_group].index if pin_group in obj.vertex_groups else None
        if gi is not None:
            for v in me.vertices:
                for g in v.groups:
                    if g.group == gi and g.weight > 0.5:
                        self.pins[v.index] = True
        ev.to_mesh_clear()
        self.source_verts = len(obj.data.vertices)
        self.inv = np.linalg.inv(np.array(obj.matrix_world))

        # Point-only helper: the Result modifier samples its positions by index
        helper = bpy.data.objects.get(helper_name(obj))
        self.resume = None
        if helper is not None and len(helper.data.vertices) == len(self.rest):
            # Continue from the drape saved in the file
            co = np.empty(len(self.rest) * 3)
            helper.data.vertices.foreach_get("co", co)
            m = np.array(obj.matrix_world)
            self.resume = co.reshape(-1, 3) @ m[:3, :3].T + m[:3, 3]
        helper_me = bpy.data.meshes.new(helper_name(obj))
        helper_me.vertices.add(len(self.rest))
        if helper is None:
            helper = bpy.data.objects.new(helper_name(obj), helper_me)
            for coll in obj.users_collection:
                coll.objects.link(helper)
            # Disabled in viewports and renders: the Result modifier still evaluates it
            helper.hide_viewport = helper.hide_render = helper.hide_select = True
        else:
            old = helper.data
            helper.data = helper_me
            bpy.data.meshes.remove(old)
        mod.properties.inputs.Socket_1.value = helper
        obj.update_tag()
        self.pin_bind = None
        self.target_dirty = False

    @property
    def obj(self):
        return bpy.data.objects[self.obj_name]

    def source(self, context):
        """World positions of the mesh evaluated up to the Result modifier (Armature applied)"""
        (pos, _, _), ev, _ = evaluated_up_to(context, self.obj, self.obj.modifiers[RESULT_MOD])
        ev.to_mesh_clear()
        return pos

    def write(self, pos):
        local = pos[self.span] @ self.inv[:3, :3].T + self.inv[:3, 3]
        me = bpy.data.objects[helper_name(self.obj)].data
        me.vertices.foreach_set("co", local.ravel())
        me.update()

    def save_shape_key(self, context, pos, name="Cloth Physics"):
        """Store the drape as a Shape Key of the source mesh, back through deforming modifiers"""
        obj = self.obj
        n = len(obj.data.vertices)
        if n != len(self.rest):
            raise ValueError(
                "the simulation mesh is subdivided: switch Simulation Mesh to Cage to save it"
            )
        mod = obj.modifiers[RESULT_MOD]
        if obj.data.shape_keys is None:
            obj.shape_key_add(name="Basis", from_mix=False)
        basis = np.empty(n * 3)
        obj.data.shape_keys.reference_key.data.foreach_get("co", basis)
        basis = basis.reshape(-1, 3)
        # Each vertex's deformation (linear per vertex): probed with 1 mm offsets
        probe = obj.shape_key_add(name="Cloth Physics probe", from_mix=False)
        eps = 1e-3

        def evaluated(offset):
            probe.data.foreach_set("co", (basis + offset).ravel())
            probe.value = 1.0
            obj.data.update()
            (co, _, _), ev, _ = evaluated_up_to(context, obj, mod)
            ev.to_mesh_clear()
            return co @ self.inv[:3, :3].T + self.inv[:3, 3]

        x0 = evaluated(np.zeros(3))
        jac = np.stack([(evaluated(np.eye(3)[k] * eps) - x0) / eps for k in range(3)], axis=2)
        obj.shape_key_remove(probe)
        target = pos[self.span] @ self.inv[:3, :3].T + self.inv[:3, 3]
        # Modifiers that project (Shrinkwrap) flatten the probe: keep their offsets as they are
        flat = np.abs(np.linalg.det(jac)) < 1e-3
        jac[flat] = np.eye(3)
        delta = np.linalg.solve(jac, (target - x0)[:, :, None])[:, :, 0]
        key = obj.shape_key_add(name=name, from_mix=False)
        key.data.foreach_set("co", (basis + delta).ravel())
        key.value = 1.0
        obj.data.update()
        return key


class World:
    """All cloths in one solver: one set of dispatches, and cloth against cloth by self-collision"""

    def __init__(self, context, cloths, colliders, params):
        self.cloths = cloths
        self.colliders = [c.name for c in colliders]
        offset, groups = 0, []
        for c in cloths:
            c.span = slice(offset, offset + len(c.rest))
            groups.append((offset, len(c.rest), c.fabric))
            offset += len(c.rest)
        shift = [c.span.start for c in cloths]
        pos = np.concatenate([c.rest for c in cloths])
        edges = np.concatenate([c.edges + o for c, o in zip(cloths, shift, strict=True)])
        loop_start = np.concatenate(
            [
                c.polys[0] + o
                for c, o in zip(
                    cloths, np.cumsum([0] + [len(c.polys[2]) for c in cloths[:-1]]), strict=True
                )
            ]
        )
        loop_total = np.concatenate([c.polys[1] for c in cloths])
        loop_verts = np.concatenate([c.polys[2] + o for c, o in zip(cloths, shift, strict=True)])
        pins = np.concatenate([c.pins for c in cloths])
        t = time.perf_counter()
        self.solver = Solver(pos, edges, (loop_start, loop_total, loop_verts), pins, params, groups)
        self.build_ms = (time.perf_counter() - t) * 1000
        self.rest = pos
        self.refresh_body(pos, reload=True)
        self.solver.fit_thickness(pos)
        self.pos = pos.copy()
        # Crossing checks spacing, last motion and lists; last frames shown (display filter)
        self.steps, self.motion, self.lists, self.shown = 0, np.inf, None, []
        self.follow_bind = None  # Follow Body on deformed colliders: (vertices, binding)
        for c in cloths:
            if c.resume is not None:
                self.pos[c.span] = c.resume
        self.solver.set_positions(self.pos)
        for c in cloths:
            c.write(self.pos)
            self.bind_pins(c)
        self.cache = {}  # frame -> state, filled by timeline playback
        self.frame = None
        self.redetect_all = False  # positions jumped (reset, cache): search every contact again
        self.bins_stale = False
        self.sources_dirty = False  # frame changed: pins follow the outfits' new pose

    @property
    def source_verts(self):
        return sum(c.source_verts for c in self.cloths)

    def refresh_body(self, pos, reload):
        """Bin the colliders around the cloth; reload re-reads their evaluated meshes"""
        prev = None
        if reload:
            old = getattr(self, "body", None)
            self.body = collider_arrays(
                [bpy.data.objects[n] for n in self.colliders], bpy.context.evaluated_depsgraph_get()
            )
            self.body_dirty = False
            # The colliders move from where they were over the next frame's substeps
            if old is not None and len(old[0]) == len(self.body[0]):
                prev = old[0]
            if getattr(self.solver, "binned", None) and self.solver.move_body(
                self.body[0], self.body[0] if prev is None else prev
            ):
                return
        m = self.solver.params["margin"]
        self.solver.set_body(*self.body, (pos.min(0) - m, pos.max(0) + m), prev)

    def bind_pins(self, cloth):
        """Pins on a Target Object keep their spot on its nearest triangle"""
        cloth.pin_bind = None
        cloth.target_dirty = False
        idx = np.flatnonzero(self.solver.pins[cloth.span]) + cloth.span.start
        if cloth.target is None or cloth.target not in bpy.data.objects or not len(idx):
            return
        verts, tris = collider_arrays(
            [bpy.data.objects[cloth.target]], bpy.context.evaluated_depsgraph_get()
        )
        cloth.pin_bind = (idx, *surface_bind(self.solver.pin_pos[idx], verts, tris))

    def update_pins(self, cloth):
        """Move the bound pins with the Target Object's current shape."""
        cloth.target_dirty = False
        if cloth.pin_bind is None:
            return
        idx, *bind = cloth.pin_bind
        verts, _ = collider_arrays(
            [bpy.data.objects[cloth.target]], bpy.context.evaluated_depsgraph_get()
        )
        self.solver.pin_pos[idx] = surface_points(bind, verts)
        self.solver.upload_attach()

    def step(self, dt=1 / 30, follow=False):
        """One frame; follow turns Follow Body on (timeline playback)"""
        if self.solver.follow_active != follow:
            self.solver.follow_active = follow
            self.solver.upload_attach()
        if self.sources_dirty:
            for c in self.cloths:
                c.inv = np.linalg.inv(np.array(c.obj.matrix_world))
            self.follow_sources(bpy.context)
        moved = self.body_dirty
        if moved:
            self.refresh_body(self.pos, reload=True)
        elif self.bins_stale:
            # The colliders moved last step and stopped: searches now see them where they ended
            self.solver.set_body(*self.body, self.solver.bounds)
        self.bins_stale = moved
        for c in self.cloths:
            if c.target_dirty:
                self.update_pins(c)
        pos_before, sv, p = self.pos, self.solver, self.solver.params
        sv.step(dt, detect=moved or self.redetect_all)
        # While the GPU runs: last frame's crossings, every frame while moving, else every 4th
        self.steps += 1
        if p["untangle"] and p["self_k"] > 0:
            if self.lists is not None and (
                self.motion > p["self_margin"] / 2 or sv.tangled.any() or self.steps % 4 == 0
            ):
                sv.untangle(pos_before, self.lists, still=self.motion < p["self_margin"] / 2)
        elif sv.tangled.any():  # turned off: every pair repels again
            sv.tangled[:] = 0
            sv.tex["tangle"] = _texture(np.zeros((sv.n, 4), np.float32))
        self.redetect_all = False
        if moved:
            self.solver.tex["bv0"] = self.solver.tex["bv"]  # still until the colliders move again
        self.pos = pos = sv.read()
        self.lists = (
            sv.read_lists() if p["untangle"] and p["self_k"] > 0 else None
        )  # the GPU is idle now
        self.motion = np.abs(pos - pos_before).max()
        # Self lists refreshed as often as the fastest vertex needs (once a frame at rest)
        refreshes = int(
            np.clip(
                np.ceil(2 * self.motion / p["self_margin"]), 1, p["substeps"] // p["self_every"]
            )
        )
        sv.self_every = p["substeps"] // refreshes
        # Interactive Mode shows 1/4, 1/2, 1/4 of the last 3 frames: frame-rate flapping cancels
        self.shown = (
            ([pos] + self.shown)[:3] if not follow and p["smooth_display"] and self.shown else [pos]
        )
        shown = (
            0.25 * self.shown[0] + 0.5 * self.shown[1] + 0.25 * self.shown[2]
            if len(self.shown) == 3
            else pos
        )
        for c in self.cloths:
            c.write(shown)
        lo, hi = self.solver.bounds
        m = self.solver.params["margin"] / 2
        if np.any(pos.min(0) < lo + m) or np.any(pos.max(0) > hi - m):
            self.refresh_body(pos, reload=False)
        return pos

    def reset(self, cloth=None):
        """Back to the rest shape, one cloth or all"""
        span = cloth.span if cloth else slice(None)
        self.solver.stuck[span] = False
        self.shown = []
        self.pos = self.pos.copy()
        self.pos[span] = self.rest[span]
        self.solver.set_positions(self.pos)
        self.redetect_all = True
        for c in self.cloths:
            c.write(self.pos)

    # ------------------------------------------------------------ playback

    def follow_sources(self, context):
        """Pins without a Target Object and Follow Body follow the cloth's own deformation"""
        self.sources_dirty = False
        sv = self.solver
        if not hasattr(self, "pin_ref"):
            self.pin_ref = np.full((sv.n, 3), np.nan)
        new = sv.pins & np.isnan(self.pin_ref[:, 0])
        self.pin_ref[new] = sv.pin_pos[new] - self.rest[new]
        self.pin_ref[~sv.pins] = np.nan
        for c in self.cloths:
            idx = np.flatnonzero(sv.pins[c.span])
            pinned = c.target is None and len(idx)
            if not pinned and c.fabric["follow"] <= 0:
                continue
            src = c.source(context)
            sv.follow_target[c.span] = src
            if pinned:
                sv.pin_pos[idx + c.span.start] = src[idx] + self.pin_ref[idx + c.span.start]
        if self.follow_bind is not None:
            # Toward the vertex's spot on the deformed colliders
            idx, *bind = self.follow_bind
            sv.follow_target[idx] = surface_points(bind, self.collider_verts(context))
        sv.upload_attach()

    def collider_verts(self, context):
        objects = [bpy.data.objects[n] for n in self.colliders]
        return collider_arrays(objects, context.evaluated_depsgraph_get())[0]

    def playback_step(self, context, dt):
        """One animation frame: colliders and pin targets re-read, pins follow the cloth"""
        for c in self.cloths:
            c.inv = np.linalg.inv(np.array(c.obj.matrix_world))
            c.target_dirty = c.target is not None
        self.body_dirty = True
        self.solver.follow_active = True
        self.follow_sources(context)
        return self.step(dt, follow=True)

    def state(self):
        """Positions now and at the previous substep start (the velocity), for the frame cache"""
        return self.pos.copy(), self.solver.read_tex("x0")

    def start(self, context):
        """Playback start: every cloth back to its deformed source mesh, nothing cached"""
        pos = np.concatenate([c.source(context) for c in self.cloths])
        for c in self.cloths:
            c.inv = np.linalg.inv(np.array(c.obj.matrix_world))
        self.pin_ref = np.full((self.solver.n, 3), np.nan)
        self.body_dirty = True
        self.solver.stuck[:] = False
        self.solver.follow_target = pos.copy()
        # Colliders deformed beyond their Armature (physics cages): Follow Body pulls toward their
        # surface, each vertex bound to its nearest triangle; the outfit's Armature shape ignores it
        self.follow_bind = None
        objects = [bpy.data.objects[n] for n in self.colliders]
        deformed = any(
            m.type in BODY_DEFORMERS and m.show_viewport for o in objects for m in o.modifiers
        )
        idx = [np.arange(c.span.start, c.span.stop) for c in self.cloths if c.fabric["follow"] > 0]
        if idx and deformed:
            verts, tris = collider_arrays(objects, context.evaluated_depsgraph_get())
            idx = np.concatenate(idx)
            self.follow_bind = (idx, *surface_bind(pos[idx], verts, tris))
        self.solver.upload_attach()
        self.set_state((pos, pos))
        self.cache = {}

    def set_state(self, state):
        x, x0 = state
        self.shown = []
        sv = self.solver
        sv.tex["x"] = _texture(x[sv.order])
        sv.tex["x0"] = _texture(x0[sv.order])
        sv.tex["v"] = _texture(np.zeros((sv.n, 4), np.float32))
        self.pos = x.copy()
        self.redetect_all = True
        for c in self.cloths:
            c.write(self.pos)

    def save_shape_key(self, context, cloth=None):
        return (cloth or self.cloths[0]).save_shape_key(context, self.pos)


def surface_bind(points, verts, tris):
    """Points kept on their nearest triangles: (corners, barycentric, offset along the normal)"""
    bvh = BVHTree.FromPolygons(verts.tolist(), tris.tolist())
    corners = tris[np.array([bvh.find_nearest(q)[2] for q in points])]
    a, b, c = (verts[corners[:, k]] for k in range(3))
    bary = barycentric(points, a, b, c)
    point = bary[:, :1] * a + bary[:, 1:2] * b + bary[:, 2:] * c
    nrm = np.cross(b - a, c - a)
    nrm /= np.linalg.norm(nrm, axis=1, keepdims=True)
    return corners, bary, np.einsum("ij,ij->i", points - point, nrm)


def surface_points(bind, verts):
    """The bound points on the triangles' current shape"""
    corners, bary, offset = bind
    a, b, c = (verts[corners[:, k]] for k in range(3))
    nrm = np.cross(b - a, c - a)
    nrm /= np.linalg.norm(nrm, axis=1, keepdims=True)
    return bary[:, :1] * a + bary[:, 1:2] * b + bary[:, 2:] * c + offset[:, None] * nrm


def barycentric(p, a, b, c):
    """Barycentric coordinates of the points projected on the triangles"""
    v0, v1, v2 = b - a, c - a, p - a
    d00, d01, d11 = (v0 * v0).sum(1), (v0 * v1).sum(1), (v1 * v1).sum(1)
    d20, d21 = (v2 * v0).sum(1), (v2 * v1).sum(1)
    den = d00 * d11 - d01 * d01
    v = (d11 * d20 - d01 * d21) / den
    w = (d00 * d21 - d01 * d20) / den
    return np.stack([1 - v - w, v, w], axis=1)


@bpy.app.handlers.persistent
def colliders_changed(scene, depsgraph):
    """Flag the world when its colliders or pin targets were re-evaluated"""
    world = WORLD["world"]
    if world is None:
        return
    names = {u.id.original.name for u in depsgraph.updates if isinstance(u.id, bpy.types.Object)}
    if names.intersection(world.colliders):
        world.body_dirty = True
    for c in world.cloths:
        if c.target in names:
            c.target_dirty = True


@bpy.app.handlers.persistent
def file_loaded(*args):
    """GPU state does not survive a file load: cloths resume from their helper meshes"""
    SIMS.clear()
    WORLD["world"] = None
