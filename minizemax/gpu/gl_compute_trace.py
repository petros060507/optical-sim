"""GPU-трассировка пучка compute-шейдером OpenGL 4.3+ (SSBO + glDispatchCompute).
Не требует kompute/Vulkan-биндингов: использует тот же современный GL-контекст Qt.
Результат возвращается в CPU-массивы для анализа (spot/OPD/MTF)."""
from __future__ import annotations
import math
import numpy as np
from OpenGL import GL as gl

_CS = """
#version 430 core
layout(local_size_x = 256) in;
#define NSURF {nsurf}
layout(std430, binding = 0) readonly buffer RaysIn {{ vec4 rin[]; }};
layout(std430, binding = 1) readonly buffer DirIn  {{ vec4 din[]; }};
layout(std430, binding = 2) readonly buffer SurfP  {{ vec4 sp[]; }};
layout(std430, binding = 3) writeonly buffer OutP  {{ vec4 outp[]; }};
uniform float z_img;

vec3 refract_vec(vec3 d, vec3 n, float n1, float n2, out bool tir) {{
    if (dot(d, n) > 0.0) n = -n;
    float eta = n1 / n2;
    float ci = -dot(d, n);
    float s2 = eta * eta * (1.0 - ci * ci);
    tir = s2 > 1.0;
    float ct = sqrt(max(1.0 - s2, 0.0));
    return eta * d + (eta * ci - ct) * n;
}}

void main() {{
    uint i = gl_GlobalInvocationID.x;
    vec3 o = rin[i].xyz;
    vec3 d = normalize(din[i].xyz);
    float opl = 0.0, status = 0.0;
    for (int s = 0; s < NSURF; s++) {{
        vec4 g = sp[2 * s];
        vec4 m = sp[2 * s + 1];
        float R = g.x, k = g.y, zs = g.z, semi = g.w;
        float n1 = m.x, n2 = m.y, refl = m.z, plane = m.w;
        vec3 ol = o - vec3(0.0, 0.0, zs);
        float t; vec3 p; vec3 n;
        if (plane > 0.5) {{
            if (abs(d.z) < 1e-12) {{ status = 3.0; break; }}
            t = -ol.z / d.z; p = ol + t * d; n = vec3(0.0, 0.0, 1.0);
        }} else {{
            vec3 C = vec3(0.0, 0.0, R);
            vec3 oc = ol - C;
            float b = dot(oc, d);
            float c = dot(oc, oc) - R * R;
            float disc = b * b - c;
            if (disc < 0.0) {{ status = 3.0; break; }}
            float sq = sqrt(disc);
            float t1 = -b - sq, t2 = -b + sq;
            t = (t1 > 1e-9) ? t1 : t2;
            p = ol + t * d;
            if ((p.z - R) * R >= 0.0) {{ status = 3.0; break; }}
            for (int it = 0; it < 3; it++) {{
                float r = length(p.xy);
                float q = 1.0 - (1.0 + k) * r * r / (R * R);
                float sag = r * r / (R * (1.0 + sqrt(max(q, 0.0))));
                float f = p.z - sag;
                float ds = r / (R * sqrt(max(q, 1e-12)));
                float drdt = dot(p.xy, d.xy) / max(r, 1e-12);
                float dfdt = d.z - ds * drdt;
                t -= f / (abs(dfdt) > 1e-12 ? dfdt : 1.0);
                p = ol + t * d;
            }}
            float r2 = length(p.xy);
            float q2 = 1.0 - (1.0 + k) * r2 * r2 / (R * R);
            float ds2 = r2 / (R * sqrt(max(q2, 1e-12)));
            n = normalize(vec3(-ds2 * p.x / max(r2, 1e-12), -ds2 * p.y / max(r2, 1e-12), 1.0));
        }}
        if (t <= 1e-9) {{ status = 3.0; break; }}
        if (length(p.xy) > semi) {{ status = 1.0; break; }}
        opl += n1 * t;
        vec3 pn = o + t * d;
        if (refl > 0.5) {{
            d = reflect(d, n);
        }} else {{
            bool tir;
            vec3 dn = refract_vec(d, n, n1, n2, tir);
            if (tir) {{ status = 2.0; break; }}
            d = dn;
        }}
        o = pn + 1e-9 * d;
    }}
    if (status == 0.0 && abs(d.z) > 1e-12) {{
        o = o + ((z_img - o.z) / d.z) * d;
    }}
    outp[i] = vec4(o.x, o.y, opl, status);
}}
"""

