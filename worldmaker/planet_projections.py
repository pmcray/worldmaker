import cv2
import numpy as np
import math
import plotly.graph_objects as go
from typing import Dict, Any, Tuple

# --- Icosahedron Geometry Setup (Derived from weorold/wp15_traveller_map.py) ---
phi = (1.0 + np.sqrt(5.0)) / 2.0
PN = np.array([0.0, 0.0, 1.0])
PS = np.array([0.0, 0.0, -1.0])
alpha = np.arcsin(1.0 / np.sqrt(5.0))

P = []
for k in range(5):
    theta = k * 72.0 * np.pi / 180.0
    P.append(np.array([np.cos(theta) * np.cos(alpha), np.sin(theta) * np.cos(alpha), np.sin(alpha)]))

Q = []
for k in range(5):
    theta = (k + 0.5) * 72.0 * np.pi / 180.0
    Q.append(np.array([np.cos(theta) * np.cos(alpha), np.sin(theta) * np.cos(alpha), -np.sin(alpha)]))

def _get_triangles_definition(S):
    H = S * np.sqrt(3) / 2.0
    triangles = []
    
    # 1. Top Polar Triangles
    triangles.append({"name": "Top_1", "pts2d": np.array([[S, 0.0], [0.5*S, H], [1.5*S, H]], dtype=np.float32), "pts3d": [PN, P[0], P[1]]})
    triangles.append({"name": "Top_3", "pts2d": np.array([[2.0*S, 0.0], [1.5*S, H], [2.5*S, H]], dtype=np.float32), "pts3d": [PN, P[1], P[2]]})
    triangles.append({"name": "Top_5", "pts2d": np.array([[3.0*S, 0.0], [2.5*S, H], [3.5*S, H]], dtype=np.float32), "pts3d": [PN, P[2], P[3]]})
    triangles.append({"name": "Top_7", "pts2d": np.array([[4.0*S, 0.0], [3.5*S, H], [4.5*S, H]], dtype=np.float32), "pts3d": [PN, P[3], P[4]]})
    triangles.append({"name": "Top_9", "pts2d": np.array([[5.0*S, 0.0], [4.5*S, H], [5.5*S, H]], dtype=np.float32), "pts3d": [PN, P[4], P[0]]})
    
    # 2. Middle Up-pointing Triangles
    triangles.append({"name": "Mid_Up_0", "pts2d": np.array([[0.5*S, H], [0.0, 2.0*H], [S, 2.0*H]], dtype=np.float32), "pts3d": [P[0], Q[4], Q[0]]})
    triangles.append({"name": "Mid_Up_2", "pts2d": np.array([[1.5*S, H], [S, 2.0*H], [2.0*S, 2.0*H]], dtype=np.float32), "pts3d": [P[1], Q[0], Q[1]]})
    triangles.append({"name": "Mid_Up_4", "pts2d": np.array([[2.5*S, H], [2.0*S, 2.0*H], [3.0*S, 2.0*H]], dtype=np.float32), "pts3d": [P[2], Q[1], Q[2]]})
    triangles.append({"name": "Mid_Up_6", "pts2d": np.array([[3.5*S, H], [3.0*S, 2.0*H], [4.0*S, 2.0*H]], dtype=np.float32), "pts3d": [P[3], Q[2], Q[3]]})
    triangles.append({"name": "Mid_Up_8", "pts2d": np.array([[4.5*S, H], [4.0*S, 2.0*H], [5.0*S, 2.0*H]], dtype=np.float32), "pts3d": [P[4], Q[3], Q[4]]})
    
    # 3. Middle Down-pointing Triangles
    triangles.append({"name": "Mid_Down_1", "pts2d": np.array([[S, 2.0*H], [0.5*S, H], [1.5*S, H]], dtype=np.float32), "pts3d": [Q[0], P[0], P[1]]})
    triangles.append({"name": "Mid_Down_3", "pts2d": np.array([[2.0*S, 2.0*H], [1.5*S, H], [2.5*S, H]], dtype=np.float32), "pts3d": [Q[1], P[1], P[2]]})
    triangles.append({"name": "Mid_Down_5", "pts2d": np.array([[3.0*S, 2.0*H], [2.5*S, H], [3.5*S, H]], dtype=np.float32), "pts3d": [Q[2], P[2], P[3]]})
    triangles.append({"name": "Mid_Down_7", "pts2d": np.array([[4.0*S, 2.0*H], [3.5*S, H], [4.5*S, H]], dtype=np.float32), "pts3d": [Q[3], P[3], P[4]]})
    triangles.append({"name": "Mid_Down_9", "pts2d": np.array([[5.0*S, 2.0*H], [4.5*S, H], [5.5*S, H]], dtype=np.float32), "pts3d": [Q[4], P[4], P[0]]})
    
    # 4. Bottom Polar Triangles
    triangles.append({"name": "Bot_0", "pts2d": np.array([[0.5*S, 3.0*H], [0.0, 2.0*H], [S, 2.0*H]], dtype=np.float32), "pts3d": [PS, Q[4], Q[0]]})
    triangles.append({"name": "Bot_2", "pts2d": np.array([[1.5*S, 3.0*H], [S, 2.0*H], [2.0*S, 2.0*H]], dtype=np.float32), "pts3d": [PS, Q[0], Q[1]]})
    triangles.append({"name": "Bot_4", "pts2d": np.array([[2.5*S, 3.0*H], [2.0*S, 2.0*H], [3.0*S, 2.0*H]], dtype=np.float32), "pts3d": [PS, Q[1], Q[2]]})
    triangles.append({"name": "Bot_6", "pts2d": np.array([[3.5*S, 3.0*H], [3.0*S, 2.0*H], [4.0*S, 2.0*H]], dtype=np.float32), "pts3d": [PS, Q[2], Q[3]]})
    triangles.append({"name": "Bot_8", "pts2d": np.array([[4.5*S, 3.0*H], [4.0*S, 2.0*H], [5.0*S, 2.0*H]], dtype=np.float32), "pts3d": [PS, Q[3], Q[4]]})
    
    return triangles

