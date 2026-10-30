"""Detailed government and law characteristics (WBH pp.156-172).

The UWP's single Government and Law Level digits expand into a centralisation
and authority description, a government structure, factions with strength and
relationships, a justice system profile (PSU-I-D) and Law Level subcodes
(O-WECPR).
"""
import random
from typing import Any, Dict, List

from .utils import Utils

GOVERNMENT_TYPES = {
    0: "None / Family or Clan", 1: "Company/Corporation",
    2: "Participating Democracy", 3: "Self-Perpetuating Oligarchy",
    4: "Representative Democracy", 5: "Feudal Technocracy",
    6: "Captive Government / Colony", 7: "Balkanisation",
    8: "Civil Service Bureaucracy", 9: "Impersonal Bureaucracy",
    10: "Charismatic Dictator", 11: "Non-Charismatic Leader",
    12: "Charismatic Oligarchy", 13: "Religious Dictatorship",
    14: "Religious Autocracy", 15: "Totalitarian Oligarchy",
}

CENTRALISATION = {2: 'Confederal', 3: 'Confederal', 4: 'Confederal',
                  5: 'Federal', 6: 'Federal', 7: 'Federal', 8: 'Federal',
                  9: 'Unitary', 10: 'Unitary', 11: 'Unitary', 12: 'Unitary'}

AUTHORITY = {2: 'Legislative', 3: 'Legislative', 4: 'Legislative',
             5: 'Executive', 6: 'Executive', 7: 'Executive', 8: 'Executive',
             9: 'Judicial', 10: 'Judicial', 11: 'Balanced', 12: 'Balanced'}

JUDICIAL_SYSTEMS = {2: 'Inquisitional', 3: 'Inquisitional', 4: 'Inquisitional',
                    5: 'Adversarial', 6: 'Adversarial', 7: 'Adversarial',
                    8: 'Adversarial', 9: 'Traditional', 10: 'Traditional',
                    11: 'Traditional', 12: 'Traditional'}

LAW_UNIFORMITY = {2: 'Personal', 3: 'Personal', 4: 'Personal', 5: 'Territorial',
                  6: 'Territorial', 7: 'Territorial', 8: 'Territorial',
                  9: 'Universal', 10: 'Universal', 11: 'Universal', 12: 'Universal'}

FACTION_STRENGTH = {1: 'Obscure', 2: 'Fringe', 3: 'Minor', 4: 'Notable',
                    5: 'Significant', 6: 'Dominant'}

_STRUCTURES = {
    'Confederal': ["Loose league of autonomous states",
                   "Treaty organisation with rotating chair",
                   "Trade compact with minimal central organs"],
    'Federal': ["Bicameral federation with regional assemblies",
                "Federated provinces under a common charter",
                "Federal union with devolved planetary regions"],
    'Unitary': ["Single centralised administration",
                "Unitary state with appointed prefects",
                "Centralised authority with district governors"],
}


def _law_subcode(overall: int) -> int:
    """Law Level subcodes are Overall Law Level + 2D3-4 (WBH p.170)."""
    return max(0, min(33, overall + (Utils.D3() + Utils.D3()) - 4))


def generate_factions(gov_code: int) -> List[Dict[str, Any]]:
    """Determines the factions within a government (WBH p.161).

    Balkanised worlds and those with weak central authority have more."""
    dm = 0
    if gov_code == 7:
        dm += 2
    elif gov_code == 0:
        dm += 1
    elif gov_code >= 10:
        dm -= 1

    count = max(1, Utils.D3() + dm)
    factions = []
    for i in range(count):
        ftype = Utils.D6(2) - 2
        factions.append({
            'id': i + 1,
            'government_type': GOVERNMENT_TYPES.get(ftype, 'Unaligned Movement'),
            'government_code': ftype,
            'strength': FACTION_STRENGTH[Utils.D6()],
        })

    # Relationships between factions, recorded as I+II=# in the book
    for a in range(len(factions)):
        for b in range(a + 1, len(factions)):
            roll = Utils.D6(2)
            if roll <= 4:
                rel = 'Hostile'
            elif roll <= 6:
                rel = 'Unfriendly'
            elif roll <= 8:
                rel = 'Neutral'
            elif roll <= 10:
                rel = 'Friendly'
            else:
                rel = 'Allied'
            factions[a].setdefault('relations', {})[factions[b]['id']] = rel
            factions[b].setdefault('relations', {})[factions[a]['id']] = rel

    return factions


