"""Redraw the spectrum, graphene and tolerance figures from data/*.csv.

Run from the repository root: python scripts/plot_figures.py
Needs numpy and matplotlib.
"""
import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA, FIG = ROOT / "data", ROOT / "figures"
CONE, SINGLE, DUAL = "#8c8c8c", "#8fb8de", "#1f4e9c"
plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False})

HBAR = 1.054571817e-34  # J s
Q = 1.602176634e-19  # C
KB_EV = 8.617333262e-5  # eV/K
SIGMA0 = Q**2 / (4 * HBAR)


def read(name):
    with open(DATA / name, newline="") as f:
        return list(csv.DictReader(f))


def re_sigma(ef_ev, wavelength_nm=445.0, temp=300.0, tau=50e-15):
    """Real part of the graphene Kubo conductivity, in units of e^2/(4 hbar)."""
    hw = 1239.841984 / wavelength_nm  # eV
    w = hw * Q / HBAR
    kt = KB_EV * temp
    inter = 0.5 * (np.tanh((hw + 2 * ef_ev) / (4 * kt)) + np.tanh((hw - 2 * ef_ev) / (4 * kt)))
    weight = 2 * kt * np.log(2 * np.cosh(ef_ev / (2 * kt)))  # eV
    intra = (Q**2 / (np.pi * HBAR**2)) * (weight * Q) * (1 / tau) / (w**2 + 1 / tau**2) / SIGMA0
    return inter + intra


def incident_field(power=1.0, waist=500e-9, n=1.4656, z0=376.73):
    """Peak |E| of an l = 1 Laguerre-Gaussian beam in SiO2."""
    peak_intensity = 2 * power / (np.pi * waist**2) * np.exp(-1)
    return np.sqrt(2 * z0 / n * peak_intensity)


def spectrum():
    rows = read("spectrum_aperture_intensity.csv")
    wl = [float(r["wavelength_nm"]) for r in rows]
    c, s, d = (np.array([float(r[k]) for r in rows]) for k in ("cone", "single_arm", "dual_arm"))
    fig, (a, b) = plt.subplots(2, 1, figsize=(7, 6), sharex=True, height_ratios=[2, 1])
    a.semilogy(wl, d, "o-", color=DUAL, lw=2.2, label=f"Dual-arm spiral (mean {d.mean():.2f})")
    a.semilogy(wl, s, "o-", color=SINGLE, label=f"Single-arm spiral (mean {s.mean():.2f})")
    a.semilogy(wl, c, "o-", color=CONE, label=f"Tapered (mean {c.mean():.3f})")
    a.axhline(1, color="0.6", ls=":")
    a.axvline(445, color="0.6", ls="--")
    a.text(446, 3.0, "design wavelength 445 nm", color="0.35", va="top")
    a.set_ylabel(r"$\langle|E|^2\rangle_{ap}/|E_{inc}|^2$")
    a.set_ylim(0.012, 3.5)
    a.legend(frameon=False, loc="lower left")
    b.plot(wl, d / c, "o-", color=DUAL)
    b.set_xlabel("Wavelength (nm)")
    b.set_ylabel("Dual-arm / tapered")
    b.annotate("the tapered probe is dark here", (470, (d / c)[7]), (405, 30),
               arrowprops={"arrowstyle": "->"})
    print(f"gain per wavelength {(d/c).min():.1f}-{(d/c).max():.1f}, "
          f"ratio of band means {d.mean()/c.mean():.1f}")
    fig.tight_layout()
    fig.savefig(FIG / "fig4_spectrum.png", dpi=200)


