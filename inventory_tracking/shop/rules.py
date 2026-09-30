"""Shopping targets matched on decoded stats, never tooltip text or prices.

Legacy resale patterns cite: guides/pricing.html §2 (blue table), pricing-primer
§3.3 and pindle-anya §4.1 (Anya rows), Traderie asks 2026-09-18/19. Build-list candidates
(starter / pre-runeword pieces, resistance gear, Teleport / Life Tap / Lower Resist charges,
Echoing weapons at a 1-Ist median behind 63 sellers) do not alert. The compiled build catalog
stays available behind `build_candidates=True` for offline audits only.
Reviewed +3 tree amulets and +5/+6 staffmod combinations are usefulness candidates
(AMULETS.md, SKILL_REVIEW.md), not verified price claims.
"""

import json
from functools import cache
from pathlib import Path

from inventory_tracking.items.stat_constants import CLASS_NAMES, SKILL_TABS, StatId
from inventory_tracking.shop.amulets import match_amulet
from inventory_tracking.shop.catalog import match_catalog
from inventory_tracking.shop.staffmods import PRIMARY_SKILLS, companions


LIFE, DEXTERITY, BLOCK, DAMAGE_REDUCTION, IAS, FRW, FHR, FBR, FCR = 7, 2, 20, 34, 93, 96, 99, 102, 105
# Skill-tab layers are class_id * 8 + tree, in SKILL_TABS order.
GLOVE_TREES = (0, 1, 2, 50)  # Bow, Passive, Javelin, Martial Arts: "of Alacrity" gloves
JAVELIN_TREE = 2
TRAPS = 48
CLAW_TYPES = ('h2h', 'h2h2')
# Any-affix 4-socket magic rolls of these bases sell at the 4os bucket minimum (9.3 / 11.4 Ist).
FOUR_SOCKET_ELITES = ('Monarch', 'Archon Plate')
# Jeweler's armor suffixes with multi-Jah asks: of the Whale 90-100, of Amicae, of Stability, of Precision.
JEWELERS_ARMOR = (
    (LIFE, 90, 'life'),
    (DAMAGE_REDUCTION, 15, 'damage reduction'),
    (FHR, 24, 'FHR'),
    (DEXTERITY, 10, 'dexterity'),
)
CLAW_STAFFMODS = ('Lightning Sentry', 'Death Sentry', 'Wake of Fire')


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
    # Native +3 staffmods of demanded skills; class/tree prefixes apply only to their own skill.
    native = [t for t in skill_targets() if value(StatId.CLASS_SINGLE_SKILL, t['id']) >= 3]

    if item['rarity'] == 'magic':
        if sockets == 4 and base in FOUR_SOCKET_ELITES:
            if base == 'Monarch' and value(BLOCK) >= 20 and value(FBR) >= 30:
                reasons.append("Jeweler's Monarch of Deflecting (4 sockets / 20 block / 30 FBR)")
            else:
                reasons.append(f"Jeweler's {base}: any 4-socket magic {base}")
        if kind == 'tors' and sockets == 4:
            for stat, minimum, label in JEWELERS_ARMOR:
                if value(stat) >= minimum:
                    reasons.append(f"Jeweler's armor: 4 sockets + {value(stat):g} {label}")
        if kind == 'circ':
            for class_id, name in enumerate(CLASS_NAMES):
                if value(StatId.CLASS_SKILLS, class_id) >= 2:
                    extras = [
                        label
                        for good, label in (
                            (fcr >= 20, f'{fcr:g} FCR'),
                            (sockets >= 2, f'{sockets:g} sockets'),
                            (value(FRW) >= 30, f'{value(FRW):g} FRW'),
                        )
                        if good
                    ]
                    reasons.append(f'+2 {name} {base}' + (' / ' + ' / '.join(extras) if extras else ' (no FCR)'))
            if sockets >= 3:
                frw = f' / {value(FRW):g} FRW' if value(FRW) >= 30 else ''
                reasons.append(f"Artisan's {base}: 3-socket magic {base}{frw}")
        if kind == 'glov' and ias >= 20:
            for layer in GLOVE_TREES:
                if tree(layer) >= 3:
                    reasons.append(f'+3 {tree_name(layer)} / {ias:g} IAS gloves')
        if kind in CLAW_TYPES and ias >= 30 and (tree(TRAPS) >= 3 or class_bonus('Assassin') >= 2):
            prefix = f'+{tree(TRAPS):g} Traps' if tree(TRAPS) >= 3 else f'+{class_bonus("Assassin"):g} Assassin'
            mods = ''.join(
                f' (+{value(StatId.CLASS_SINGLE_SKILL, t["id"]):g} {t["name"]})'
                for t in native
                if t['name'] in CLAW_STAFFMODS
            )
            reasons.append(f'{prefix} / {ias:g} IAS claws{mods}')
        if (
            kind == 'ajav'
            and tree(JAVELIN_TREE) >= 3
            and ias >= 40
            and (tree(JAVELIN_TREE) >= 5 or class_bonus('Amazon') >= 1)
        ):
            amazon = f' / +{class_bonus("Amazon"):g} Amazon' if class_bonus('Amazon') else ''
            reasons.append(f'+{tree(JAVELIN_TREE):g} Javelin and Spear Skills / {ias:g} IAS javelin{amazon}')
    for target in native:
        if target['name'] not in PRIMARY_SKILLS:
            continue
        class_part = value(StatId.CLASS_SKILLS, target['class_id'])
        tree_part = tree(target['tab_layer'])
        if class_part >= 2 or tree_part >= 3:
            single = value(StatId.CLASS_SINGLE_SKILL, target['id'])
            bonus = class_part + tree_part
            prefix = (
                f'+{class_part:g} {CLASS_NAMES[target["class_id"]]}'
                if class_part >= 2
                else f'+{tree_part:g} {tree_name(target["tab_layer"])}'
            )
            extras = [f'+3 {t["name"]}' for t in native if t['name'] in companions(target['name'])]
            suffix = '; also ' + ' / '.join(extras) if extras else ''
            reasons.append(f'+{bonus + single:g} {target["name"]} ({prefix} +{single:g} staffmod){suffix}')
    if build_candidates:
        reasons.extend(match_catalog(observation, stats))
    return list(dict.fromkeys(reasons))
