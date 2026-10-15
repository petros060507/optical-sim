"""Бэкенд-независимая 3D-сцена: меши поверхностей/ободьев/диафрагмы/детектора
+ ОДИН батч сегментов на все лучи. Float32/uint32 — готово к загрузке в VBO."""
from __future__ import annotations
from dataclasses import dataclass, field
import numpy as np

from minizemax.core.bundle import STATUS_ALIVE, STATUS_BLOCKED, STATUS_TIR, STATUS_MISS
from minizemax.engine.source import make_bundle
from minizemax.engine.tracer import SequentialTracer


@dataclass
class MeshData:
    verts: np.ndarray          # (M,3) float32, физические координаты (x,y,z)
    faces: np.ndarray          # (K,3) uint32
    color: tuple               # rgba 0..1
    name: str
    gl_options: str = "translucent"


@dataclass
class Scene:
    meshes: list = field(default_factory=list)
    line_verts: np.ndarray = None     # (L,2,3) float32 сегменты
    line_colors: np.ndarray = None    # (L,2,4) float32
    polylines: list = field(default_factory=list)   # [(P,3) float32, rgba]
    center: np.ndarray = None         # (3,) физический центр сцены
    scale: float = 100.0


def to_gl(verts: np.ndarray) -> np.ndarray:
    """(x,y,z) оптики -> (x,y,z) GL: оптическая ось горизонталь, up = y оптики."""
    return np.ascontiguousarray(verts[:, [2, 0, 1]], dtype=np.float32)


def _revolve(z_of_r, r_max, z_off, n_theta, n_r):
    r = np.linspace(0.0, r_max, n_r)
    th = np.linspace(0.0, 2 * np.pi, n_theta, endpoint=False)
    R, T = np.meshgrid(r, th)
    Z = z_off + z_of_r(R)
    verts = np.stack([R * np.cos(T), R * np.sin(T), Z], -1).reshape(-1, 3)
    faces = []
    for i in range(n_theta):
        i2 = (i + 1) % n_theta
        for j in range(n_r - 1):
            a = i * n_r + j; b = a + 1; c = i2 * n_r + j + 1; d = i2 * n_r + j
            faces.append((a, b, c)); faces.append((a, c, d))
    return (np.ascontiguousarray(verts, np.float32),
            np.ascontiguousarray(faces, np.uint32))


def _cylinder(re, z1, z2, n_theta):
    th = np.linspace(0.0, 2 * np.pi, n_theta, endpoint=False)
    top = np.stack([re * np.cos(th), re * np.sin(th), np.full(n_theta, z2)], 1)
    bot = np.stack([re * np.cos(th), re * np.sin(th), np.full(n_theta, z1)], 1)
    verts = np.concatenate([bot, top], 0).astype(np.float32)
    faces = []
    for i in range(n_theta):
        i2 = (i + 1) % n_theta
        a, b, c, d = i, i2, n_theta + i2, n_theta + i
        faces.append((a, b, c)); faces.append((a, c, d))
    return verts, np.ascontiguousarray(faces, np.uint32)


def _is_glass(mat):
    return getattr(mat, "name", "air") != "air"


