"""Shopping targets matched on decoded stats, never tooltip text or prices.

Only really good buys alert ("not just any +2 skills", the player, 2026-10-22); each case below was confirmed on the
scoped Traderie asks (SC/NL/PC/RotW, caches 2026-09-18 to 10-09, asks only, no fills) and the d2data affix tables, and
the cases are in README.md "Targets". Build-list candidates (starter / pre-runeword pieces, charges, Echoing weapons)
do not alert; the compiled build catalog stays available behind `build_candidates=True` for offline audits only.
"""

import json
from functools import cache
from pathlib import Path

from inventory_tracking.items.stat_constants import CLASS_NAMES, SKILL_TABS, StatId
from inventory_tracking.shop.amulets import match_amulet
from inventory_tracking.shop.catalog import match_catalog
from inventory_tracking.shop.staffmods import PRIMARY_SKILLS, companions


LIFE, STRENGTH, DEXTERITY, BLOCK, DAMAGE_REDUCED, MF, IAS, FRW, FBR, FCR = 7, 0, 2, 20, 36, 80, 93, 96, 102, 105
# Skill-tab layers are class_id * 8 + tree, in SKILL_TABS order.
# Gloves: +3 and 20 IAS (of Alacrity, the most a magic glove rolls): Javelin asks median 11.4 (5 sellers), Martial
# Arts Q1 4.05 (16), Bow Q1 4.05 (14); +3 Passive asks a median of 1 (10 sellers), so it stays in the shop
GLOVE_TREES = (0, 2, 50)  # Bow, Javelin, Martial Arts
JAVELIN_TREE = 2
CLAW_TYPES = ('h2h', 'h2h2')
# Jeweler's (4 sockets) of the Whale: 28 sellers, asks Q1 45.7 on any base tier; 81-89 life has 2 sellers, Amicae 2,
# Stability and Precision are weak or thin even on elite bases (2026-09-18 and 10-04)
WHALE = 90
# Jeweler's of Deflecting (20 block, 30 FBR): Monarch 74.6 -> 114 (17 sellers), Aegis / Ward from 79.9 (5), Paladin
# shields Q1 11.4 (10); a plain 4-socket Monarch is a 22.8 wall and no bare 4-socket Archon Plate is listed
DEFLECTING_BASES = ('Monarch', 'Aegis', 'Ward')
PALADIN_SHIELD = 'ashd'
# Javelins (the base's +1-3 Javelin automod in the total): +5 and 40 IAS (Maiden 3-6 Jah, 7 sellers), +6 and 30 IAS
# (3-12 Jah), +2 Amazon, +3 and 40 IAS (57.1-80); +1 Amazon has one seller at 4.05 and +5 / 30 is not listed
# A paid staffmod with a class or own-tree prefix, +5 or more in all (pricing/triage/import_class_rules.py: magic asks
# median 69 at +5 and 91 at +6 against 10 under +5)
PAID_TOTAL = 5
# Magic circlets (pricing/triage/import_affixed_rules.py): +3 tree and 20 FCR (2-6 sellers per tree, 9 in all, Q1
# 11.4); any 30 FRW (7 sellers from 11.4); +3 tree with a big suffix (6 sellers). A +2 class circlet, plain or with 20
# FCR (Q1 2.6), is not kept (pricing.html, 2026-10-21)
CIRCLET_TREES = (8, 9, 10, 17, 24, 57, 58)  # Fire, Lightning, Cold, Poison and Bone, Combat (Paladin), Eldritch, Chaos
CIRCLET_SUFFIXES = ((LIFE, 80, 'life'), (STRENGTH, 25, 'strength'), (DEXTERITY, 25, 'dexterity'), (MF, 30, 'MF'),
                    (DAMAGE_REDUCED, 20, '% damage reduction'))  # fmt: skip


@cache
def skill_targets():
    return json.loads(Path(__file__).with_name('skills.json').read_text())['skills']