def render_traveller_icosahedral_net(texture_array: np.ndarray, S=240, bg_color=(15, 23, 42)) -> np.ndarray:
    """
    Projects an equirectangular planetary texture onto a classic 20-triangle unfolded icosahedral 
    net map (the iconic Traveller 1981 world map format).
    """
    H_tex, W_tex, Channels = texture_array.shape
    H_tri = S * np.sqrt(3) / 2.0
    width = int(5.5 * S)
    height = int(3.0 * H_tri)
    
    out_img = np.zeros((height, width, 3), dtype=np.uint8)
    out_img[:, :] = np.array(bg_color, dtype=np.uint8)
    
    triangles = _get_triangles_definition(S)
    
    for tri in triangles:
        pts2d = tri["pts2d"]
        v_A, v_B, v_C = tri["pts3d"]
        
        x_min = max(0, min(width - 1, int(np.floor(np.min(pts2d[:, 0])))))
        x_max = max(0, min(width - 1, int(np.ceil(np.max(pts2d[:, 0])))))
        y_min = max(0, min(height - 1, int(np.floor(np.min(pts2d[:, 1])))))
        y_max = max(0, min(height - 1, int(np.ceil(np.max(pts2d[:, 1])))))
        
        xs = np.arange(x_min, x_max + 1, dtype=np.float32)
        ys = np.arange(y_min, y_max + 1, dtype=np.float32)
        grid_x, grid_y = np.meshgrid(xs, ys)
        
        p0, p1, p2 = pts2d[0], pts2d[1], pts2d[2]
        denom = (p1[1] - p2[1]) * (p0[0] - p2[0]) + (p2[0] - p1[0]) * (p0[1] - p2[1])
        
        wA = ((p1[1] - p2[1]) * (grid_x - p2[0]) + (p2[0] - p1[0]) * (grid_y - p2[1])) / denom
        wB = ((p2[1] - p0[1]) * (grid_x - p2[0]) + (p0[0] - p2[0]) * (grid_y - p2[1])) / denom
        wC = 1.0 - wA - wB
        
        mask = (wA >= 0) & (wB >= 0) & (wC >= 0)
        
        if not np.any(mask): continue
        
        wA_m = wA[mask]
        wB_m = wB[mask]
        wC_m = wC[mask]
        
        V_x = wA_m * v_A[0] + wB_m * v_B[0] + wC_m * v_C[0]
        V_y = wA_m * v_A[1] + wB_m * v_B[1] + wC_m * v_C[1]
        V_z = wA_m * v_A[2] + wB_m * v_B[2] + wC_m * v_C[2]
        
        norms = np.sqrt(V_x**2 + V_y**2 + V_z**2)
        V_x /= norms
        V_y /= norms
        V_z /= norms
        
        lon = np.arctan2(V_y, V_x)
        lat = np.arcsin(np.clip(V_z, -1.0, 1.0))
        
        u = (lon + np.pi) / (2.0 * np.pi)
        v = (np.pi / 2.0 - lat) / np.pi
        
        px = np.clip(np.floor(u * W_tex).astype(int), 0, W_tex - 1)
        py = np.clip(np.floor(v * H_tex).astype(int), 0, H_tex - 1)
        
        out_img[grid_y[mask].astype(int), grid_x[mask].astype(int)] = texture_array[py, px]
        
        # Draw triangle borders
        cv2.polylines(out_img, [pts2d.astype(np.int32)], True, (220, 220, 220), 1, cv2.LINE_AA)

    return out_img

