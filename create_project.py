#!/usr/bin/env python3
"""fix_render_chain.py: закрывает каскад NaN->warning->crash одним проходом.
1) materials: безопасный Sellmeier (arg<0 -> nan БЕЗ numpy-warning, валидный диапазон не тронут)
2) tracer:    inline t_safe (устойчив к вёрстке, чинит 'invalid value in multiply')
3) scene3d:   guard concatenate(segs/cols/_nc) -> пустые массивы правильной формы
4) pyproject: docs-совместимые ignore для безвредного шума matplotlib/Deprecation
5) тест:      build_scene не крэшит, формы согласованы, и НЕТ RuntimeWarning (локальный strict)
"""
import pathlib
import py_compile
import re

# ── 1) materials.py: безопасный sqrt ─────────────────────────────────────────
pm = pathlib.Path("minizemax/core/materials.py")
sm = pm.read_text(encoding="utf-8")
pat = re.compile(r'^([ \t]*)return np\.sqrt\(1\.0 \+ sum\(.*\)\)\s*$', re.MULTILINE)
m = pat.search(sm)
if m and "np.where(arg" not in sm:
    ind = m.group(1)
    repl = (f"{ind}arg = 1.0 + sum(b * w2 / (w2 - c) for b, c in zip(self.B, self.C))\n"
            f"{ind}# вне полосы прозрачности Sellmeier arg<0 -> n не определён (nan), но без warning\n"
            f"{ind}return np.where(arg >= 0.0, np.sqrt(np.where(arg >= 0.0, arg, 1.0)), np.nan)")
    pm.write_text(sm[:m.start()] + repl + sm[m.end():], encoding="utf-8")
    print("✓ materials.py: безопасный Sellmeier sqrt")
elif "np.where(arg" in sm:
    print("• materials.py уже защищён")
else:
    print("✗ materials.py: якорь sqrt не найден")

# ── 2) tracer.py: inline t_safe (все вхождения подстроки) ────────────────────
pt = pathlib.Path("minizemax/engine/tracer.py")
st = pt.read_text(encoding="utf-8")
new_st, n = re.subn(r"hit\.t\[:,\s*None\]\s*\*\s*b\.direction",
                    "np.where(np.isfinite(hit.t), hit.t, 0.0)[:, None] * b.direction", st)
if n:
    pt.write_text(new_st, encoding="utf-8")
    print(f"✓ tracer.py: t_safe inline ({n} вхождений)")
else:
    print("• tracer.py: паттерн hit.t[:,None]*direction не найден (возможно, уже исправлен)")

# ── 3) scene3d.py: guard concatenate ─────────────────────────────────────────
ps = pathlib.Path("minizemax/analysis/scene3d.py")
ss = ps.read_text(encoding="utf-8")
GUARDS = [
    (r"np\.concatenate\(segs\)", "(np.concatenate(segs) if segs else np.zeros((0, 2, 3), np.float32))"),
    (r"np\.concatenate\(_nc\)",  "(np.concatenate(_nc) if _nc else np.zeros((0, 2, 4), np.float32))"),
    (r"np\.concatenate\(cols\)", "(np.concatenate(cols) if cols else np.zeros((0, 2, 4), np.float32))"),
]
tot = 0
for pat_, rep in GUARDS:
    ss, k = re.subn(pat_, rep, ss)
    tot += k
if tot:
    ps.write_text(ss, encoding="utf-8")
    print(f"✓ scene3d.py: guard concatenate ({tot} правок)")
else:
    print("• scene3d.py: concatenate-якоря не найдены")

for f in (pm, pt, ps):
    py_compile.compile(str(f), doraise=True)
print("py_compile OK")

# ── 4) pyproject.toml: docs-совместимые фильтры (без глобального 'error',     ─
#      чтобы не хрупить collection на шумных либах; strict — локально в тесте) ─
pp = pathlib.Path("pyproject.toml")
sp = pp.read_text(encoding="utf-8") if pp.exists() else ""
BLOCK = ('[tool.pytest.ini_options]\n'
         'filterwarnings = [\n'
         '    "ignore:No artists with labels:UserWarning",   # matplotlib: пустой legend (безвредно)\n'
         '    "ignore::DeprecationWarning",                  # сторонние либы (Qt/mpl)\n'
         '    "ignore::PendingDeprecationWarning",\n'
         ']\n')
if "[tool.pytest.ini_options]" not in sp:
    sp = (sp.rstrip() + "\n\n" + BLOCK) if sp else BLOCK
    pp.write_text(sp, encoding="utf-8")
    print("✓ pyproject.toml: [tool.pytest.ini_options] filterwarnings")
else:
    print("• pyproject.toml: секция pytest уже есть (фильтры не дублируем)")

# ── 5) тест-регрессия: no-crash + согласованные формы + НЕТ warnings ─────────
pathlib.Path("tests").mkdir(exist_ok=True)
pathlib.Path("tests/test_render_robust.py").write_text('''
"""Регрессия рендер-цепочки: Sellmeier/tracer/scene3d не дают ни крэша, ни warnings."""
import warnings
import numpy as np
import pytest
from minizemax.system.prescription import Prescription
from minizemax.core.materials import glass, n_at
from minizemax.analysis.scene3d import build_scene

CONFIGS = ["examples/doublet.zmx-lite", "examples/cooke_triplet.yaml", "examples/fourf_4x.yaml"]


def test_sellmeier_finite_in_visible():
    # защита не должна превращать валидный диапазон в nan
    for name in ("N-BK7", "N-F2", "N-SK16"):
        for wl in (0.4861, 0.5876, 0.6563):
            n = float(n_at(glass(name), wl))
            assert np.isfinite(n) and n > 1.0, (name, wl, n)


@pytest.mark.parametrize("cfg", CONFIGS)
def test_build_scene_no_crash_no_warning(cfg):
    try:
        pres = Prescription.load(cfg)
    except FileNotFoundError:
        pytest.skip(f"нет {cfg}")
    built = pres.build()
    with warnings.catch_warnings():
        warnings.simplefilter("error")          # docs: «no warnings emitted»
        sc = build_scene(built, 0, 0, n_rays=24)
    # инвариант формы (пустые массивы допустимы, рассогласование — нет)
    assert sc.line_verts.ndim == 3 and sc.line_verts.shape[1:] == (2, 3)
    assert sc.line_colors.shape == sc.line_verts.shape[:2] + (4,)
''', encoding="utf-8")
py_compile.compile("tests/test_render_robust.py", doraise=True)
print("write tests/test_render_robust.py")

# ── диагностика: рисуются ли лучи (не валит suite, просто печатает) ───────────
print("\n--- диагностика 3D (len line_verts по конфигам) ---")
for cfg in CONFIGS:
    try:
        sc = build_scene(Prescription.load(cfg).build(), 0, 0, n_rays=24)
        print(f"  {cfg:34s} line_verts={sc.line_verts.shape}")
    except FileNotFoundError:
        print(f"  {cfg:34s} (нет файла)")
    except Exception as e:  # noqa: BLE001
        print(f"  {cfg:34s} ERROR {type(e).__name__}: {e}")