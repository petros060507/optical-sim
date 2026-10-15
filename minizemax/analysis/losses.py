"""Loss budget: счётчики причин гибели лучей."""
from __future__ import annotations
from minizemax.core.bundle import STATUS_ALIVE, STATUS_BLOCKED, STATUS_TIR, STATUS_MISS
from minizemax.engine.tracer import trace_field

NAMES = {STATUS_ALIVE: "alive",
         STATUS_BLOCKED: "blocked(aperture)",
         STATUS_TIR: "tir",
         STATUS_MISS: "miss(no hit)"}


def loss_counts(res) -> dict:
    st = res.bundle.status
    return {name: int((st == code).sum()) for code, name in NAMES.items()}


def loss_table(pres) -> str:
    built = pres.build()
    sd = pres.sysdata
    tot = {name: 0 for name in NAMES.values()}
    ntot = 0
    for fi in range(len(sd.fields)):
        for wi in range(len(sd.wavelengths)):
            res = trace_field(built, fi, wi)
            c = loss_counts(res)
            ntot += len(res.bundle.status)
            for k, v in c.items():
                tot[k] += v
    L = ["--- Loss budget (fields x wavelengths) ---"]
    for code, name in NAMES.items():
        v = tot[name]
        L.append(f"  {name:18s} {v:6d}  ({100.0 * v / max(1, ntot):5.1f}%)")
    L.append(f"  {'total':18s} {ntot:6d}")
    return "\n".join(L)
