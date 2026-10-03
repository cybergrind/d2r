"""Shared original/upgraded defense proof for Gore Rider trade and exact prices."""

from pathlib import Path

from pricing.knowledge.artifacts import read_artifact
from pricing.knowledge.assessment.mechanics.socket_evidence import reviewed_native


MODE = 'gore_rider_original_defense'
VARIANT_MODE = 'gore_rider_variant_defense'
ROOT = Path(__file__).resolve().parents[4]


def _valid_variant(row, *, upgraded):
    props = row.get('properties', {})
    return not (
        (row.get('rarity'), row.get('name')) != ('unique', 'Gore Rider')
        or row.get('base_code') not in (('uhb',) if upgraded else (None, 'xhb'))
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
    if type(ed) is not int or not 160 <= ed <= 200 or type(total) is not int:
        return None
    # Original War Boots43..53 become54 with intrinsic ED. Upgraded Myrmidon
    # Boots reroll62..71; even their minimum exceeds the original at the same ED.
    expected = 54 * (100 + ed) // 100
    upgraded_min = 62 * (100 + ed) // 100
    ethereal_min = (43 * 3 // 2) * (100 + ed) // 100
    return 'xhb' if total == expected and total < min(upgraded_min, ethereal_min) else None


def infer(row):
    return False if original_code(row) else None


def variant_code(row):
    if row.get('base_code') != 'uhb':
        return original_code(row)
    if not _valid_variant(row, upgraded=True):
        return None
    props = row.get('properties', {})
    ed, total = props.get('425'), props.get('1855')
    if type(ed) is not int or not 160 <= ed <= 200 or type(total) is not int:
        return None
    # Upgrade rerolls62..71; perfect200% ED permits186..213 in steps of3.
    # Explicit elite identity separates it from original ethereal possibilities.
    totals = {base * (100 + ed) // 100 for base in range(62, 72)}
    ethereal_min = (62 * 3 // 2) * (100 + ed) // 100
    return 'uhb' if total in totals and total < ethereal_min else None


def infer_variant(row):
    return False if variant_code(row) else None
