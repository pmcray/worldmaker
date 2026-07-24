from typing import Union
from .classes import Sector, StellarSystem
from .exporters import export_system_html, create_system_dataframe
from .sector import generate_subsector_svg
from .adventure import generate_system_adventure_seeds
from .utils import Utils

def export_campaign_briefing_html(target: Union[Sector, StellarSystem], title: str = "IISS Sector Campaign Briefing") -> str:
    """
    Generates a print-ready HTML campaign briefing booklet with print stylesheets (@media print), 
    cover banner, vector maps, UWP tables, adventure seeds, and Referee briefing notes.
    """
    html = []
    html.append(f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=JetBrains+Mono:wght@500;700&family=Georgia&display=swap');

@media print {{
    body {{ background: #fff !important; color: #000 !important; font-size: 10pt; }}
    .page-break {{ page-break-after: always; }}
    .no-print {{ display: none !important; }}
    .briefing-card {{ border: 1px solid #666 !important; box-shadow: none !important; background: #fff !important; }}
}}

body {{
    font-family: 'Inter', -apple-system, sans-serif;
    background: #0f172a;
    color: #f8fafc;
    margin: 0;
    padding: 20px;
}}
.container {{
    max-width: 960px;
    margin: 0 auto;
}}
.cover-header {{
    text-align: center;
    border-bottom: 3px double #0284c7;
    padding-bottom: 20px;
    margin-bottom: 30px;
}}
.cover-title {{
    font-family: 'Georgia', serif;
    font-size: 2.2rem;
    color: #38bdf8;
    margin: 0;
    text-transform: uppercase;
    letter-spacing: 2px;
}}
.cover-subtitle {{
    font-size: 1rem;
    color: #94a3b8;
    margin-top: 8px;
    font-family: 'JetBrains Mono', monospace;
}}
.briefing-card {{
    background: #1e293b;
    border-radius: 8px;
    border: 1px solid #334155;
    padding: 20px;
    margin-bottom: 24px;
}}
.card-title {{
    font-size: 1.2rem;
    font-weight: 700;
    color: #f1f5f9;
    border-bottom: 1px solid #334155;
    padding-bottom: 8px;
    margin-top: 0;
}}
.print-btn {{
    background: #0284c7;
    color: #fff;
    border: none;
    padding: 10px 20px;
    border-radius: 6px;
    font-weight: 600;
    cursor: pointer;
    margin-bottom: 20px;
}}
.print-btn:hover {{ background: #0369a1; }}
</style>
</head>
<body>
<div class="container">
<button class="print-btn no-print" onclick="window.print()">🖨️ Print / Save as PDF</button>

<div class="cover-header">
    <h1 class="cover-title">{title}</h1>
    <div class="cover-subtitle">Imperial Interstellar Scout Service (IISS) Survey Briefing</div>
</div>
""")

    if isinstance(target, StellarSystem):
        # System briefing
        html.append(export_system_html(target))
    elif isinstance(target, Sector):
        # Subsector briefing
        subsector_svg = generate_subsector_svg(target, name=target.name)
        html.append('<div class="briefing-card">')
        html.append('<h2 class="card-title">Subsector Vector Map</h2>')
        html.append(f'<div>{subsector_svg}</div>')
        html.append('</div>')

        html.append('<div class="page-break"></div>')

        # Systems Overview Table
        html.append('<div class="briefing-card">')
        html.append('<h2 class="card-title">Subsector System Catalog & UWPs</h2>')
        html.append('<table style="width:100%; border-collapse:collapse; font-size:0.85rem;">')
        html.append('<tr style="background:#0f172a; color:#94a3b8; text-align:left;"><th style="padding:8px;">Hex</th><th>System Name</th><th>UWP</th><th>Allegiance</th><th>Bases</th><th>Trade Codes</th></tr>')

        for hex_coord, sys in sorted(target.systems.items()):
            mw = next((w for w in sys.all_worlds if w.is_mainworld), None)
            if not mw: continue
            bases_str = ", ".join(sys.bases) if sys.bases else "—"
            tcodes_str = " ".join(mw.trade_codes) if mw.trade_codes else "—"
            html.append(f'<tr style="border-bottom:1px solid #334155; padding:8px;">')
            html.append(f'<td style="padding:8px;"><code>{hex_coord}</code></td>')
            html.append(f'<td><strong>{sys.name}</strong></td>')
            html.append(f'<td><code>{mw.uwp}</code></td>')
            html.append(f'<td>{sys.allegiance}</td>')
            html.append(f'<td>{bases_str}</td>')
            html.append(f'<td>{tcodes_str}</td>')
            html.append('</tr>')

        html.append('</table>')
        html.append('</div>')

    html.append("""
</div>
</body>
</html>
""")
    return "".join(html)
