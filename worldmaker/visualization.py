import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from typing import Optional
from .classes import StellarSystem, PlanetaryBody

def plot_system_orbit_diagram(system: StellarSystem, figsize=(12, 6), dark_mode=True) -> plt.Figure:
    """
    Renders a graphical 2D orbital layout chart for a Traveller star system using matplotlib.
    Displays stars, habitable zone, planetary orbits, planet sizes, and moon counts.
    """
    # Styling setup
    if dark_mode:
        plt.style.use('dark_background')
        bg_color = '#0b0e14'
        text_color = '#e6edf3'
        hz_color = '#2ea043'
        grid_color = '#21262d'
    else:
        plt.style.use('default')
        bg_color = '#ffffff'
        text_color = '#1f2328'
        hz_color = '#1f883d'
        grid_color = '#d0d7de'

    fig, ax = plt.subplots(figsize=figsize, facecolor=bg_color)
    ax.set_facecolor(bg_color)

    primary = system.primary_star
    if not primary:
        ax.text(0.5, 0.5, "Empty System", color=text_color, ha='center', va='center')
        return fig

    # Habitable zone boundaries in AU
    hzco = primary.hzco
    hz_min = max(0.01, hzco - 0.4 * hzco)
    hz_max = hzco + 0.5 * hzco

    # Draw Habitable Zone Band
    ax.axvspan(hz_min, hz_max, color=hz_color, alpha=0.18, label='Habitable Zone (HZ)')
    ax.axvline(hzco, color=hz_color, linestyle='--', alpha=0.5, label=f'HZ Center ({hzco:.2f} AU)')

    # Draw Primary Star at origin (0.01 AU for log scale)
    star_color = '#ffcc00'
    if 'M' in primary.spectral_type: star_color = '#ff4d4d'
    elif 'K' in primary.spectral_type: star_color = '#ffaa33'
    elif 'A' in primary.spectral_type or 'F' in primary.spectral_type: star_color = '#e6f2ff'
    elif 'O' in primary.spectral_type or 'B' in primary.spectral_type: star_color = '#80b3ff'

    ax.scatter([0.02], [0], s=600, color=star_color, edgecolors='#ffffff', linewidth=1.5, zorder=5, label=f'Star: {primary.spectral_type}')
    ax.annotate(f"{primary.designation}\n({primary.spectral_type})", (0.02, 0.4), color=text_color,
                ha='center', fontsize=9, fontweight='bold')

    # Collect all placed worlds
    worlds = system.all_worlds
    if not worlds:
        ax.set_xscale('log')
        ax.set_title(f"Stellar System: {system.name}", color=text_color, fontsize=14)
        return fig

    # Colors for body types
    type_colors = {
        'Terrestrial': '#38bdf8',
        'Gas Giant': '#a855f7',
        'Planetoid Belt': '#f97316',
        'Empty': '#64748b'
    }

    x_aus = []
    y_pos = []
    
    for idx, world in enumerate(sorted(worlds, key=lambda w: w.orbit_au)):
        au = max(0.03, world.orbit_au)
        x_aus.append(au)
        y = 0.0

        btype = world.body_type
        color = type_colors.get(btype, '#94a3b8')

        # Size of marker based on world size / type
        marker_size = 120
        if btype == 'Gas Giant':
            marker_size = 320
        elif btype == 'Planetoid Belt':
            marker_size = 60
        elif btype == 'Terrestrial':
            try:
                sz = int(world.size_code, 16) if isinstance(world.size_code, str) else int(world.size_code)
                marker_size = max(80, sz * 25)
            except (ValueError, TypeError):
                marker_size = 140

        # Draw Orbit line
        ax.axvline(au, color=grid_color, linestyle=':', alpha=0.6)

        # Plot Planet Marker
        if btype == 'Planetoid Belt':
            # Scatter multiple small dots around orbit line
            belt_y = np.linspace(-0.3, 0.3, 7)
            belt_x = [au + np.random.uniform(-au*0.03, au*0.03) for _ in range(7)]
            ax.scatter(belt_x, belt_y, s=20, color=color, alpha=0.7, zorder=4)
        else:
            edge_c = '#f43f5e' if world.is_mainworld else ('#f59e0b' if world.notes else '#ffffff')
            lw = 2.0 if (world.is_mainworld or world.notes) else 0.8
            ax.scatter([au], [y], s=marker_size, color=color, edgecolors=edge_c, linewidth=lw, zorder=4)

        # Labels
        label_text = f"{world.designation}\n{world.name}\n({world.uwp.uwp_string if world.uwp and world.uwp.uwp_string else world.body_type})"
        if world.satellites:
            num_moons = len(world.satellites)
            label_text += f"\n[{num_moons} moon{'s' if num_moons>1 else ''}]"

        y_offset = 0.5 if (idx % 2 == 0) else -0.7
        ax.annotate(label_text, (au, y_offset), color=text_color, fontsize=8, ha='center',
                    bbox=dict(boxstyle='round,pad=0.2', facecolor=bg_color, edgecolor=grid_color, alpha=0.8),
                    arrowprops=dict(arrowstyle='->', color=grid_color, lw=0.8))

    ax.set_xscale('log')
    ax.set_xlim(0.01, max(x_aus)*1.8 if x_aus else 20.0)
    ax.set_ylim(-1.5, 1.5)
    ax.set_yticks([])
    ax.set_xlabel("Orbital Distance (Astronomical Units - AU, Log Scale)", color=text_color, fontsize=10)
    ax.set_title(f"Stellar System Layout: {system.name} (Hex {system.hex_location if hasattr(system, 'hex_location') else 'N/A'})",
                 color=text_color, fontsize=13, fontweight='bold', pad=15)

    # Custom Legend
    handles = [
        patches.Patch(color=hz_color, alpha=0.3, label='Habitable Zone'),
        plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='#38bdf8', markersize=8, label='Terrestrial World'),
        plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='#a855f7', markersize=12, label='Gas Giant'),
        plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='#f97316', markersize=5, label='Planetoid Belt'),
        plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='#38bdf8', markeredgecolor='#f43f5e', markeredgewidth=2, markersize=9, label='Mainworld')
    ]
    ax.legend(handles=handles, loc='upper right', facecolor=bg_color, edgecolor=grid_color, labelcolor=text_color, fontsize=8)

    plt.tight_layout()
    return fig
