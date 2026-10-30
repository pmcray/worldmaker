import math
import networkx as nx
import plotly.graph_objects as go
from typing import Dict, Any
from .classes import Sector
from .sector import hex_to_coords
from .utils import Utils

def plot_subsector_trade_network(subsector: Sector, dark_mode=True) -> go.Figure:
    """
    Renders an interactive Trade & Communications Network Graph using NetworkX and Plotly.
    Displays WTN trade potential routes, scout communications relays, and political allegiances.
    """
    G = nx.Graph()
    
    # Allegiance colors
    allegiance_colors = {
        'Im': '#ef4444', # Imperial red
        'Zh': '#3b82f6', # Zhodani blue
        'Av': '#f59e0b', # Avalar amber
        'Na': '#10b981', # Non-aligned green
        'Cs': '#8b5cf6'  # Client State purple
    }

    # 1. Add System Nodes
    pos = {}
    node_x = []
    node_y = []
    node_sizes = []
    node_colors = []
    node_texts = []

    for hex_coord, system in subsector.systems.items():
        mainworld = system.mainworld
        if not mainworld: continue

        col, row = hex_to_coords(hex_coord)
        
        # Hex grid layout coordinates (invert Y for map orientation)
        x = col * 1.5
        y = -(row * math.sqrt(3) + (0.866 if col % 2 == 1 else 0))
        pos[hex_coord] = (x, y)
        G.add_node(hex_coord, name=system.name, mainworld=mainworld, allegiance=system.allegiance)

        node_x.append(x)
        node_y.append(y)

        # Node size based on population
        pop_val = Utils.from_eHex(mainworld.uwp.population)
        node_sizes.append(max(12, pop_val * 4))

        color = allegiance_colors.get(system.allegiance, '#94a3b8')
        node_colors.append(color)

        bases_str = f"Bases: {', '.join(system.bases)}" if system.bases else "Bases: None"
        tcodes_str = f"Trade: {', '.join(mainworld.trade_codes)}" if mainworld.trade_codes else "Trade: None"
        hover_str = (f"<b>Hex {hex_coord}: {system.name}</b><br>"
                     f"UWP: {mainworld.uwp}<br>"
                     f"Allegiance: {system.allegiance}<br>"
                     f"{bases_str}<br>{tcodes_str}")
        node_texts.append(hover_str)

    # 2. Add Edges (Trade Routes)
    edge_x = []
    edge_y = []
    
    for h1, h2, rtype in subsector.routes:
        if h1 in pos and h2 in pos:
            x0, y0 = pos[h1]
            x1, y1 = pos[h2]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])
            G.add_edge(h1, h2, route_type=rtype)

    fig = go.Figure()

    # Draw Trade Route Edges
    fig.add_trace(go.Scatter(
        x=edge_x, y=edge_y,
        line=dict(width=2, color='#10b981'),
        hoverinfo='none',
        mode='lines',
        name='Major Trade Routes (WTN)'
    ))

    # Draw System Nodes
    fig.add_trace(go.Scatter(
        x=node_x, y=node_y,
        mode='markers+text',
        marker=dict(
            size=node_sizes,
            color=node_colors,
            line=dict(width=2, color='#ffffff')
        ),
        text=[f"{h}" for h in pos.keys()],
        textposition="bottom center",
        textfont=dict(size=9, color='#cbd5e1' if dark_mode else '#1f2328'),
        hovertext=node_texts,
        hoverinfo='text',
        name='Systems'
    ))

    # Dark / Light Theme
    bg_color = '#0b0e14' if dark_mode else '#ffffff'
    text_color = '#f8fafc' if dark_mode else '#1f2328'

    fig.update_layout(
        title=dict(
            text=f"Subsector Interstellar Trade & Communications Network",
            font=dict(color=text_color, size=16)
        ),
        paper_bgcolor=bg_color,
        plot_bgcolor=bg_color,
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        margin=dict(l=20, r=20, b=20, t=50),
        legend=dict(font=dict(color=text_color), bgcolor=bg_color)
    )

    return fig
