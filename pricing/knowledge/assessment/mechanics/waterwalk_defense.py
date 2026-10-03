"""Original/upgraded Waterwalk defense proof for exact comparisons."""

from pathlib import Path

from pricing.knowledge.artifacts import read_artifact
from pricing.knowledge.assessment.mechanics.socket_evidence import reviewed_native


VARIANT_MODE = 'waterwalk_variant_defense'
ROOT = Path(__file__).resolve().parents[4]


def _valid_variant(row, *, upgraded):
    props = row.get('properties', {})
    return not (
        (row.get('rarity'), row.get('name')) != ('unique', 'Waterwalk')
        or row.get('base_code') not in (('uvb',) if upgraded else (None, 'xvb'))
        or not (row.get('ethereal') is None or row['ethereal'] is False)
        or not (row.get('base_upgrade') is None or row['base_upgrade'] is upgraded)
        or type(row.get('sockets')) is not int
        or row['sockets'] != 0
        or row.get('socket_contents') != 'empty'
        or not (props.get('1216') is None or props['1216'] is upgraded)
        or not (props.get('738') is None or props['738'] is False)
        or props.get('930') not in (None, 'Elite' if upgraded else 'Exceptional')
        or ('402' in props and (type(props['402']) is not int or props['402'] != 0))
        or '399' in props
        or not reviewed_native(ROOT, read_artifact)
    )


def original_code(row):
    if not _valid_variant(row, upgraded=False):
        return None
    props = row.get('properties', {})
    ed, total = props.get('425'), props.get('1855')
    if type(ed) is not int or not 180 <= ed <= 210 or type(total) is not int:
        return None
    # Original Sharkskin Boots33..39 become40 with intrinsic ED. Upgraded
    # Scarabshell Boots reroll56..65, above the original at the same ED.
    expected = 40 * (100 + ed) // 100
    upgraded_min = 56 * (100 + ed) // 100
    ethereal_min = (33 * 3 // 2) * (100 + ed) // 100
    return 'xvb' if total == expected and total < min(upgraded_min, ethereal_min) else None


def variant_code(row):
    if row.get('base_code') != 'uvb':
        return original_code(row)
    if not _valid_variant(row, upgraded=True):
        return None
    props = row.get('properties', {})
    ed, total = props.get('425'), props.get('1855')
    if type(ed) is not int or not 180 <= ed <= 210 or type(total) is not int:
        return None
    # Upgrade rerolls56..65; enumerate integer-rounded totals, not a continuous band.
    # Explicit elite identity separates it from original ethereal possibilities.
    totals = {base * (100 + ed) // 100 for base in range(56, 66)}
    ethereal_min = (56 * 3 // 2) * (100 + ed) // 100
    return 'uvb' if total in totals and total < ethereal_min else None


def infer_variant(row):
    return False if variant_code(row) else None


def valid_total_defense(facts, *, market_properties=None):
    if (
        facts.identified is not True
        or facts.gaps
        or (market_properties is None and facts.capture_complete is not True)
        or any(key in facts.stats for key in ('214:0', '215:0'))
    ):
        return False
    props = dict(market_properties or {})
    for key, prop in [('16:0', '425'), ('31:0', '1855')]:
        stat = facts.stats.get(key, {})
        if stat.get('status') != 'decoded' or type(stat.get('value')) is not int:
            return False
        props[prop] = stat['value']
    row = {
        'rarity': facts.rarity,
        'name': facts.name,
        'base_code': facts.base_code,
        'ethereal': facts.ethereal,
        'sockets': facts.sockets,
        'socket_contents': facts.socket_contents,
        'properties': props,
    }
    return variant_code(row) == facts.base_code
