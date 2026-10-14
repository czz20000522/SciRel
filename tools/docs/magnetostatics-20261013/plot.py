"""Render monochrome chapter figures from recorded results; no science execution."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

root = Path(__file__).resolve().parent
x = json.loads((root/'results.json').read_text())
plt.rcParams.update({'font.size': 11, 'svg.fonttype': 'none', 'axes.spines.top': False,
                     'axes.spines.right': False, 'figure.facecolor': 'white'})
z = np.array(x['z_m'])
single, pair = np.array(x['single_BZ_T']), np.array(x['pair_BZ_T'])
fig, ax = plt.subplots(figsize=(8, 3.6), layout='constrained')
ax.plot(z, single*1e3, color='black', label='Numerical field')
analytic = 4*np.pi*1e-7*1000*.35**2/(2*(.35**2+z*z)**1.5)
ax.plot(z[::10], analytic[::10]*1e3, 'o', color='black', markerfacecolor='white', label='Axis formula')
ax.set(xlabel='Z (m)', ylabel='Bz (mT)'); ax.legend(frameon=False); ax.grid(alpha=.15)
fig.savefig(root/'single.svg'); plt.close(fig)
fig, axs = plt.subplots(1, 2, figsize=(9, 3.6), layout='constrained')
axs[0].plot(z, single/x['center_single_T'], 'k--', label='Single loop')
axs[0].plot(z, pair/x['center_pair_T'], 'k-', label='Equal-current pair')
axs[0].set(xlim=(-.2,.2), ylim=(.6,1.03), xlabel='Z (m)', ylabel='Bz / Bz(0)')
axs[0].legend(frameon=False, fontsize=9)
axs[1].plot(z, np.array(x['opposed_BZ_T'])*1e3, 'k-')
axs[1].axhline(0, color='black', lw=.5); axs[1].set(xlabel='Z (m)', ylabel='Bz (mT)', title='Opposite currents')
for ax in axs: ax.grid(alpha=.15)
fig.savefig(root/'pair.svg'); plt.close(fig)
fig, ax = plt.subplots(figsize=(7, 4.5), layout='constrained')
bz = np.array(x['rectangle_BZ_T'])*1e3
im = ax.contourf(x['r_m'], x['grid_z_m'], bz, levels=12, cmap='Greys')
contours = ax.contour(x['r_m'], x['grid_z_m'], bz, levels=6, colors='black', linewidths=.6)
ax.clabel(contours, fontsize=9, fmt='%.2f')
fig.colorbar(im, ax=ax, label='Bz (mT)')
ax.set(xlabel='R (m)', ylabel='Z (m)', aspect='equal')
fig.savefig(root/'rectangle.svg'); plt.close(fig)