def generate_government_details(world: Any) -> None:
    """Expands the Government and Law Level digits into full profiles."""
    uwp = world.uwp
    if not uwp.starport:
        return

    gov = Utils.from_eHex(uwp.government)
    law = Utils.from_eHex(uwp.law_level)
    pop = Utils.from_eHex(uwp.population)

    world.government_type = GOVERNMENT_TYPES.get(gov, 'Unknown')

    if pop == 0:
        world.government_structure = "None (uninhabited)"
        world.government_profile = "0-000"
        world.justice_profile = "---"
        world.law_profile = "0-00000"
        world.factions = []
        return

    # Centralisation and primary authority
    c_dm = 0
    if gov in (0, 7):
        c_dm -= 2
    elif gov >= 10:
        c_dm += 2
    centralisation = CENTRALISATION.get(
        min(12, max(2, Utils.D6(2) + c_dm)), 'Federal')
    authority = AUTHORITY.get(Utils.D6(2), 'Executive')

    world.centralisation = centralisation
    world.primary_authority = authority
    world.government_structure = random.choice(_STRUCTURES[centralisation])

    # Government profile: G-CAS (code, centralisation, authority, structure)
    world.government_profile = (
        f"{uwp.government}-{centralisation[0]}{authority[0]}"
        f"{'B' if authority == 'Balanced' else 'S'}")

    world.factions = generate_factions(gov)

    # Justice system profile: PSU-I-D
    primary = JUDICIAL_SYSTEMS.get(Utils.D6(2), 'Adversarial')
    has_secondary = Utils.D6(2) >= 8
    secondary = (JUDICIAL_SYSTEMS.get(Utils.D6(2), 'Adversarial')
                 if has_secondary else 'None')
    uniformity = LAW_UNIFORMITY.get(Utils.D6(2), 'Territorial')

    innocence_dm = 2 if law <= 4 else (-2 if law >= 10 else 0)
    presumption_of_innocence = (Utils.D6(2) + innocence_dm) >= 7

    death_dm = 0
    if law >= 9:
        death_dm += 2
    if gov in (13, 14, 15):
        death_dm += 2
    if law <= 3:
        death_dm -= 2
    death_penalty = (Utils.D6(2) + death_dm) >= 9

    world.justice_primary = primary
    world.justice_secondary = secondary
    world.law_uniformity = uniformity
    world.presumption_of_innocence = presumption_of_innocence
    world.death_penalty = death_penalty
    # PSU-I-D, using 'N' rather than a dash for absent elements so the three
    # components stay unambiguous when the profile is split.
    world.justice_profile = (
        f"{primary[0]}{secondary[0] if has_secondary else 'N'}{uniformity[0]}"
        f"-{'I' if presumption_of_innocence else 'G'}"
        f"-{'D' if death_penalty else 'N'}")

    # Law Level subcodes: O-WECPR
    world.law_weapons = _law_subcode(law)
    world.law_economic = _law_subcode(law)
    world.law_criminal = _law_subcode(law)
    world.law_private = _law_subcode(law)
    world.law_personal_rights = _law_subcode(law)
    world.law_profile = (
        f"{uwp.law_level}-"
        f"{Utils.eHex(world.law_weapons)}{Utils.eHex(world.law_economic)}"
        f"{Utils.eHex(world.law_criminal)}{Utils.eHex(world.law_private)}"
        f"{Utils.eHex(world.law_personal_rights)}")