def tree_name(layer):
    return SKILL_TABS[layer // 8][layer % 8]


def match_item(observation, *, build_candidates=False):
    """Resale patterns and explicitly labeled amulet build uses; no universal BiS claim."""
    item = observation['item']
    if item.get('identified') is not True:
        return []
    stats = {
        (r['memory_stat']['id'], r['memory_stat']['layer']): r['value']
        for r in observation.get('decoded_stats', [])
        if r.get('status') == 'decoded' and 'memory_stat' in r and 'value' in r
    }

    for row in observation.get('decoded_stats', []):
        # Combined enhanced-damage rows keep the native 17/18 payloads for the build catalog's Cruel targets.
        if row.get('status') == 'decoded' and row.get('memory_stats'):
            for stat in row['memory_stats']:
                if stat['id'] in (17, 18) and stat['layer'] == 0:
                    stats[stat['id'], 0] = stat['raw']

    unknown = {(s['id'], s['layer']) for s in observation.get('unresolved_stats', [])}

    def value(stat, layer=0):
        return 0 if (stat, layer) in unknown else stats.get((stat, layer), 0)

    def class_bonus(name):
        return value(StatId.CLASS_SKILLS, CLASS_NAMES.index(name))

    def tree(layer):
        return value(StatId.SKILL_TAB, layer)

    reasons = match_amulet(observation, stats)
    kind, base = item['item_type'], item['base_name']
    sockets, ias, fcr = value(StatId.SOCKETS), value(IAS), value(FCR)
    natives = [(t, value(StatId.CLASS_SINGLE_SKILL, t['id'])) for t in skill_targets()]
    natives = [(t, single) for t, single in natives if single >= 2]

    if item['rarity'] == 'magic':
        if kind == 'tors' and sockets == 4 and value(LIFE) >= WHALE:
            reasons.append(f"Jeweler's {base} of the Whale: 4 sockets + {value(LIFE):g} life")
        deflecting = base in DEFLECTING_BASES or kind == PALADIN_SHIELD
        if deflecting and sockets == 4 and value(BLOCK) >= 20 and value(FBR) >= 30:
            reasons.append(f"Jeweler's {base} of Deflecting (4 sockets / 20 block / 30 FBR)")
        if kind == 'circ':
            for layer in CIRCLET_TREES:
                if tree(layer) < 3:
                    continue
                if fcr >= 20:
                    reasons.append(f'+3 {tree_name(layer)} / {fcr:g} FCR {base}')
                for stat, minimum, label in CIRCLET_SUFFIXES:
                    if value(stat) >= minimum:
                        reasons.append(f'+3 {tree_name(layer)} / {value(stat):g} {label} {base}')
            if value(FRW) >= 30:
                reasons.append(f'{value(FRW):g} FRW {base}')
            if sockets >= 3 and (base == 'Diadem' or value(MF) >= 25):
                reasons.append(f"Artisan's {base}: 3 sockets" + (f' / {value(MF):g} MF' if value(MF) else ''))
        if kind == 'glov' and ias >= 20:
            for layer in GLOVE_TREES:
                if tree(layer) >= 3:
                    reasons.append(f'+3 {tree_name(layer)} / {ias:g} IAS gloves')
        if kind == 'ajav':
            javelin, amazon = tree(JAVELIN_TREE), class_bonus('Amazon')
            fast = (javelin >= 5 or (amazon >= 2 and javelin >= 3)) and ias >= 40
            if fast or (javelin >= 6 and ias >= 30):
                plus = f' / +{amazon:g} Amazon' if amazon else ''
                reasons.append(f'+{javelin:g} Javelin and Spear Skills / {ias:g} IAS javelin{plus}')
    for target, single in natives:
        if target['name'] not in PRIMARY_SKILLS:
            continue
        class_part = value(StatId.CLASS_SKILLS, target['class_id'])
        tree_part = tree(target['tab_layer'])
        if max(class_part, tree_part) < 2 or class_part + tree_part + single < PAID_TOTAL:
            continue
        prefix = (
            f'+{class_part:g} {CLASS_NAMES[target["class_id"]]}'
            if class_part >= tree_part
            else f'+{tree_part:g} {tree_name(target["tab_layer"])}'
        )
        extras = [
            f'+{n:g} {t["name"]}'
            for t, n in natives
            if t['name'] in companions(target['name']) and t['tab_layer'] == target['tab_layer']
        ]
        if kind in CLAW_TYPES and ias:
            extras.append(f'{ias:g} IAS')
        suffix = '; also ' + ' / '.join(extras) if extras else ''
        total = class_part + tree_part + single
        reasons.append(f'+{total:g} {target["name"]} ({prefix} +{single:g} staffmod){suffix}')
    if build_candidates:
        reasons.extend(match_catalog(observation, stats))
    return list(dict.fromkeys(reasons))