_CTX = None


def _ensure_ctx():
    global _CTX
    if _CTX is not None:
        _CTX.makeCurrent()
        return _CTX
    from minizemax.ui.qt import QApplication, QOpenGLWidget, QSurfaceFormat
    QApplication.instance() or QApplication([])
    w = QOpenGLWidget()
    fmt = QSurfaceFormat()
    fmt.setVersion(4, 6)
    prof = getattr(QSurfaceFormat, "CoreProfile", None)
    if prof is None:
        prof = QSurfaceFormat.OpenGLContextProfile.CoreProfile
    fmt.setProfile(prof)
    w.setFormat(fmt)
    w.resize(4, 4)
    w.show()
    w.hide()
    w.makeCurrent()
    _CTX = w
    return w


def gl_compute_available():
    try:
        _ensure_ctx()
        ver = gl.glGetString(gl.GL_VERSION).decode()
        maj, mino = (int(x) for x in ver.split(".")[:2])
        return (maj, mino) >= (4, 3), f"GL {ver}"
    except Exception as e:  # noqa: BLE001
        return False, str(e)


class GLComputeTracer:
    def __init__(self, built, wl: float):
        self._w = _ensure_ctx()
        self._built = built
        sp = []
        for s in built.surfaces:
            R = getattr(s, "radius", np.inf)
            plane = 0.0 if np.isfinite(R) else 1.0
            Rv = float(R) if np.isfinite(R) else 0.0
            n1 = float(s.mat_before.n(np.array([wl]))[0])
            n2 = abs(-n1 if s.reflective else float(s.mat_after.n(np.array([wl]))[0]))
            sp += [Rv, float(getattr(s, "conic", 0.0)), float(s.z), float(s.semi_dia),
                   n1, n2, 1.0 if s.reflective else 0.0, plane]
        self._sp = np.array(sp, np.float32)
        src = _CS.format(nsurf=len(built.surfaces))
        cs = gl.glCreateShader(gl.GL_COMPUTE_SHADER)
        gl.glShaderSource(cs, src)
        gl.glCompileShader(cs)
        if gl.glGetShaderiv(cs, gl.GL_COMPILE_STATUS) == 0:
            raise RuntimeError(gl.glGetShaderInfoLog(cs).decode())
        self._prog = gl.glCreateProgram()
        gl.glAttachShader(self._prog, cs)
        gl.glLinkProgram(self._prog)
        if gl.glGetProgramiv(self._prog, gl.GL_LINK_STATUS) == 0:
            raise RuntimeError(gl.glGetProgramInfoLog(self._prog).decode())
        gl.glDeleteShader(cs)
        self._u_z = gl.glGetUniformLocation(self._prog, "z_img")

    def _ssbo(self, arr):
        b = gl.glGenBuffers(1)
        gl.glBindBuffer(gl.GL_SHADER_STORAGE_BUFFER, b)
        gl.glBufferData(gl.GL_SHADER_STORAGE_BUFFER, arr.nbytes, arr, gl.GL_DYNAMIC_DRAW)
        return b

    def trace(self, px, py, z_img: float):
        N = len(px)
        if N == 0:
            return np.zeros((0, 2)), np.zeros(0, np.float32)
        self._w.makeCurrent()
        rin = np.zeros((N, 4), np.float32); rin[:, 0] = px; rin[:, 1] = py
        din = np.zeros((N, 4), np.float32); din[:, 2] = 1.0
        out = np.zeros((N, 4), np.float32)
        bs = [self._ssbo(rin), self._ssbo(din), self._ssbo(self._sp), self._ssbo(out)]
        for idx, b in enumerate(bs):
            gl.glBindBufferBase(gl.GL_SHADER_STORAGE_BUFFER, idx, b)
        gl.glUseProgram(self._prog)
        gl.glUniform1f(self._u_z, float(z_img))
        gl.glDispatchCompute(int(math.ceil(N / 256)), 1, 1)
        gl.glMemoryBarrier(gl.GL_BUFFER_UPDATE_BARRIER_BIT | gl.GL_SHADER_STORAGE_BARRIER_BIT)
        gl.glBindBuffer(gl.GL_SHADER_STORAGE_BUFFER, bs[3])
        gl.glGetBufferSubData(gl.GL_SHADER_STORAGE_BUFFER, 0, out.nbytes, out)
        gl.glDeleteBuffers(len(bs), bs)
        gl.glUseProgram(0)
        st = out[:, 3]
        return out[st == 0.0][:, :2], st
