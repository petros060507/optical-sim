"""GPU 3D-вид: современный OpenGL core profile (4.x, GLSL 430, VAO, MSAA) + PyOpenGL.
Камера CAD-стиля с клампами; alpha-сортировка back-to-front; legacy-fallback < GL 3.3.
Диагностика: MZ_GL_DEBUG=1. Отключить: MZ_NO_GL=1."""
from __future__ import annotations
import os
import re
import ctypes
import numpy as np
from minizemax.ui.qt import (QOpenGLWidget, QSizePolicy, QSurfaceFormat, Qt, Signal,
                            SP_EXPANDING, WA_OPAQUE, WA_NOSYSBG)
from OpenGL import GL as gl

FOV = 45.0
_MID = getattr(Qt, "MiddleButton", None) or Qt.MouseButton.MiddleButton
_SHIFT = getattr(Qt, "ShiftModifier", None) or Qt.KeyboardModifier.ShiftModifier
_LEFT = getattr(Qt, "LeftButton", None) or Qt.MouseButton.LeftButton

VS_MESH_C = ("#version 430 core\nlayout(location=0) in vec3 a_pos;\n"
             "layout(location=1) in vec3 a_nrm;\nuniform mat4 u_mvp;\nout vec3 v_nrm;\n"
             "void main(){v_nrm=a_nrm;gl_Position=u_mvp*vec4(a_pos,1.0);}")
FS_MESH_C = ("#version 430 core\nin vec3 v_nrm;\nuniform vec4 u_color;\nout vec4 frag;\n"
             "void main(){vec3 n=normalize(v_nrm);vec3 l=normalize(vec3(0.4,0.6,0.8));"
             "float d=0.40+0.60*abs(dot(n,l));frag=vec4(u_color.rgb*d,u_color.a);}")
VS_LINE_C = ("#version 430 core\nlayout(location=0) in vec3 a_pos;\n"
             "layout(location=1) in vec4 a_col;\nuniform mat4 u_mvp;\nout vec4 v_col;\n"
             "void main(){v_col=a_col;gl_Position=u_mvp*vec4(a_pos,1.0);}")
FS_LINE_C = "#version 430 core\nin vec4 v_col;\nout vec4 frag;\nvoid main(){frag=v_col;}"

VS_MESH_L = ("#version 120\nattribute vec3 a_pos;attribute vec3 a_nrm;uniform mat4 u_mvp;"
             "varying vec3 v_nrm;void main(){v_nrm=a_nrm;gl_Position=u_mvp*vec4(a_pos,1.0);}")
FS_MESH_L = ("#version 120\nvarying vec3 v_nrm;uniform vec4 u_color;void main(){"
             "vec3 n=normalize(v_nrm);vec3 l=normalize(vec3(0.4,0.6,0.8));"
             "float d=0.40+0.60*abs(dot(n,l));gl_FragColor=vec4(u_color.rgb*d,u_color.a);}")
VS_LINE_L = ("#version 120\nattribute vec3 a_pos;attribute vec4 a_col;uniform mat4 u_mvp;"
             "varying vec4 v_col;void main(){v_col=a_col;gl_Position=u_mvp*vec4(a_pos,1.0);}")
FS_LINE_L = "#version 120\nvarying vec4 v_col;\nvoid main(){gl_FragColor=v_col;}"


def gl_available() -> bool:
    if os.environ.get("MZ_NO_GL"):
        return False
    try:
        from OpenGL import GL  # noqa: F401
        return True
    except Exception:
        return False


def to_gl(v):
    from minizemax.analysis.scene3d import to_gl as _t
    return _t(v)


def _expand(verts, faces):
    tri = verts[faces.reshape(-1)].astype(np.float64)
    a, b, c = tri[0::3], tri[1::3], tri[2::3]
    n = np.cross(b - a, c - a)
    ln = np.linalg.norm(n, axis=1, keepdims=True)
    n = n / np.where(ln > 0, ln, 1.0)
    return tri, np.repeat(n, 3, axis=0)


