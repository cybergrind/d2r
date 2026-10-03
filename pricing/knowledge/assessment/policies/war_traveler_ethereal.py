"""War Traveler defense proof, preserving original versus upgraded base identity."""

from pathlib import Path

from pricing.knowledge.artifacts import read_artifact
from pricing.knowledge.assessment.mechanics.socket_evidence import reviewed_native


MODE = 'war_traveler_total_defense'
ROOT = Path(__file__).resolve().parents[4]


def infer(row):
    props = row.get('properties', {})
    code, ethereal = row.get('base_code'), row.get('ethereal')
    if code not in ('xtb', 'utb'):
        return None
    upgraded = code == 'utb'
    if (
        (row.get('rarity'), row.get('name')) != ('unique', 'War Traveler')
        or not (ethereal is None or ethereal is False)
        or type(row.get('sockets')) is not int
        or row['sockets'] != 0
        or row.get('socket_contents') != 'empty'
        or not (row.get('base_upgrade') is None or row['base_upgrade'] is upgraded)
        or not (props.get('1216') is None or props['1216'] is upgraded)
        or not (props.get('738') is None or props['738'] is False)
        or props.get('930') not in (None, 'Elite' if upgraded else 'Exceptional')
        or ('402' in props and (type(props['402']) is not int or props['402'] != 0))
        or not reviewed_native(ROOT, read_artifact)
    ):
        return None
    ed, total = props.get('425'), props.get('1855')
    if ed is not None and (type(ed) is not int or not 150 <= ed <= 190):
        return None
    if ethereal is False and '1855' not in props:
        return False
    if type(total) is not int:
        return None
    rolls = range(150, 191) if ed is None else (ed,)
    # Native ED armor uses max+1 (47+1); upgrading rerolls actual base AC59..68.
    # Boots cannot socket or receive flat-defense modifiers from inserted items.
    bases = range(59, 69) if upgraded else (48,)
    totals = {base * (100 + roll) // 100 for base in bases for roll in rolls}
    # Conservative ethereal lower bound suffices; never reverse an overlapping total.
    ethereal_min = (59 if upgraded else 39) * 3 // 2 * (100 + min(rolls)) // 100
    if total not in totals or total >= ethereal_min:
        return None
    return False
