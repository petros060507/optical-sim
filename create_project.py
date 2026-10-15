#!/usr/bin/env python3
"""fix_flicker2.py: убирает мерцание стекла (back-to-front сортировка alpha +
cen-центроиды) regex-патчами, нечувствительными к форматированию view3d_qt.py."""
import pathlib
import py_compile
import re

P = pathlib.Path("minizemax/ui/view3d_qt.py")
s = P.read_text(encoding="utf-8")
changed = False

# ── (A) мешам добавляем центроид cen (для сортировки по глубине) ──────────────
if "cen=to_gl(tri).mean(axis=0)" in s:
    print("already  (A) cen")
else:
    patA = re.compile(r'trans=\(m\.gl_options\s*==\s*"translucent"\)\)\)')
    if patA.search(s):
        s = patA.sub(
            'trans=(m.gl_options == "translucent"),\n'
            '                                        cen=to_gl(tri).mean(axis=0)))',
            s, count=1)
        changed = True
        print("patched  (A) cen")
    else:
        print("NOT FOUND (A) — нет блока trans=(m.gl_options==\"translucent\")))")

# ── (B) прозрачные меши: сортировка от дальних к ближним каждый кадр ──────────
if "trans.sort(" in s:
    print("already  (B) sort")
else:
    patB = re.compile(r'gl\.glDepthMask\(gl\.GL_FALSE\).*?gl\.glDepthMask\(gl\.GL_TRUE\)',
                      re.DOTALL)
    replB = (
        'gl.glDepthMask(gl.GL_FALSE)\n'
        '        gl.glUseProgram(self._prog_mesh)\n'
        '        eye = self.center + dirv * self.distance\n'
        '        trans = [d for d in self._drawables if d["kind"] == "mesh" and d["trans"]]\n'
        '        trans.sort(key=lambda d: -float(np.dot(d["cen"] - eye, d["cen"] - eye)))\n'
        '        for d in trans:                      # back-to-front: стабильный alpha\n'
        '            self._draw_mesh(d)\n'
        '        gl.glDepthMask(gl.GL_TRUE)')
    if patB.search(s):
        s = patB.sub(replB, s, count=1)
        changed = True
        print("patched  (B) back-to-front")
    else:
        print("NOT FOUND (B) — нет блока DepthMask(FALSE)..DepthMask(TRUE)")

if changed:
    P.write_text(s, encoding="utf-8")
py_compile.compile(str(P), doraise=True)
print("py_compile OK")

# ── диагностика: если что-то не нашлось — дамп релевантных блоков ─────────────
if not (("cen=to_gl(tri).mean(axis=0)" in s) and ("trans.sort(" in s)):
    print("\n=== ДАМП для подгонки (пришли этот вывод) ===")
    lines = s.splitlines()
    for marker in ("def _build", "def paintGL"):
        i = next((k for k, l in enumerate(lines) if marker in l), None)
        if i is None:
            print(f"[{marker}] НЕ НАЙДЕН")
            continue
        j = next((k for k in range(i + 1, len(lines))
                  if lines[k].startswith("    def ")), len(lines))
        print(f"--- {marker} ---")
        print("\n".join(lines[i:j]))