import math
import numpy as np
import plotly.graph_objects as go
from typing import List
from .classes import StellarSystem, PlanetaryBody
from .utils import Utils

def plot_system_3d_orbit_diagram(system: StellarSystem, dark_mode=True) -> go.Figure:
    """
    Renders an interactive 3D solar system orbital visualization using Plotly.
    Displays 3D stars, orbital planes, inclination angles, and planetary bodies.
    """
    fig = go.Figure()
    
    primary = system.primary_star
    if not primary:
        return fig
    
    # 1. Primary Star at (0,0,0)
    star_color = '#ffcc00'
    if 'M' in primary.spectral_type: star_color = '#ff4d4d'
    elif 'K' in primary.spectral_type: star_color = '#ffaa33'
    elif 'A' in primary.spectral_type or 'F' in primary.spectral_type: star_color = '#e6f2ff'
    
    fig.add_trace(go.Scatter3d(
        x=[0], y=[0], z=[0],
        mode='markers+text',
        marker=dict(size=18, color=star_color, opacity=0.95),
        text=[f"Star {primary.designation} ({primary.spectral_type})"],
        textposition="top center",
        name=f"Primary Star: {primary.spectral_type}",
        hoverinfo="text"
    ))

    # 2. Orbits and Planets
    worlds = sorted(system.all_worlds, key=lambda w: w.orbit_au)
    
    type_colors = {
        'Terrestrial': '#38bdf8',
        'Gas Giant': '#a855f7',
        'Planetoid Belt': '#f97316',
        'Empty': '#64748b'
    }

    for idx, world in enumerate(worlds):
        a = max(0.05, world.orbit_au) # Semi-major axis in AU
        e = min(0.9, world.eccentricity) # Eccentricity
        b = a * math.sqrt(max(0.01, 1 - e**2)) # Semi-minor axis
        
        # Inclination angle in radians
        inc_deg = getattr(world, 'inclination', (idx % 3) * 4.0)
        inc_rad = math.radians(inc_deg)

        # True anomaly angles for smooth 3D ellipse
        theta = np.linspace(0, 2 * math.pi, 100)
        
        # Orbital ellipse coordinates in orbital plane
        x_orb = a * (np.cos(theta) - e)
        y_orb = b * np.sin(theta) * math.cos(inc_rad)
        z_orb = b * np.sin(theta) * math.sin(inc_rad)

        color = type_colors.get(world.body_type, '#94a3b8')

        # Add Orbit Line Trace
        fig.add_trace(go.Scatter3d(
            x=x_orb, y=y_orb, z=z_orb,
            mode='lines',
            line=dict(color=color, width=2, dash='dot' if world.body_type=='Empty' else 'solid'),
            hoverinfo='none',
            showlegend=False
        ))

        # Position of planet on orbit (fixed angle for 3D layout)
        planet_angle = (idx * 0.85) % (2 * math.pi)
        px = a * (math.cos(planet_angle) - e)
        py = b * math.sin(planet_angle) * math.cos(inc_rad)
        pz = b * math.sin(planet_angle) * math.sin(inc_rad)

        # Size of marker
        size_val = 8
        if world.body_type == 'Gas Giant': size_val = 14
        elif world.body_type == 'Planetoid Belt': size_val = 4
        elif world.is_mainworld: size_val = 11

        uwp_str = str(world.uwp) if world.uwp and world.uwp.starport else world.body_type
        hover_txt = f"<b>{world.designation}: {world.name}</b><br>Type: {world.body_type}<br>Orbit AU: {round(world.orbit_au, 3)} AU<br>UWP: {uwp_str}<br>Inclination: {inc_deg:.1f}°"

        fig.add_trace(go.Scatter3d(
            x=[px], y=[py], z=[pz],
            mode='markers+text',
            marker=dict(
                size=size_val,
                color=color,
                line=dict(color='#ffffff' if not world.is_mainworld else '#f43f5e', width=2)
            ),
            text=[f"{world.designation}"],
            textposition="top center",
            name=f"{world.designation} ({world.name})",
            hovertext=[hover_txt],
            hoverinfo="text"
        ))

    # Dark Space Theme Layout
    bg_color = '#0b0e14' if dark_mode else '#ffffff'
    grid_color = '#1e293b' if dark_mode else '#e2e8f0'
    text_color = '#f8fafc' if dark_mode else '#1f2328'

    fig.update_layout(
        title=dict(
            text=f"3D Orbital Architecture: {system.name}",
            font=dict(color=text_color, size=16)
        ),
        paper_bgcolor=bg_color,
        plot_bgcolor=bg_color,
        scene=dict(
            xaxis=dict(title='X (AU)', backgroundcolor=bg_color, gridcolor=grid_color, showbackground=True, zerolinecolor=grid_color),
            yaxis=dict(title='Y (AU)', backgroundcolor=bg_color, gridcolor=grid_color, showbackground=True, zerolinecolor=grid_color),
            zaxis=dict(title='Z (AU - Inclination)', backgroundcolor=bg_color, gridcolor=grid_color, showbackground=True, zerolinecolor=grid_color),
            aspectmode='data'
        ),
        margin=dict(l=0, r=0, b=0, t=40),
        legend=dict(font=dict(color=text_color), bgcolor=bg_color)
    )

    return fig
