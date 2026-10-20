"""gpuprobe: что железо реально даёт для рендера и трассировки."""
from __future__ import annotations
import shutil
import subprocess


def gl_info():
    from minizemax.ui.qt import QApplication, QOpenGLWidget, QSurfaceFormat
    app = QApplication.instance() or QApplication([])
    fmt = QSurfaceFormat()
    fmt.setVersion(4, 6)
    prof = getattr(QSurfaceFormat, "CoreProfile", None)
    if prof is None:
        prof = QSurfaceFormat.OpenGLContextProfile.CoreProfile
    fmt.setProfile(prof)
    QSurfaceFormat.setDefaultFormat(fmt)
    w = QOpenGLWidget()
    w.resize(64, 64)
    w.show()
    w.makeCurrent()
    from OpenGL import GL as gl
    info = dict(version=gl.glGetString(gl.GL_VERSION).decode(),
                renderer=gl.glGetString(gl.GL_RENDERER).decode(),
                glsl=gl.glGetString(gl.GL_SHADING_LANGUAGE_VERSION).decode())
    w.doneCurrent()
    return info


def vulkan_info():
    exe = shutil.which("vulkaninfo")
    if not exe:
        return None
    try:
        out = subprocess.run([exe, "--summary"], capture_output=True,
                             text=True, timeout=20).stdout
    except Exception:
        return None
    devs, rt = [], False
    for line in out.splitlines():
        s = line.strip()
        if s.startswith("deviceName"):
            devs.append(s.split("=", 1)[-1].strip())
        if "VK_KHR_ray_tracing_pipeline" in s or "VK_KHR_acceleration_structure" in s:
            rt = True
    return {"devices": devs[:3], "rt": rt}


def report() -> str:
    L = ["=== GPU PROBE ==="]
    try:
        gi = gl_info()
        L += [f"OpenGL : {gi['version']}", f"Renderer: {gi['renderer']}", f"GLSL   : {gi['glsl']}"]
    except Exception as e:  # noqa: BLE001
        L.append(f"OpenGL : unavailable ({e})")
    vk = vulkan_info()
    if vk:
        L.append(f"Vulkan : {vk['devices']}")
        L.append(f"RT extensions (RT-ядра): {'yes' if vk['rt'] else 'no'}")
    else:
        L.append("Vulkan : vulkaninfo not found (apt install vulkan-tools)")
    try:
        from minizemax.gpu.kompute_trace import kompute_available
        ok, why = kompute_available()
        L.append(f"Kompute (Vulkan compute): {'available' if ok else 'unavailable: ' + why}")
    except Exception as e:  # noqa: BLE001
        L.append(f"Kompute: {e}")
    try:
        from minizemax.gpu.gl_compute_trace import gl_compute_available
        ok, why = gl_compute_available()
        L.append(f"GL compute (4.3+): {'available' if ok else 'unavailable: ' + why}")
    except Exception as e:  # noqa: BLE001
        L.append(f"GL compute: {e}")
    L += ["",
          "Verdict: последовательная аналитическая трассировка не требует BVH ->",
          "RT-ядра бесполезны; тензорные ядра исполняют GEMM и не ускоряют per-ray",
          "замкнутые формулы; Kompute compute-шейдер уже загружает параллельные ALU.",
          "Тензорные ядра имели бы смысл только в нейро-стадии (denoise/surrogate)."]
    return "\n".join(L)