def _lookat(eye, center, up):
    f = center - eye; f = f / np.linalg.norm(f)
    s = np.cross(f, up); s = s / np.linalg.norm(s)
    u = np.cross(s, f)
    M = np.eye(4)
    M[0, :3], M[1, :3], M[2, :3] = s, u, -f
    M[0, 3], M[1, 3], M[2, 3] = -s @ eye, -u @ eye, f @ eye
    return M


def _persp(fovy, aspect, near, far):
    f = 1.0 / np.tan(np.deg2rad(fovy) / 2.0)
    M = np.zeros((4, 4))
    M[0, 0] = f / aspect; M[1, 1] = f
    M[2, 2] = (far + near) / (near - far); M[2, 3] = 2 * far * near / (near - far)
    M[3, 2] = -1.0
    return M


class GLView3D(QOpenGLWidget):
    objectMenuRequested = Signal(int, object)
    PICK_PX = 40.0
    PAD_FACTOR = 1.5
    DIST_MIN_F = 0.05
    DIST_MAX_F = 25.0
    EL_LIMIT = 89.0

    def __init__(self, parent=None):
        super().__init__(parent)
        fmt = QSurfaceFormat()
        fmt.setVersion(4, 6)
        prof = getattr(QSurfaceFormat, "CoreProfile", None)
        if prof is None:
            prof = QSurfaceFormat.OpenGLContextProfile.CoreProfile
        fmt.setProfile(prof)
        fmt.setDepthBufferSize(24)
        fmt.setSamples(4)                      # MSAA: гладкие лучи и кромки
        self.setFormat(fmt)
        self._scene = None
        self._drawables = []
        self._dirty = True
        self._ready = False
        self._core = True
        self._dbg_printed = False
        self.center = np.zeros(3)
        self.distance = 300.0
        self.azimuth = -60.0
        self.elevation = 20.0
        self._last = (0, 0)
        self._panning = False
        self._bbox_min = np.full(3, -1e9)
        self._bbox_max = np.full(3, 1e9)
        self._diag = 300.0
        self.setSizePolicy(SP_EXPANDING, SP_EXPANDING)
        self.setMinimumSize(320, 240)
        # Wayland: тултип на GL-виджете = hover-popup = лишние коммиты = мерцание.
        # Подсказку переносим в статус-бар главного окна при входе во вкладку.
        self.setAttribute(WA_OPAQUE, True)
        self.setAttribute(WA_NOSYSBG, True)
        self.setMouseTracking(False)

    def set_scene(self, scene) -> None:
        self._scene = scene
        vs = [to_gl(m.verts) for m in scene.meshes]
        vs += [to_gl(np.asarray(P, np.float64)) for P, _ in (scene.polylines or [])]
        V = np.concatenate(vs, 0) if vs else np.zeros((1, 3))
        self._bbox_min = V.min(0)
        self._bbox_max = V.max(0)
        self._diag = max(float(np.linalg.norm(self._bbox_max - self._bbox_min)), 1.0)
        self.reset_view(fit_only=True)
        self._dirty = True
        self.update()

    def reset_view(self, fit_only: bool = False) -> None:
        self.center = 0.5 * (self._bbox_min + self._bbox_max)
        self.distance = self._diag * 1.35
        if not fit_only:
            self.azimuth, self.elevation = -60.0, 20.0
        self._clamp()
        self.update()

    def _clamp(self) -> None:
        self.elevation = float(np.clip(self.elevation, -self.EL_LIMIT, self.EL_LIMIT))
        self.distance = float(np.clip(self.distance,
                                      self.DIST_MIN_F * self._diag,
                                      self.DIST_MAX_F * self._diag))
        pad = self.PAD_FACTOR * self._diag
        self.center = np.clip(self.center, self._bbox_min - pad, self._bbox_max + pad)

    def initializeGL(self):
        ver = gl.glGetString(gl.GL_VERSION).decode()
        mver = re.match(r"(\d+)\.(\d+)", ver)   # "4.6 (Core Profile) Mesa ..." и т.п.
        maj, mino = (int(mver.group(1)), int(mver.group(2))) if mver else (1, 0)
        self._core = (maj, mino) >= (3, 3)
        self._vao_ok = (maj, mino) >= (3, 0)   # VAO есть уже в GL 3.0
        if os.environ.get("MZ_GL_DEBUG"):
            print(f"[GL] context: {ver} core={self._core}")
        gl.glEnable(gl.GL_DEPTH_TEST)
        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        gl.glClearColor(0.07, 0.07, 0.09, 1.0)
        if self._core:
            try:
                self._prog_mesh = self._compile(VS_MESH_C, FS_MESH_C, None)
                self._prog_line = self._compile(VS_LINE_C, FS_LINE_C, None)
            except RuntimeError:
                self._core = False
        if not self._core:
            self._prog_mesh = self._compile(VS_MESH_L, FS_MESH_L, ["a_pos", "a_nrm"])
            self._prog_line = self._compile(VS_LINE_L, FS_LINE_L, ["a_pos", "a_col"])
        self._u_mvp_m = gl.glGetUniformLocation(self._prog_mesh, "u_mvp")
        self._u_col_m = gl.glGetUniformLocation(self._prog_mesh, "u_color")
        self._u_mvp_l = gl.glGetUniformLocation(self._prog_line, "u_mvp")
        self._ready = True
        self._dirty = True

    def _shader(self, kind, src):
        sh = gl.glCreateShader(kind)
        gl.glShaderSource(sh, src)
        gl.glCompileShader(sh)
        if gl.glGetShaderiv(sh, gl.GL_COMPILE_STATUS) == 0:
            raise RuntimeError(gl.glGetShaderInfoLog(sh).decode())
        return sh

    def _compile(self, vs, fs, attribs):
        prog = gl.glCreateProgram()
        sv, sf = self._shader(gl.GL_VERTEX_SHADER, vs), self._shader(gl.GL_FRAGMENT_SHADER, fs)
        gl.glAttachShader(prog, sv); gl.glAttachShader(prog, sf)
        if attribs:
            for i, name in enumerate(attribs):
                gl.glBindAttribLocation(prog, i, name)
        gl.glLinkProgram(prog)
        if gl.glGetProgramiv(prog, gl.GL_LINK_STATUS) == 0:
            raise RuntimeError(gl.glGetProgramInfoLog(prog).decode())
        gl.glDeleteShader(sv); gl.glDeleteShader(sf)
        return prog

    def _build(self):
        for d in self._drawables:
            gl.glDeleteBuffers(1, [d["vbo"]])
            if d.get("vao"):
                gl.glDeleteVertexArrays(1, [d["vao"]])
        self._drawables = []
        for m in self._scene.meshes:
            tri, nrm = _expand(m.verts, m.faces)
            arr = np.concatenate([to_gl(tri), to_gl(nrm)], 1).astype(np.float32)
            self._add_drawable(arr, 24, dict(kind="mesh", count=len(arr),
                                             color=m.color, trans=(m.gl_options == "translucent"),
                                             cen=to_gl(tri).mean(axis=0)))
        for P, col in (self._scene.polylines or []):
            arr = np.concatenate([to_gl(P), np.tile(col, (len(P), 1))], 1).astype(np.float32)
            self._add_drawable(arr, 28, dict(kind="line", count=len(arr)))

    def _add_drawable(self, arr, stride, d):
        vbo = gl.glGenBuffers(1)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, vbo)
        gl.glBufferData(gl.GL_ARRAY_BUFFER, arr.nbytes, arr, gl.GL_STATIC_DRAW)
        d["vbo"] = vbo
        d["stride"] = stride
        d["vao"] = 0
        if getattr(self, "_vao_ok", self._core):
            vao = gl.glGenVertexArrays(1)
            gl.glBindVertexArray(vao)
            gl.glBindBuffer(gl.GL_ARRAY_BUFFER, vbo)
            gl.glEnableVertexAttribArray(0)
            gl.glEnableVertexAttribArray(1)
            gl.glVertexAttribPointer(0, 3, gl.GL_FLOAT, gl.GL_FALSE, stride, ctypes.c_void_p(0))
            off = 12 if stride == 24 else 12
            gl.glVertexAttribPointer(1, 3 if stride == 24 else 4, gl.GL_FLOAT, gl.GL_FALSE,
                                     stride, ctypes.c_void_p(off))
            gl.glBindVertexArray(0)
            d["vao"] = vao
        self._drawables.append(d)

    def _current_mvp(self, w, h):
        near = max(self._diag * 1e-3, self.distance * 0.01)
        far = self.distance * 20.0 + self._diag * 10.0
        proj = _persp(FOV, w / h, near, far)
        el, az = np.deg2rad(self.elevation), np.deg2rad(self.azimuth)
        dirv = np.array([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)])
        eye = self.center + dirv * self.distance
        mvp = proj @ _lookat(eye, self.center, np.array([0.0, 0.0, 1.0]))
        return mvp, eye

    def paintGL(self):
        if not self._ready:
            return
        dpr = self.devicePixelRatio()
        w = max(1, int(round(self.width() * dpr)))
        h = max(1, int(round(self.height() * dpr)))
        gl.glViewport(0, 0, w, h)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
        if w < 2 or h < 2 or self._scene is None:
            return
        if self._dirty:
            self._build()
            self._dirty = False
        if os.environ.get("MZ_GL_DEBUG") and not self._dbg_printed:
            self._dbg_printed = True
            print(f"[GL] first paint: {w}x{h} drawables={len(self._drawables)} core={self._core}")
        mvp, eye = self._current_mvp(w, h)
        mvp = mvp.astype(np.float32)
        gl.glUseProgram(self._prog_mesh)
        gl.glUniformMatrix4fv(self._u_mvp_m, 1, gl.GL_TRUE, mvp)
        for d in self._drawables:
            if d["kind"] == "mesh" and not d["trans"]:
                self._draw_mesh(d)
        gl.glUseProgram(self._prog_line)
        gl.glUniformMatrix4fv(self._u_mvp_l, 1, gl.GL_TRUE, mvp)
        for d in self._drawables:
            if d["kind"] == "line":
                self._draw_line(d)
        trans = [d for d in self._drawables if d["kind"] == "mesh" and d["trans"]]
        trans.sort(key=lambda d: -float(np.dot(d["cen"] - eye, d["cen"] - eye)))
        gl.glDepthMask(gl.GL_FALSE)
        gl.glUseProgram(self._prog_mesh)
        for d in trans:
            self._draw_mesh(d)
        gl.glDepthMask(gl.GL_TRUE)
        gl.glUseProgram(0)

    def _draw_mesh(self, d):
        if d.get("vao"):
            gl.glBindVertexArray(d["vao"])
        else:
            gl.glBindBuffer(gl.GL_ARRAY_BUFFER, d["vbo"])
            gl.glEnableVertexAttribArray(0); gl.glEnableVertexAttribArray(1)
            gl.glVertexAttribPointer(0, 3, gl.GL_FLOAT, gl.GL_FALSE, 24, ctypes.c_void_p(0))
            gl.glVertexAttribPointer(1, 3, gl.GL_FLOAT, gl.GL_FALSE, 24, ctypes.c_void_p(12))
        gl.glUniform4f(self._u_col_m, *d["color"])
        gl.glDrawArrays(gl.GL_TRIANGLES, 0, d["count"])
        if d.get("vao"):
            gl.glBindVertexArray(0)
        else:
            gl.glDisableVertexAttribArray(0); gl.glDisableVertexAttribArray(1)

    def _draw_line(self, d):
        if d.get("vao"):
            gl.glBindVertexArray(d["vao"])
        else:
            gl.glBindBuffer(gl.GL_ARRAY_BUFFER, d["vbo"])
            gl.glEnableVertexAttribArray(0); gl.glEnableVertexAttribArray(1)
            gl.glVertexAttribPointer(0, 3, gl.GL_FLOAT, gl.GL_FALSE, 28, ctypes.c_void_p(0))
            gl.glVertexAttribPointer(1, 4, gl.GL_FLOAT, gl.GL_FALSE, 28, ctypes.c_void_p(12))
        gl.glDrawArrays(gl.GL_LINE_STRIP, 0, d["count"])
        if d.get("vao"):
            gl.glBindVertexArray(0)
        else:
            gl.glDisableVertexAttribArray(0); gl.glDisableVertexAttribArray(1)

    def resizeGL(self, w, h):
        self.update()

    def _cam_basis(self):
        el, az = np.deg2rad(self.elevation), np.deg2rad(self.azimuth)
        f = -np.array([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)])
        s = np.cross(f, np.array([0.0, 0.0, 1.0])); s /= np.linalg.norm(s)
        return s, np.cross(s, f)

    @staticmethod
    def _xy(e):
        """Локальные координаты мыши кросс-версионно: PyQt6 position()->QPointF,
        PyQt5 без position() -> x()/y(). position() — МЕТОД, его надо ВЫЗВАТЬ."""
        pos = getattr(e, "position", None)
        if callable(pos):
            pos = pos()
        if pos is not None and hasattr(pos, "x"):
            return int(pos.x()), int(pos.y())
        return int(e.x()), int(e.y())

    def mousePressEvent(self, e):
        self._last = self._xy(e)
        mid = bool(e.buttons() & _MID)
        shift = bool(e.modifiers() & _SHIFT)
        self._panning = mid or (shift and bool(e.buttons() & _LEFT))

    def mouseMoveEvent(self, e):
        x, y = self._xy(e)
        dx, dy = x - self._last[0], y - self._last[1]
        self._last = (x, y)
        if self._panning:
            s, u = self._cam_basis()
            upp = 2.0 * self.distance * np.tan(np.deg2rad(FOV) / 2.0) / max(1, self.height())
            self.center = self.center + (-dx * s + dy * u) * upp
        elif bool(e.buttons() & _LEFT):
            self.azimuth += dx * 0.5
            self.elevation -= dy * 0.5
        self._clamp()
        self.update()

    def mouseDoubleClickEvent(self, e):
        self.reset_view()

    @staticmethod
    def _ev_points(e):
        lp = getattr(e, "position", None)
        lp = lp() if callable(lp) else getattr(e, "pos", lambda: None)()
        gp = getattr(e, "globalPosition", None)
        gp = gp() if callable(gp) else getattr(e, "globalPos", lambda: None)()
        to_p = lambda p: p.toPoint() if hasattr(p, "toPoint") else p
        return to_p(lp), to_p(gp)

    def _pick_lde_row(self, lpos):
        if self._scene is None or not self._drawables: return None
        w, h = max(1, self.width()), max(1, self.height())
        mvp, _ = self._current_mvp(w, h)
        best_i, best_d = None, self.PICK_PX
        for k, m in enumerate(self._scene.meshes):
            if k >= len(self._drawables): break
            cen = self._drawables[k].get("cen")
            if cen is None: continue
            clip = mvp @ np.array([cen[0], cen[1], cen[2], 1.0], float)
            if clip[3] <= 1e-9: continue
            nx, ny, _ = clip[:3] / clip[3]
            sx, sy = (nx * 0.5 + 0.5) * w, (1.0 - (ny * 0.5 + 0.5)) * h
            d = float(np.hypot(sx - lpos.x(), sy - lpos.y()))
            if d < best_d: best_d, best_i = d, k
        if best_i is None: return None
        name = self._scene.meshes[best_i].name
        if name == "detector": return -1
        import re as _re
        mm = _re.match(r"(?:surf|mirror|stop|rim)(\\d+)", name)
        return int(mm.group(1)) + 1 if mm else None

    def contextMenuEvent(self, e):
        lpos, gpos = self._ev_points(e)
        if gpos is None: gpos = self.mapToGlobal(lpos)
        row = self._pick_lde_row(lpos)
        if row is None:
            from minizemax.ui.qt import QMenu
            from minizemax.ui.object_actions import menu_exec
            m = QMenu(self)
            m.addAction("Reset view").triggered.connect(lambda: self.reset_view())
            menu_exec(m, gpos); e.accept(); return
        self.objectMenuRequested.emit(row, gpos); e.accept()

    def wheelEvent(self, e):
        self.distance *= (1.0 - 0.001 * e.angleDelta().y())
        self._clamp()
        self.update()