def build_scene(built, fi=0, wi=0, n_rays=24, n_theta=64, n_r=12,
                show_axis: bool = False) -> Scene:
    sc = Scene()
    GLASS = (0.45, 0.70, 0.95, 0.55)
    RIM = (0.20, 0.45, 0.80, 0.75)
    MIRROR = (0.80, 0.80, 0.85, 1.0)
    STOP = (0.20, 0.20, 0.20, 1.0)
    DET = (0.92, 0.92, 0.92, 0.55)

    for i, s in enumerate(built.surfaces):
        v, f = _revolve(s.sag, s.semi_dia, s.z, n_theta, n_r)
        if s.reflective:
            sc.meshes.append(MeshData(v, f, MIRROR, f"mirror{i}", "opaque"))
        else:
            sc.meshes.append(MeshData(v, f, GLASS, f"surf{i}", "translucent"))
        if i == built.stop_idx and not s.reflective:
            v2, f2 = _revolve(lambda r: np.zeros_like(r), 1.6 * s.semi_dia, s.z, n_theta, 2)
            # кольцо: вырезаем внутреннюю часть простым способом — два радиуса
            rr = np.linspace(s.semi_dia, 1.6 * s.semi_dia, 3)
            th = np.linspace(0, 2 * np.pi, n_theta, endpoint=False)
            R, T = np.meshgrid(rr, th)
            vv = np.stack([R * np.cos(T), R * np.sin(T), np.full_like(R, s.z)], -1)
            vv = vv.reshape(-1, 3).astype(np.float32)
            ff = []
            for a in range(n_theta):
                a2 = (a + 1) % n_theta
                for b in range(2):
                    p, q = a * 3 + b, a * 3 + b + 1
                    u, w = a2 * 3 + b + 1, a2 * 3 + b
                    ff.append((p, q, u)); ff.append((p, u, w))
            sc.meshes.append(MeshData(vv, np.ascontiguousarray(ff, np.uint32),
                                      STOP, f"stop{i}", "opaque"))
            del v2, f2
        if i + 1 < len(built.surfaces) and _is_glass(s.mat_after) \
                and s.mat_after is built.surfaces[i + 1].mat_before:
            s2 = built.surfaces[i + 1]
            re = min(s.semi_dia, s2.semi_dia) * 0.998   # внутрь: без z-fighting на стыках
            z1 = s.z + float(s.sag(np.array([re]))[0])
            z2 = s2.z + float(s2.sag(np.array([re]))[0])
            v, f = _cylinder(re, z1, z2, n_theta)
            sc.meshes.append(MeshData(v, f, RIM, f"rim{i}", "translucent"))

    h = max(s.semi_dia for s in built.surfaces) * 1.2
    q = np.array([[-h, -h, 0], [h, -h, 0], [h, h, 0], [-h, h, 0]], np.float32)
    q[:, 2] = built.detector_z
    sc.meshes.append(MeshData(q, np.array([(0, 1, 2), (0, 2, 3)], np.uint32),
                              DET, "detector", "translucent"))

    # лучи: один батч сегментов
    ang = np.linspace(0, 2 * np.pi, n_rays, endpoint=False)
    px = np.concatenate([[0.0], 0.85 * np.cos(ang), 0.45 * np.cos(ang + 0.3)])
    py = np.concatenate([[0.0], 0.85 * np.sin(ang), 0.45 * np.sin(ang + 0.3)])
    b = make_bundle(built, fi, wi, px=px, py=py, w=np.ones(len(px)) / len(px))
    res = SequentialTracer(built.surfaces, record_history=True).trace(b)
    bb = res.bundle
    dz = bb.direction[:, 2]
    safe = np.abs(dz) > 1e-12
    tz = np.where(safe, (built.detector_z - bb.origin[:, 2]) / np.where(safe, dz, 1.0), np.nan)
    pz = bb.origin + np.where(np.isfinite(tz), tz, 0.0)[:, None] * bb.direction
    pts_all = res.history + [pz]
    segs, cols = [], []
    polys = []
    COLORS = {STATUS_ALIVE: (0.10, 0.45, 1.00, 0.90),
              STATUS_BLOCKED: (1.00, 0.55, 0.00, 0.95),
              STATUS_TIR: (0.85, 0.20, 0.85, 0.95),
              STATUS_MISS: (0.55, 0.55, 0.55, 0.70)}
    st = bb.status
    stop_surf = getattr(res, "stop_surf", None)
    stop_point = getattr(res, "stop_point", None)
    for j in range(len(px)):
        k = int(stop_surf[j]) if stop_surf is not None else -1
        if k < 0:
            P = np.array([h_[j] for h_ in pts_all])          # живой: до детектора
        else:
            P = np.array([h_[j] for h_ in pts_all[:k + 1]])  # до прибытия на поверх. k
            if st[j] in (STATUS_BLOCKED, STATUS_TIR) and stop_point is not None:
                sp = stop_point[j]
                if np.isfinite(sp).all():
                    P = np.concatenate([P, sp[None, :]], 0)  # огрызок до апертуры/ПВО
            elif st[j] == STATUS_MISS:
                o, d = bb.origin[j], bb.direction[j]
                if abs(d[2]) > 1e-12:
                    t = (built.detector_z - o[2]) / d[2]
                    if t > 0:
                        P = np.concatenate([P, (o + t * d)[None, :]], 0)
        P = P[np.isfinite(P[:, 2])]
        if len(P) < 2:
            continue
        col = COLORS[int(st[j])]
        S = np.stack([P[:-1], P[1:]], 1)
        segs.append(S)
        polys.append((P.astype(np.float32), np.array(col, np.float32)))
        cols.append(np.tile(np.array(col, np.float32), (len(S), 1, 1)))
    sc.line_verts = np.ascontiguousarray(np.concatenate(segs), np.float32)
    sc.line_colors = np.ascontiguousarray(np.concatenate(cols), np.float32)
    z0 = built.surfaces[0].z
    if show_axis:
        polys.append((np.array([[z0 - 5.0, 0.0, 0.0], [built.detector_z, 0.0, 0.0]], np.float32),
                      np.array([0.75, 0.75, 0.75, 0.6], np.float32)))
    sc.center = np.array([0.0, 0.0, (z0 + built.detector_z) / 2])
    sc.scale = (built.detector_z - z0) + 4 * h
    sc.polylines = polys
    return sc
