import math
from typing import Dict, Any, List
from .classes import StellarSystem, PlanetaryBody
from .sector import hex_distance
from .utils import Utils

# Standard Traveller Speculative Trade Goods Table
TRADE_GOODS_CATALOG = [
    {
        "name": "Agricultural Goods",
        "base_price": 1000,
        "purchase_dm": {"Ag": 2, "Wa": 1},
        "sale_dm": {"As": 2, "De": 2, "In": 1, "Na": 1, "Po": 1}
    },
    {
        "name": "Industrial Machinery",
        "base_price": 10000,
        "purchase_dm": {"In": 2, "Ht": 2},
        "sale_dm": {"Ag": 2, "Ni": 2, "Po": 1}
    },
    {
        "name": "High Tech Electronics",
        "base_price": 20000,
        "purchase_dm": {"Ht": 3, "In": 1},
        "sale_dm": {"Lt": 3, "Ni": 2, "Po": 2}
    },
    {
        "name": "Basic Raw Materials",
        "base_price": 5000,
        "purchase_dm": {"As": 3, "De": 1, "Va": 2},
        "sale_dm": {"In": 3, "Ri": 1}
    },
    {
        "name": "Luxury Consumer Goods",
        "base_price": 50000,
        "purchase_dm": {"Ri": 2, "Ht": 1},
        "sale_dm": {"Ri": 3, "In": 1}
    },
    {
        "name": "Medical Supplies & Cybernetics",
        "base_price": 30000,
        "purchase_dm": {"Ht": 2, "In": 1},
        "sale_dm": {"Po": 2, "De": 2, "As": 2}
    }
]

def calculate_speculative_trade_run(source_system: StellarSystem, target_system: StellarSystem, cargo_tonnage: int = 40) -> Dict[str, Any]:
    """
    Calculates jump distance, speculative trade cargo purchase/sale price modifiers, 
    and estimated profit per ton between two star systems.
    """
    source_mw = source_system.mainworld
    target_mw = target_system.mainworld

    if not source_mw or not target_mw:
        return {"error": "Both systems must have established mainworlds."}

    source_hex = getattr(source_system, 'hex_location', '0101')
    target_hex = getattr(target_system, 'hex_location', '0102')

    # Distance in parsecs
    distance_parsecs = math.ceil(hex_distance(source_hex, target_hex))
    fuel_tons_needed = cargo_tonnage * 0.1 * distance_parsecs

    source_tcodes = source_mw.trade_codes
    target_tcodes = target_mw.trade_codes

    profitable_goods = []

    for item in TRADE_GOODS_CATALOG:
        purch_dm = sum(item["purchase_dm"].get(tc, 0) for tc in source_tcodes)
        sale_dm = sum(item["sale_dm"].get(tc, 0) for tc in target_tcodes)

        # Base purchase price modifier (e.g. -5% per DM point)
        buy_factor = max(0.6, 1.0 - (purch_dm * 0.05))
        sell_factor = min(1.8, 1.0 + (sale_dm * 0.08))

        estimated_buy_price = int(item["base_price"] * buy_factor)
        estimated_sell_price = int(item["base_price"] * sell_factor)
        profit_per_ton = estimated_sell_price - estimated_buy_price

        if profit_per_ton > 0:
            total_profit = profit_per_ton * cargo_tonnage
            profitable_goods.append({
                "name": item["name"],
                "base_price": item["base_price"],
                "buy_price": estimated_buy_price,
                "sell_price": estimated_sell_price,
                "profit_per_ton": profit_per_ton,
                "total_profit_40t": total_profit,
                "purch_dm": purch_dm,
                "sale_dm": sale_dm
            })

    # Sort by profit per ton
    profitable_goods.sort(key=lambda x: x["profit_per_ton"], reverse=True)

    return {
        "source_name": source_system.name,
        "source_hex": source_hex,
        "source_uwp": str(source_mw.uwp),
        "source_tcodes": source_tcodes,
        "target_name": target_system.name,
        "target_hex": target_hex,
        "target_uwp": str(target_mw.uwp),
        "target_tcodes": target_tcodes,
        "distance_parsecs": distance_parsecs,
        "jump_rating_required": f"Jump-{min(6, max(1, distance_parsecs))}",
        "fuel_tons_needed": fuel_tons_needed,
        "recommended_cargo": profitable_goods
    }