def graphene():
    rows = read("graphene_absorption_vs_Ef.csv")
    ef = [float(r["E_f_eV"]) for r in rows]
    dual = [float(r["P_g_norm_dual_arm"]) for r in rows]
    cone = [float(r["P_g_norm_cone"]) for r in rows]
    x = np.linspace(0.0, 2.0, 801)
    ref = re_sigma(0.2)
    print(f"Kubo Re sigma(0.2 eV) / Re sigma(1.7 eV) = {ref / re_sigma(1.7):.0f}; "
          f"simulated {dual[0] / dual[-1]:.0f}")
    fig, (a, b) = plt.subplots(1, 2, figsize=(12, 4.8))
    a.semilogy(x, re_sigma(x) / ref, color="0.3", lw=2,
               label=r"Kubo Re $\sigma_g(E_f)$ / Re $\sigma_g$(0.2 eV)")
    a.semilogy(ef, cone, "s", ms=10, mfc="none", mec=SINGLE, mew=2, label="Simulated $P_g$, tapered")
    a.semilogy(ef, dual, "o", ms=5, color=DUAL, label="Simulated $P_g$, dual-arm")
    a.axvline(1.393, color="0.5", ls="--")
    a.text(1.36, 0.035, "Pauli blocking\n" + r"$E_f=\hbar\omega/2=1.393$ eV", ha="right")
    a.set_xlabel(r"Fermi level $E_f$ (eV)")
    a.set_ylabel("Graphene absorption (normalized to 0.2 eV)")
    a.set_ylim(1e-3, 3)
    a.legend(frameon=False, loc="lower left")
    a.set_title("(a) Graphene absorption switches by 269× at 445 nm", loc="left")

    mod = read("graphene_modulation.csv")
    names = [r"Graphene own absorption $P_g$", r"Tip $|E_t|^2$", "Tip total field (dual-arm)",
             r"$P_{NW}$, j = +1, 3 layers", r"$P_{NW}$, j = 0, 1 layer", r"$P_{NW}$, j = +1, 1 layer"]
    vals = [float(r["modulation_percent"]) for r in mod]
    y = np.arange(len(vals))[::-1]
    b.barh(y, vals, color=[DUAL] + [CONE] * 5)
    b.set_xscale("log")
    b.set_xlim(0.05, 3e5)
    b.set_yticks(y, names)
    labels = ["269× (24 dB)", "9%", "1.4%", "0.33%", "0.17%", "0.14%"]
    for yi, v, t in zip(y, vals, labels):
        b.text(v * 1.3, yi, t, va="center", bbox={"fc": "white", "ec": "none", "pad": 1})
    b.axvline(2.3, color="#c0392b", ls=":")
    b.text(2.8, 0.0, r"monolayer limit $\pi\alpha\approx2.3\%$", color="#c0392b", va="center")
    b.set_xlabel(r"Modulation, $E_f$ = 0.2 → 1.7 eV (%)")
    b.set_title("(b) Large own absorption, small external effect", loc="left")
    fig.tight_layout()
    fig.savefig(FIG / "fig6_graphene.png", dpi=200)


def tolerance():
    rows = read("tolerance_P_NW.csv")[::-1]
    fig, ax = plt.subplots(figsize=(8, 4.6))
    y, ticks, last = 0.0, {}, None
    for r in rows:
        if r["parameter"] != last:
            y += 0.5
            last = r["parameter"]
        v = float(r["change_percent"])
        ax.barh(y, v, color=DUAL if v > 0 else SINGLE)
        ax.text(v + (0.12 if v >= 0 else -0.12), y, f"{r['variation'].replace('lambda_spp', 'λspp').replace('+/-', '±')}: {v:+g}%", va="center",
                ha="left" if v >= 0 else "right", fontsize=9)
        ticks.setdefault(r["parameter"], []).append(y)
        y += 1
    ax.axvspan(-5, 5, color="0.92", zorder=0)
    ax.axvline(0, color="k", lw=1)
    ax.set_yticks([sum(v) / len(v) for v in ticks.values()], list(ticks))
    ax.set_xlim(-8, 8)
    ax.set_xlabel(r"Change in $P_{NW}$ (%), dual-arm, j = 0")
    ax.set_title("Tested variations: all within ±5% (see tolerance_P_NW.csv for the ranges)", loc="left", fontsize=11)
    fig.tight_layout()
    fig.savefig(FIG / "fig8_tolerance.png", dpi=200)


if __name__ == "__main__":
    print(f"incident peak |E| = {incident_field():.3g} V/m")
    spectrum()
    graphene()
    tolerance()
