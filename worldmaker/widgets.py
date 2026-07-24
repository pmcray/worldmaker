import base64
import cv2
import numpy as np
import ipywidgets as widgets
from IPython.display import display, HTML, SVG, clear_output
import matplotlib.pyplot as plt

from .classes import Sector, StellarSystem, PlanetaryBody
from .generator import generate_full_system
from .exporters import export_system_html, export_system_markdown, create_system_dataframe
from .visualization import plot_system_orbit_diagram
from .visualization_3d import plot_system_3d_orbit_diagram
from .trade_network import plot_subsector_trade_network
from .trade_calculator import calculate_speculative_trade_run
from .pdf_exporter import export_campaign_briefing_html
from .sector import generate_sector, generate_subsector_svg
from .system import calculate_available_orbits
from .planet_mapper import generate_planetary_maps
from .planet_projections import render_traveller_icosahedral_net, plot_3d_planet_globe

def _ndarray_to_html_img(arr_rgb: np.ndarray, width="100%") -> str:
    """Converts an RGB numpy array image into a base64 inline HTML <img> tag."""
    arr_bgr = cv2.cvtColor(arr_rgb, cv2.COLOR_RGB2BGR)
    _, buffer = cv2.imencode('.png', arr_bgr)
    b64_str = base64.b64encode(buffer).decode('utf-8')
    return f'<img src="data:image/png;base64,{b64_str}" style="width:{width}; border-radius:8px; border:1px solid #334155;" />'

def render_generator_dashboard():
    """
    Renders an interactive ipywidgets control dashboard for generating and exploring Traveller star systems inside Jupyter Notebooks.
    """
    header = HTML("""
    <div style="background: linear-gradient(135deg, #0f172a, #1e293b); padding: 18px; border-radius: 10px; border: 1px solid #334155; margin-bottom: 16px;">
        <h2 style="color: #38bdf8; margin: 0; font-family: sans-serif;">🌌 Traveller System Generator Dashboard</h2>
        <p style="color: #94a3b8; margin: 4px 0 0 0; font-size: 0.9rem; font-family: sans-serif;">Interactive System Generation & Visual Explorer (WBH & SCG Engine)</p>
    </div>
    """)

    txt_name = widgets.Text(value="Regulus Prime", description="System Name:", style={'description_width': '120px'})
    dd_model = widgets.Dropdown(options=[('Physics (Hill Spheres)', 'physics'), ('Simple (Exclusion Zones)', 'simple')],
                                value='physics', description="Stability Model:", style={'description_width': '120px'})
    slider_pop = widgets.IntSlider(value=0, min=-5, max=5, step=1, description="Population DM:", style={'description_width': '120px'})
    btn_generate = widgets.Button(description="🚀 Generate System", button_style='primary',
                                  layout=widgets.Layout(width='180px', height='38px', margin='10px 0 0 0'))

    controls_box = widgets.VBox([
        widgets.HBox([txt_name, dd_model]),
        widgets.HBox([slider_pop, btn_generate])
    ], layout=widgets.Layout(padding='12px', background='#1e293b', border='1px solid #334155', border_radius='8px'))

    out_dossier = widgets.Output()
    out_diagram2d = widgets.Output()
    out_diagram3d = widgets.Output()
    out_cartography = widgets.Output()
    out_table = widgets.Output()
    out_markdown = widgets.Output()

    tab = widgets.Tab(children=[out_dossier, out_diagram2d, out_diagram3d, out_cartography, out_table, out_markdown])
    tab.set_title(0, '📋 HTML Card & Rumors')
    tab.set_title(1, '🪐 2D System Layout')
    tab.set_title(2, '🌐 3D Orbital Model')
    tab.set_title(3, '🌍 World Cartography & Globe')
    tab.set_title(4, '📊 Data Table')
    tab.set_title(5, '📝 Raw Markdown')

    def on_generate_clicked(b):
        btn_generate.disabled = True
        btn_generate.description = "Generating..."
        
        name = txt_name.value.strip() or "Unnamed System"
        model = dd_model.value
        pop_dm = slider_pop.value

        system = generate_full_system(name=name, population_dm=pop_dm)
        calculate_available_orbits(system, model=model)

        with out_dossier:
            clear_output(wait=True)
            display(HTML(export_system_html(system)))

        with out_diagram2d:
            clear_output(wait=True)
            fig = plot_system_orbit_diagram(system)
            display(fig)
            plt.close(fig)

        with out_diagram3d:
            clear_output(wait=True)
            fig3d = plot_system_3d_orbit_diagram(system)
            fig3d.show()

        with out_cartography:
            clear_output(wait=True)
            mainworld = next((w for w in system.all_worlds if w.is_mainworld), None)
            if mainworld:
                maps_data = generate_planetary_maps(mainworld)
                ico_net_bgr = render_traveller_icosahedral_net(maps_data["surface_texture"])
                img_ico_html = _ndarray_to_html_img(ico_net_bgr)
                img_eq_html = _ndarray_to_html_img(maps_data["surface_texture"])
                
                html_carto = f"""
                <div style="background:#0f172a; padding:18px; border-radius:10px; border:1px solid #334155; color:#f8fafc;">
                    <h3 style="color:#38bdf8; margin-top:0;">Planetary Cartography: {mainworld.designation} ({mainworld.name})</h3>
                    <div><strong>UWP:</strong> <code>{mainworld.uwp}</code> &bull; <strong>Size:</strong> {mainworld.size_code} &bull; <strong>Hydrographics:</strong> {int(maps_data['hydro_fraction']*100)}% Water</div>
                    
                    <h4 style="color:#f1f5f9; margin-top:16px;">1. Classic Traveller 20-Triangle Icosahedral Net Map</h4>
                    {img_ico_html}
                    
                    <h4 style="color:#f1f5f9; margin-top:16px;">2. Modern 2D Equirectangular Surface & Relief Map</h4>
                    {img_eq_html}
                </div>
                """
                display(HTML(html_carto))
                
                # Render 3D Globe
                fig_globe = plot_3d_planet_globe(maps_data["surface_texture"], world_name=mainworld.name)
                fig_globe.show()
            else:
                display(HTML("<div>No Mainworld found in this system.</div>"))

        with out_table:
            clear_output(wait=True)
            df = create_system_dataframe(system)
            display(df)

        with out_markdown:
            clear_output(wait=True)
            md = export_system_markdown(system)
            display(HTML(f"<pre style='background:#0f172a; color:#f8fafc; padding:16px; border-radius:8px;'>{md}</pre>"))

        btn_generate.disabled = False
        btn_generate.description = "🚀 Generate System"

    btn_generate.on_click(on_generate_clicked)

    display(header)
    display(controls_box)
    display(tab)
    on_generate_clicked(btn_generate)

