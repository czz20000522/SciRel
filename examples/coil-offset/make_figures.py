#!/usr/bin/env python3
"""Draw the report figures. Dense grids here are for visualization only.

Every reported metric still comes from the fixed points in data/summary.json.
Run from a checkout: PYTHONPATH=src python examples/coil-offset/make_figures.py
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap

from solve import GRID_R, GRID_Z, RADIUS, REFERENCE, STATES, field

HERE = Path(__file__).resolve().parent
OUT = HERE / "figures"
NOMINAL, OFFSET, MUTED, INK, SECONDARY, GRID = "#2a78d6", "#eb6834", "#a3a29a", "#0b0b0b", "#52514e", "#e6e5e0"
DIVERGING = LinearSegmentedColormap.from_list("cool_warm", ["#1c5cab", "#8fb8ec", "#f0efec", "#f2a988", "#b5441a"])
LABELS = {"nominal": "Nominal: rings at Z = -0.25, +0.25 m", "offset": "Offset: rings at Z = -0.25, +0.27 m"}
SHORT = {"nominal": "Nominal", "offset": "Offset"}

plt.rcParams.update({
    "font.size": 10, "axes.edgecolor": MUTED, "axes.labelcolor": SECONDARY, "axes.titlesize": 11,
    "axes.titlecolor": INK, "xtick.color": SECONDARY, "ytick.color": SECONDARY, "axes.spines.top": False,
    "axes.spines.right": False, "figure.facecolor": "white", "savefig.dpi": 160, "savefig.bbox": "tight",
    "legend.frameon": False,
})


def grid_map(rings, r_axis, z_axis):
    r, z = np.meshgrid(r_axis, z_axis)
    result = field(rings, np.column_stack((r.ravel(), z.ravel())))
    return r, z, {key: result[key].reshape(r.shape) for key in ("psi", "Bz", "Br")}


def centre_box(ax, **style):
    ax.add_patch(plt.Rectangle((0, -0.10), 0.10, 0.20, fill=False, **style))


def figure_field_lines():
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.8), sharey=True, constrained_layout=True)
    r_axis, z_axis = np.linspace(0.002, 0.9, 400), np.linspace(-0.75, 0.75, 500)
    _, _, reference = grid_map(STATES["nominal"], r_axis, z_axis)
    levels = np.linspace(2e-6, np.nanpercentile(reference["psi"], 99.5), 18)
    for ax, (name, rings), color in zip(axes, STATES.items(), (NOMINAL, OFFSET)):
        r, z, values = grid_map(rings, r_axis, z_axis)
        for sign in (1, -1):
            ax.contour(sign * r, z, values["psi"], levels=levels, colors=color, linewidths=0.9)
            ax.plot([sign * RADIUS] * 2, rings, "o", color=INK, ms=6)
        ax.add_patch(plt.Rectangle((-0.10, -0.10), 0.20, 0.20, fill=False, ec=INK, lw=1.2, ls="--"))
        ax.axhline(0, color=GRID, lw=0.8, zorder=0)
        ax.set(xlabel="R (m), mirrored about the axis", title=LABELS[name], aspect="equal", xlim=(-0.9, 0.9))
    axes[0].set_ylabel("Z (m)")
    fig.savefig(OUT / "fig1_field_lines.png")
    plt.close(fig)


def figure_uniformity_map():
    fig, axes = plt.subplots(1, 2, figsize=(7.4, 5.2), sharey=True, constrained_layout=True)
    r_axis, z_axis = np.linspace(0.0, 0.20, 161), np.linspace(-0.20, 0.20, 321)
    limit = 2.0
    levels = np.linspace(-limit, limit, 41)
    for ax, (name, rings) in zip(axes, STATES.items()):
        r, z, values = grid_map(rings, r_axis, z_axis)
        bref = field(rings, [REFERENCE])["Bz"][0]
        deviation = 100 * (values["Bz"] / bref - 1)
        filled = ax.contourf(r, z, np.clip(deviation, -limit, limit), levels=levels, cmap=DIVERGING, extend="both")
        lines = ax.contour(r, z, deviation, levels=[-1, -0.25, 0.25, 1], colors=INK, linewidths=0.7)
        ax.clabel(lines, fmt="%+.2f%%", fontsize=8)
        points = np.array([(a, b) for a in GRID_R for b in GRID_Z])
        ax.plot(points[:, 0], points[:, 1], ".", color=INK, ms=4)
        ax.plot(*REFERENCE, "s", mfc="white", mec=INK, ms=6)
        centre_box(ax, ec=INK, lw=1.2, ls="--")
        ax.set(xlabel="R (m)", title=SHORT[name], aspect="equal")
    axes[0].set_ylabel("Z (m)")
    bar = fig.colorbar(filled, ax=axes, shrink=0.85, ticks=[-2, -1, 0, 1, 2])
    bar.set_label("Bz / Bref - 1 (%)")
    fig.savefig(OUT / "fig2_uniformity_map.png")
    plt.close(fig)


def figure_profiles():
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.9), constrained_layout=True)
    z_axis = np.linspace(-0.20, 0.20, 401)
    r_axis = np.linspace(0.0, 0.20, 201)
    for (name, rings), color in zip(STATES.items(), (NOMINAL, OFFSET)):
        bref = field(rings, [REFERENCE])["Bz"][0]
        axial = field(rings, np.column_stack((np.zeros_like(z_axis), z_axis)))["Bz"]
        radial = field(rings, np.column_stack((r_axis, np.zeros_like(r_axis))))["Bz"]
        short = name.capitalize()
        axes[0].plot(z_axis, axial * 1e3, color=color, lw=2, label=short)
        axes[1].plot(z_axis, 100 * (axial / bref - 1), color=color, lw=2, label=short)
        axes[2].plot(r_axis, 100 * (radial / bref - 1), color=color, lw=2, label=short)
    for ax in axes:
        ax.grid(color=GRID, lw=0.7)
        ax.set_axisbelow(True)
    for ax in axes[:2]:
        ax.axvspan(-0.10, 0.10, color=GRID, alpha=0.6, lw=0)
        ax.set_xlabel("Z (m), on the axis R = 0")
    axes[2].axvspan(0, 0.10, color=GRID, alpha=0.6, lw=0)
    axes[2].set_xlabel("R (m), in the plane Z = 0")
    axes[0].set_ylabel("Bz (mT)")
    axes[1].set_ylabel("Bz / Bref - 1 (%)")
    axes[2].set_ylabel("Bz / Bref - 1 (%)")
    axes[0].set_title("(a) Axial field strength")
    axes[1].set_title("(b) Axial shape, each state vs its own Bref")
    axes[2].set_title("(c) Radial shape, each state vs its own Bref")
    axes[0].legend(loc="lower center")
    fig.savefig(OUT / "fig3_profiles.png")
    plt.close(fig)


def figure_indicators():
    states = json.loads((HERE / "data" / "summary.json").read_text(encoding="utf-8"))["states"]
    order = [("offset", "Offset (actual)\ngap 0.52 m, centre +1 cm", OFFSET),
             ("gap_only", "Wider gap only\ngap 0.52 m, centre 0", MUTED),
             ("shift_only", "Common shift only\ngap 0.50 m, centre +1 cm", MUTED),
             ("nominal", "Nominal\ngap 0.50 m, centre 0", NOMINAL)]
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.4), sharey=True, constrained_layout=True)
    panels = (("U", 100, "Non-uniformity U at the 9 central points (%)", "{:.2f}%"),
              ("tilt_max_rad", 1e3, "Largest tilt at the 9 central points (mrad)", "{:.2f} mrad"))
    y = np.arange(len(order))
    for ax, (key, factor, title, fmt) in zip(axes, panels):
        values = [states[name][key] * factor for name, _, _ in order]
        ax.barh(y, values, color=[item[2] for item in order], height=0.55)
        for row, value in zip(y, values):
            ax.text(value + max(values) * 0.015, row, fmt.format(value), va="center", color=INK)
        ax.set_xlim(0, max(values) * 1.28)
        ax.set_title(title, loc="left")
        ax.spines["left"].set_visible(False)
        ax.tick_params(axis="y", length=0)
        ax.grid(axis="x", color=GRID, lw=0.7)
        ax.set_axisbelow(True)
    axes[0].set_yticks(y, [item[1] for item in order])
    fig.savefig(OUT / "fig4_indicators.png")
    plt.close(fig)


def main():
    OUT.mkdir(exist_ok=True)
    figure_field_lines()
    figure_uniformity_map()
    figure_profiles()
    figure_indicators()


if __name__ == "__main__":
    main()