def plot_3d_planet_globe(texture_array: np.ndarray, world_name: str = "World") -> go.Figure:
    """
    Renders an interactive 3D textured globe using Plotly.
    Allows 360° rotation and interactive exploration in Jupyter Notebooks.
    """
    H_tex, W_tex, _ = texture_array.shape
    
    # Downsample for smooth interactive 3D WebGL rendering
    sample_h = min(256, H_tex)
    sample_w = min(512, W_tex)
    small_tex = cv2.resize(texture_array, (sample_w, sample_h))

    # Spherical coordinates
    lon = np.linspace(-np.pi, np.pi, sample_w)
    lat = np.linspace(-np.pi/2, np.pi/2, sample_h)
    lon_grid, lat_grid = np.meshgrid(lon, lat)

    x = np.cos(lat_grid) * np.cos(lon_grid)
    y = np.cos(lat_grid) * np.sin(lon_grid)
    z = np.sin(lat_grid)

    # Convert RGB image matrix to hex string colors for Plotly surface
    colorscale = []
    surfacecolor = np.zeros((sample_h, sample_w))
    
    for r in range(sample_h):
        for c in range(sample_w):
            rgb = small_tex[r, c]
            surfacecolor[r, c] = r * sample_w + c

    # Create custom colorscale mapping every pixel color
    flat_rgb = small_tex.reshape(-1, 3)
    n_pixels = len(flat_rgb)
    step = max(1, n_pixels // 250)
    for i in range(0, n_pixels, step):
        r, g, b = flat_rgb[i]
        colorscale.append([i / (n_pixels - 1), f'rgb({r},{g},{b})'])
    colorscale.append([1.0, f'rgb({flat_rgb[-1][0]},{flat_rgb[-1][1]},{flat_rgb[-1][2]})'])

    fig = go.Figure(data=[go.Surface(
        x=x, y=y, z=z,
        surfacecolor=surfacecolor,
        colorscale=colorscale,
        showscale=False,
        hoverinfo='none'
    )])

    fig.update_layout(
        title=dict(text=f"3D Interactive Globe: {world_name}", font=dict(color='#f8fafc', size=16)),
        paper_bgcolor='#0f172a',
        plot_bgcolor='#0f172a',
        scene=dict(
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, backgroundcolor='#0f172a'),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, backgroundcolor='#0f172a'),
            zaxis=dict(showgrid=False, zeroline=False, showticklabels=False, backgroundcolor='#0f172a'),
            aspectmode='cube'
        ),
        margin=dict(l=0, r=0, b=0, t=40)
    )

    return fig