def render_subsector_dashboard(subsector: Sector = None):
    """
    Renders an interactive Subsector Hex Click Inspector, Interstellar Trade Route Network Graph,
    Speculative Trade Calculator, and Planetary Cartography Map & Globe engine inside Jupyter Notebooks.
    """
    if subsector is None:
        subsector = generate_sector(width=8, height=10)

    header = HTML(f"""
    <div style="background: linear-gradient(135deg, #0f172a, #1e293b); padding: 18px; border-radius: 10px; border: 1px solid #334155; margin-bottom: 16px;">
        <h2 style="color: #38bdf8; margin: 0; font-family: sans-serif;">🗺️ Subsector Interactive Explorer: {subsector.name}</h2>
        <p style="color: #94a3b8; margin: 4px 0 0 0; font-size: 0.9rem; font-family: sans-serif;">Hex Click Inspector, Trade Network Graph, Planetary Maps & Speculative Trade</p>
    </div>
    """)

    hex_options = [f"{h} - {sys.name}" for h, sys in sorted(subsector.systems.items())]
    if not hex_options:
        hex_options = ["None"]

    dd_hex = widgets.Dropdown(options=hex_options, value=hex_options[0], description="Inspect Hex:", style={'description_width': '110px'})
    
    # Speculative Trade controls
    dd_trade_origin = widgets.Dropdown(options=hex_options, value=hex_options[0], description="Trade Origin:", style={'description_width': '110px'})
    dd_trade_dest = widgets.Dropdown(options=hex_options, value=hex_options[min(1, len(hex_options)-1)], description="Destination:", style={'description_width': '110px'})
    btn_calc_trade = widgets.Button(description="💰 Calculate Trade Run", button_style='info', layout=widgets.Layout(width='180px'))

    controls_box = widgets.VBox([
        widgets.HBox([dd_hex]),
        widgets.HBox([dd_trade_origin, dd_trade_dest, btn_calc_trade])
    ], layout=widgets.Layout(padding='12px', background='#1e293b', border='1px solid #334155', border_radius='8px'))

    out_map = widgets.Output()
    out_dossier = widgets.Output()
    out_cartography = widgets.Output()
    out_trade_network = widgets.Output()
    out_trade_calculator = widgets.Output()

    tab = widgets.Tab(children=[out_map, out_dossier, out_cartography, out_trade_network, out_trade_calculator])
    tab.set_title(0, '🗺️ Vector Hex Map')
    tab.set_title(1, '📋 System Dossier & Rumors')
    tab.set_title(2, '🌍 World Map & 3D Globe')
    tab.set_title(3, '🕸️ Trade Network Graph')
    tab.set_title(4, '💰 Speculative Trade Run')

    # Render Subsector Map
    with out_map:
        clear_output(wait=True)
        svg_content = generate_subsector_svg(subsector, name=subsector.name)
        display(SVG(svg_content))

    # Render Trade Network Graph
    with out_trade_network:
        clear_output(wait=True)
        fig_net = plot_subsector_trade_network(subsector)
        fig_net.show()

    def update_system_dossier(change):
        selected = dd_hex.value.split(" - ")[0]
        sys = subsector.systems.get(selected)
        with out_dossier:
            clear_output(wait=True)
            if sys:
                display(HTML(export_system_html(sys)))

        with out_cartography:
            clear_output(wait=True)
            if sys:
                mw = next((w for w in sys.all_worlds if w.is_mainworld), None)
                if mw:
                    maps_data = generate_planetary_maps(mw)
                    ico_net_bgr = render_traveller_icosahedral_net(maps_data["surface_texture"])
                    img_ico_html = _ndarray_to_html_img(ico_net_bgr)
                    img_eq_html = _ndarray_to_html_img(maps_data["surface_texture"])
                    
                    html_carto = f"""
                    <div style="background:#0f172a; padding:18px; border-radius:10px; border:1px solid #334155; color:#f8fafc;">
                        <h3 style="color:#38bdf8; margin-top:0;">Planetary Cartography: {mw.designation} ({mw.name})</h3>
                        <div><strong>UWP:</strong> <code>{mw.uwp}</code> &bull; <strong>Size:</strong> {mw.size_code} &bull; <strong>Hydrographics:</strong> {int(maps_data['hydro_fraction']*100)}% Water</div>
                        
                        <h4 style="color:#f1f5f9; margin-top:16px;">1. Classic Traveller 20-Triangle Icosahedral Net Map</h4>
                        {img_ico_html}
                        
                        <h4 style="color:#f1f5f9; margin-top:16px;">2. Modern 2D Equirectangular Surface & Relief Map</h4>
                        {img_eq_html}
                    </div>
                    """
                    display(HTML(html_carto))
                    
                    fig_globe = plot_3d_planet_globe(maps_data["surface_texture"], world_name=mw.name)
                    fig_globe.show()

    dd_hex.observe(update_system_dossier, names='value')
    update_system_dossier(None)

    def on_trade_calc_clicked(b):
        orig_hex = dd_trade_origin.value.split(" - ")[0]
        dest_hex = dd_trade_dest.value.split(" - ")[0]

        orig_sys = subsector.systems.get(orig_hex)
        dest_sys = subsector.systems.get(dest_hex)

        with out_trade_calculator:
            clear_output(wait=True)
            if orig_sys and dest_sys:
                res = calculate_speculative_trade_run(orig_sys, dest_sys)
                
                html_trade = [f"""
                <div style="background:#1e293b; color:#f8fafc; padding:18px; border-radius:8px; border:1px solid #334155;">
                    <h3 style="color:#38bdf8; margin-top:0;">Trade Route Analysis: {res['source_name']} ({res['source_hex']}) ➔ {res['target_name']} ({res['target_hex']})</h3>
                    <div><strong>Jump Distance:</strong> {res['distance_parsecs']} Parsecs ({res['jump_rating_required']} drive required) &bull; <strong>Fuel Needed:</strong> {res['fuel_tons_needed']} Tons</div>
                    <div style="margin-top:8px;"><strong>Source Trade Codes:</strong> <code>{', '.join(res['source_tcodes'])}</code> &bull; <strong>Target Trade Codes:</strong> <code>{', '.join(res['target_tcodes'])}</code></div>
                    <h4 style="color:#f1f5f9; margin-top:16px;">Top Profitable Speculative Cargo (40-Ton Free Trader Hold)</h4>
                    <table style="width:100%; border-collapse:collapse; font-size:0.85rem; margin-top:8px;">
                        <tr style="background:#0f172a; color:#94a3b8; text-align:left;"><th style="padding:8px;">Cargo Good</th><th>Base Cost</th><th>Buy Price/t</th><th>Sell Price/t</th><th>Profit/t</th><th>Total 40t Profit</th></tr>
                """]

                for item in res['recommended_cargo']:
                    html_trade.append(f"""
                        <tr style="border-bottom:1px solid #334155;">
                            <td style="padding:8px;"><strong>{item['name']}</strong></td>
                            <td>Cr{item['base_price']:,}</td>
                            <td>Cr{item['buy_price']:,}</td>
                            <td>Cr{item['sell_price']:,}</td>
                            <td style="color:#22c55e; font-weight:bold;">+Cr{item['profit_per_ton']:,}</td>
                            <td style="color:#38bdf8; font-weight:bold;">+Cr{item['total_profit_40t']:,}</td>
                        </tr>
                    """)

                html_trade.append("</table></div>")
                display(HTML("".join(html_trade)))

    btn_calc_trade.on_click(on_trade_calc_clicked)

    display(header)
    display(controls_box)
    display(tab)
    on_trade_calc_clicked(btn_calc_trade)
