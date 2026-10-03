"""Dracul's original unsocketable glove defense as explicit nonethereal evidence."""

from pathlib import Path

from pricing.knowledge.artifacts import read_artifact
from pricing.knowledge.assessment.mechanics.socket_evidence import reviewed_native


MODE = 'draculs_total_defense'
ROOT = Path(__file__).resolve().parents[4]


def infer(row):
    props = row.get('properties', {})
    if (
        (row.get('rarity'), row.get('name'), row.get('base_code')) != ('unique', "Dracul's Grasp", 'uvg')
        or not (row.get('ethereal') is None or row['ethereal'] is False)
        or type(row.get('sockets')) is not int
        or row['sockets'] != 0
        or row.get('socket_contents') != 'empty'
        or not (row.get('base_upgrade') is None or row['base_upgrade'] is False)
        or not (props.get('1216') is None or props['1216'] is False)
        or not (props.get('738') is None or props['738'] is False)
        or props.get('930') not in (None, 'Elite')
        or ('402' in props and (type(props['402']) is not int or props['402'] != 0))
        or '399' in props
        or not reviewed_native(ROOT, read_artifact)
    ):
        return None
    ed, total = props.get('425'), props.get('1855')
    if type(ed) is not int or not 90 <= ed <= 120 or type(total) is not int:
        return None
    # Native Vampirebone Gloves56..65, intrinsic ED90..120, no flat defense.
    # Original ED sets base65+1. Minimum possible ethereal armor is already
    # above every nonethereal total; do not infer from ED or base identity alone.
    expected = 66 * (100 + ed) // 100
    ethereal_min = (56 * 3 // 2) * (100 + ed) // 100
    return False if total == expected and total < ethereal_min else None
