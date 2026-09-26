"""Shopping targets that sell in this economy. Match decoded stats, never tooltip text or prices.

Every rule cites a priced blue pattern: guides/pricing.html §2 (blue table), pricing-primer
§3.3 and pindle-anya §4.1 (Anya rows), Traderie asks 2026-09-18/19. Build-list candidates
(starter / pre-runeword pieces, resistance gear, Teleport / Life Tap / Lower Resist charges,
Echoing weapons at a 1-Ist median behind 63 sellers) do not alert. The compiled build catalog
stays available behind `build_candidates=True` for offline audits only.
"""

import json
from functools import cache
from pathlib import Path

from inventory_tracking.items.stat_constants import CLASS_NAMES, SKILL_TABS, StatId
from inventory_tracking.shop.catalog import match_catalog


LIFE, DEXTERITY, BLOCK, DAMAGE_REDUCTION, IAS, FRW, FHR, FBR, FCR = 7, 2, 20, 34, 93, 96, 99, 102, 105
# Skill-tab layers are class_id * 8 + tree, in SKILL_TABS order.
GLOVE_TREES = (0, 1, 2, 50)  # Bow, Passive, Javelin, Martial Arts: "of Alacrity" gloves
JAVELIN_TREE = 2
WARCRIES = 34
TRAPS = 48
WARLOCK_TREES = (56, 57, 58)
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
    """Reasons to buy a loaded item for resale; a hit is a priced pattern, not a BiS claim."""
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

    def value(stat, layer=0):
        return stats.get((stat, layer), 0)

    def class_bonus(name):
        return value(StatId.CLASS_SKILLS, CLASS_NAMES.index(name))

    def tree(layer):
        return value(StatId.SKILL_TAB, layer)

    reasons = []
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
        if kind == 'phlm' and tree(WARCRIES) >= 3:
            reasons.append(f'Echoing Barbarian helm: +{tree(WARCRIES):g} Warcries')
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
        if native and ((kind == 'orb' and fcr >= 20) or (kind == 'scep' and fcr >= 10)):
            reasons.append(f'{base} / {fcr:g} FCR + ' + ' / '.join(f'+3 {t["name"]}' for t in native))
        if kind == 'head' and sockets >= 2 and class_bonus('Necromancer') >= 1:
            reasons.append(f'{base}: {sockets:g} sockets + {class_bonus("Necromancer"):g} Necromancer')
        if kind == 'grim':
            for layer in WARLOCK_TREES:
                if tree(layer) >= 3:
                    reasons.append(f'+{tree(layer):g} {tree_name(layer)} grimoire')

    for target in native:
        class_part = value(StatId.CLASS_SKILLS, target['class_id'])
        tree_part = tree(target['tab_layer'])
        if class_part >= 2 or tree_part >= 2:
            single = value(StatId.CLASS_SINGLE_SKILL, target['id'])
            bonus = class_part + tree_part
            reasons.append(f'+{bonus + single:g} {target["name"]} (+{bonus:g} class/tree +{single:g} staffmod)')
    # Two demanded +3 staffmods on one item (mastery + main skill) sell without a skill prefix.
    if len(native) >= 2:
        reasons.append(' / '.join(f'+3 {t["name"]}' for t in native))
    if build_candidates:
        reasons.extend(match_catalog(observation, stats))
    return list(dict.fromkeys(reasons))
