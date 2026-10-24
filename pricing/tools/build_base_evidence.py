"""Build pricing/data/base-evidence.json (pricing/knowledge/base_evidence.py): fills, asks and bids per plain-base
facet from the 2026-10-23 Traderie pulls, plus the KB's asks bands per plain key.

The facets and their matching are the base-price study's (rca/2026-10-23/base-prices-findings.md, "Sources, and how
to read the numbers"):
- fills: Traderie Recent Trades (accepted and completed offers) read through the player's browser, PC/SC/NL/RotW
  by the listing's own properties, one row per offer id, since FILLS_SINCE; the paid price is the counter-offer if
  any, else the listing's, an OR-group its cheapest;
- asks: the scoped sell pages (pricing.knowledge.scope `in_scope`), active listings only, one vote per seller (their
  cheapest priced ask);
- bids: the scoped buy pages (`selling` false), one vote per distinct buyer (their highest priced bid).
Only white rows (normal, superior; a seller's "normal" with an ED roll counts as superior). A plain facet matches only
listings with no property but a white base's own (PLAIN_OK; the all-res automod on the shields that roll it).

Item codes come from the game data (inventory_tracking.items.metadata, by the base's name), staff-mod skill ids from
its skills table, both resolved by the Traderie names and property labels (pricing/data/appraisal-properties.json);
nothing is written from memory. The raw pulls are read here only: the built file is the runtime's.

Run: uv run --offline python -m pricing.tools.build_base_evidence
"""

import argparse
import datetime
import glob
import json
import re
import statistics
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from functools import cache
from pathlib import Path
from typing import Any

from pricing.knowledge.base_evidence import EVIDENCE_FILE, key, plain_item
from pricing.knowledge.market import convert_groups
from pricing.knowledge.refresh import atomic_json
from pricing.knowledge.scope import in_scope


__all__ = ['FACETS', 'band_record', 'build', 'kb_records', 'main', 'match', 'wpb_records']

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / 'pricing' / 'raw' / 'traderie'
PULLED = '2026-10-23'
ASK_DIRS = ('pull-20261023-scoped', 'pull-20261023-bases')
FILL_DIRS = ('recent-20261009', 'recent-20261023', 'recent-20261023-pages')  # deduplicated by offer id
BID_DIRS = ('buy-side-20261023',)
FILLS_SINCE = '2026-07-01'
LADDER = ROOT / 'pricing' / 'data' / 'wp-f-ladder.json'
CATALOG = ROOT / 'pricing' / 'data' / 'appraisal-traderie-catalog.json'
PROPERTIES = ROOT / 'pricing' / 'data' / 'appraisal-properties.json'
WPB = ROOT / 'pricing' / 'data' / 'wp-b-prices.json'
# Traderie property ids (pricing/data/appraisal-properties.json labels)
RARITY, ETHEREAL, SOCKETS, ALL_RES, ED_ARMOR, ED_WEAPON, DEFENSE, DEFENSE_ETH = 797, 738, 402, 441, 425, 510, 399, 1855
PLATFORM, MODE, LADDER_PROP, VERSION = 798, 799, 800, 1854
# A white base's own properties on Traderie: scope, sockets, ED, defense, durability, level, AR, socket contents.
# Anything else (FCR, life, skills, single resists...) is a magic or rare item labelled normal: not a plain base
PLAIN_OK = frozenset((797, 798, 799, 800, 1854, 402, 425, 399, 1855, 937, 738, 510, 796, 934, 932, 423))
RES_BASES = frozenset(('Sacred Rondache', 'Sacred Targe', 'Targe'))
NAMES = {'Kris': 'Kriss', 'Stiletto': 'Stilleto'}  # Traderie's spelling -> the game's
CLASSES = {'Warlock': 'war', 'Assassin': 'ass'}
SKILL_LABEL = re.compile(r'^\+\{\{value\}\} to (.+) \((\w+) Only\)$')
WPB_TYPES = frozenset(('tors', 'shie', 'swor', 'axe', 'pole', 'mace', 'spea', 'helm'))
WPB_BUCKET = re.compile(r'^(\d)os/(eth|noneth)/(normal|superior)(/15ed)?$')
WPB_LISTINGS = 3  # a wp-b bucket counts with this many priced listings
PERFECT_ED = 15


# -- the facets (the study's specs.py): a base set x grade x eth x sockets (x res band or staff-mod condition)

DAGGERS = ['Kris', 'Blade', 'Cinquedeas', 'Stiletto', 'Fanged Knife', 'Legend Spike']
TALONS = ['Greater Talons', 'Runic Talons']
TOMES = [
    'Tome',
    'Codex',
    'Grimoire',
    'Burnt Text',
    'Dark Tome',
    'Possessed Grimoire',
    'Occult Tome',
    'Blasphemous Grimoire',
]
VOID_MODS = (
    'Abyss',
    'Hex: Purge',
    'Apocalypse',
    'Eldritch Blast',
    'Summon Defiler',
    'Hex: Siphon',
    'Summon Tainted',
    'Sigil: Death',
    'Engorge',
    'Enhanced Entropy',
    'Flame Wave',
    'Echoing Strike',
    'Consume',
    'Bind Demon',
    'Miasma Chain',
    'Mirrored Blades',
    'Psychic Ward',
)
CLAW_MODS = (
    'Phoenix Strike',
    'Lightning Sentry',
    'Death Sentry',
    'Wake of Fire',
    'Claws of Thunder',
    'Blades of Ice',
    'Wake of Inferno',
    'Venom',
    'Fade',
    'Blade Fury',
    'Blade Shield',
    'Dragon Flight',
    'Mind Blast',
)
ARMORS = [
    'Archon Plate',
    'Dusk Shroud',
    'Wire Fleece',
    'Mage Plate',
    'Sacred Armor',
    'Great Hauberk',
    'Lacquered Plate',
    'Shadow Plate',
    'Balrog Skin',
    'Hellforge Plate',
    'Kraken Shell',
    'Boneweave',
    'Diamond Mail',
    'Loricated Mail',
    'Scarab Husk',
    'Wyrmhide',
]
OTHERS = [
    ('Phase Blade', [5, 2, 6]),
    ('Colossus Blade', [1, 5, 6]),
    ('Spired Helm', [2, 3]),
    ('Bone Visage', [2, 3]),
    ('Demonhead', [1, 3]),
    ('Coronet', [0]),
    ('Circlet', [0, 2]),
    ('Flail', [0, 1, 2, 3, 4, 5]),
    ('Monarch', [4]),
    ('Bone Shield', [0, 2]),
    ('Great Bow', [4]),
    ('Short Battle Bow', [4]),
    ('Short War Bow', [4]),
    ('Naga', [5, 6]),
    ('Great Poleaxe', [4, 6]),
    ('Cryptic Axe', [4]),
    ('Colossus Voulge', [0, 1, 4]),
    ('Mancatcher', [4]),
]
SHEET = [
    ('Grand Crown', [3]),
    ('Grim Helm', [3]),
    ('Dragon Shield', [3]),
    ('Troll Nest', [2, 3]),
    ('Grim Shield', [2]),
    ('Hyperion', [2]),
    ('Berserker Axe', [4, 5]),
    ('Knout', [3]),
    ('Scourge', [3]),
    ('Crystal Sword', [4, 5]),
    ('War Scepter', [4, 5]),
    ('Caduceus', [4]),
    ('War Pike', [5, 6]),
    ('Matriarchal Bow', [5]),
    ('Grand Matron Bow', [5]),
    ('Hydra Bow', [4, 5]),
    ('Ward Bow', [4]),
    ('Spider Bow', [4]),
    ('Cryptic Sword', [3, 4]),
    ('Legend Sword', [3]),
    ('Feral Axe', [4]),
    ('Balrog Blade', [4]),
    ('Archon Staff', [6]),
    ('Rune Staff', [6]),
    ('War Staff', [6]),
    ('Greater Claws', [3]),
    ('Elder Staff', [4]),
    ('Shillelagh', [4]),
    ('Decapitator', [5]),
    ('Thresher', [4, 5]),
    ('Giant Thresher', [5]),
    ('Colossus Sword', [4]),
]
GRADES = ('normal', 'sup<15', 'sup15')
RES45, RES40 = (45, 99), (40, 44)


def _slug(name: str) -> str:
    return name.lower().replace(':', '').replace(' ', '-')


def _facets() -> Iterator[dict[str, Any]]:
    """Every facet spec: id, group, label, Traderie base names and conditions (skills by name)."""

    def spec(group: str, id: str, label: str, names: list[str], **conditions: Any) -> dict[str, Any]:
        return {'group': group, 'id': id, 'label': label, 'names': names, **conditions}

    group = 'Sacred shields (45 / 40-44 all res)'
    for name, short in (('Sacred Rondache', 'rondache'), ('Sacred Targe', 'targe')):
        for res, said in ((RES45, '45'), (RES40, '40-44')):
            for eth in (False, True):
                for sockets in (0, 3, 4):
                    for grade in GRADES:
                        yield spec(
                            group,
                            f'{short}-{said}res-{"eth-" if eth else ""}{sockets}os-{grade}',
                            f'{name} {said} res {"eth " if eth else ""}{sockets}os {grade}',
                            [name],
                            grade=grade,
                            eth=eth,
                            sockets=[sockets],
                            res=res,
                            plain=True,
                        )
    yield spec(
        group,
        'targe-superior-45res',
        'Targe (pa1) superior 45 res, any os',
        ['Targe'],
        grade='superior',
        res=RES45,
        plain=True,
    )
    yield spec(
        group,
        'targe-normal-45res',
        'Targe (pa1) normal 45 res, any os',
        ['Targe'],
        grade='normal',
        res=RES45,
        plain=True,
    )

    group = 'Void daggers (Kriss / Blade / Cinquedeas / Stilleto / Fanged Knife / Legend Spike)'
    for sockets in (3, 0):
        for mod in VOID_MODS:
            yield spec(
                group,
                f'dagger-{sockets}os-plus3-{_slug(mod)}-alone',
                f'{sockets}os +3 {mod} alone (others <= +1)',
                DAGGERS,
                sockets=[sockets],
                exact=[(mod, 3)],
                others_max=1,
            )
        for mod in (
            'Abyss',
            'Hex: Purge',
            'Hex: Siphon',
            'Sigil: Death',
            'Summon Tainted',
            'Enhanced Entropy',
            'Flame Wave',
        ):
            yield spec(
                group,
                f'dagger-{sockets}os-plus2-{_slug(mod)}-alone',
                f'{sockets}os +2 {mod} alone (others <= +1)',
                DAGGERS,
                sockets=[sockets],
                exact=[(mod, 2)],
                others_max=1,
            )
    yield spec(
        group,
        'dagger-3os-abyss2-mchain2',
        '3os Abyss >= 2 and Miasma Chain >= 2',
        DAGGERS,
        sockets=[3],
        mods=[('Abyss', 2), ('Miasma Chain', 2)],
    )
    yield spec(
        group,
        'dagger-3os-abyss2only-mchain2',
        '3os Abyss = 2 and Miasma Chain >= 2 (no +3 Abyss)',
        DAGGERS,
        sockets=[3],
        exact=[('Abyss', 2)],
        mods=[('Miasma Chain', 2)],
    )
    yield spec(
        group,
        'dagger-3os-fwave3',
        '3os Flame Wave >= 3, any companions',
        DAGGERS,
        sockets=[3],
        mods=[('Flame Wave', 3)],
    )
    yield spec(
        group,
        'dagger-3os-echo3',
        '3os Echoing Strike >= 3, any companions',
        DAGGERS,
        sockets=[3],
        mods=[('Echoing Strike', 3)],
    )
    yield spec(
        group, 'dagger-3os-consume2', '3os Consume >= 2, any companions', DAGGERS, sockets=[3], mods=[('Consume', 2)]
    )
    yield spec(
        group,
        'dagger-3os-abyss2-sdeath2',
        '3os Abyss >= 2 and Sigil: Death >= 2',
        DAGGERS,
        sockets=[3],
        mods=[('Abyss', 2), ('Sigil: Death', 2)],
    )
    yield spec(
        group,
        'dagger-3os-abyss3-plus2',
        '3os +3 Abyss with a second mod >= 2 (any)',
        DAGGERS,
        sockets=[3],
        mods=[('Abyss', 3)],
        anymods=[(mod, 2) for mod in VOID_MODS if mod != 'Abyss'],
    )
    yield spec(
        group,
        'dagger-3os-eb-def-siph3-plus2',
        '3os +3 EB / Defiler / Siphon with a second mod >= 2',
        DAGGERS,
        sockets=[3],
        anymods=[('Eldritch Blast', 3), ('Summon Defiler', 3), ('Hex: Siphon', 3)],
        second=2,
    )
    yield spec(
        group,
        'dagger-3os-apoc3-abyss2',
        '3os +3 Apocalypse with Abyss >= 2',
        DAGGERS,
        sockets=[3],
        mods=[('Apocalypse', 3), ('Abyss', 2)],
    )
    yield spec(
        group,
        'dagger-0os-plain',
        '0os, no staff mods (log: Blade / Fanged Knife 0os)',
        DAGGERS,
        sockets=[0],
        plain=True,
    )

    group = 'Assassin claws (Greater / Runic Talons)'
    for sockets in (3, 0):
        for mod in CLAW_MODS:
            yield spec(
                group,
                f'claw-{sockets}os-plus3-{_slug(mod)}',
                f'{sockets}os +3 {mod}, any companions',
                TALONS,
                sockets=[sockets],
                mods=[(mod, 3)],
            )
    for mod in ('Lightning Sentry', 'Phoenix Strike', 'Claws of Thunder', 'Death Sentry'):
        yield spec(
            group,
            f'claw-3os-plus3-{_slug(mod)}-alone',
            f'3os +3 {mod} alone (others <= +1)',
            TALONS,
            sockets=[3],
            exact=[(mod, 3)],
            others_max=1,
        )
        yield spec(
            group,
            f'claw-3os-plus3-{_slug(mod)}-plus2',
            f'3os +3 {mod} with a second claw mod >= +2',
            TALONS,
            sockets=[3],
            mods=[(mod, 3)],
            anymods=[(other, 2) for other in CLAW_MODS if other != mod],
        )
    yield spec(
        group,
        'claw-3os-ds2',
        '3os +2 Death Sentry (log: Runic Talons +1 CoS +1 DT +2 DS)',
        TALONS,
        sockets=[3],
        exact=[('Death Sentry', 2)],
    )
    yield spec(
        group,
        'claw-any-woi1',
        'any +1/+2 Wake of Inferno, no +3 anywhere (log: Runic 0os +1 WoI)',
        TALONS,
        mods=[('Wake of Inferno', 1)],
        best=2,
    )

    group = 'Warlock off-hands (grimoires, tomes)'
    for mod in (
        'Bind Demon',
        'Abyss',
        'Apocalypse',
        'Summon Tainted',
        'Sigil: Death',
        'Flame Wave',
        'Consume',
        'Summon Defiler',
        'Eldritch Blast',
    ):
        yield spec(
            group, f'tome-2os-plus3-{_slug(mod)}', f'2os +3 {mod}, any companions', TOMES, sockets=[2], mods=[(mod, 3)]
        )
    yield spec(
        group,
        'tome-0os-plus2',
        '0os best mod +2 (log: Grimoire +2 Rancor, Blasphemous +2 Flame Wave, Codex +2 Defiler)',
        TOMES,
        sockets=[0],
        best=2,
    )
    yield spec(group, 'tome-2os-plus2', '2os best mod +2', TOMES, sockets=[2], best=2)
    yield spec(
        group, 'tome-1os-any', '1os any (log: Codex 1os +3 Engorge, Burnt Text 1os +1 Entropy)', TOMES, sockets=[1]
    )
    yield spec(
        group, 'tome-0os-plain', '0os, no staff mods (log: Superior Codex 0os 11% ED)', TOMES, sockets=[0], plain=True
    )

    plain = [
        ('Elite and exceptional body armor (eth / ED grade)', [(name, [0, 2, 3, 4]) for name in ARMORS]),
        ('Other plain bases (log, dropped rows)', OTHERS),
        ("Runeword bases from the player's sheet", SHEET),
    ]
    for group, bases in plain:
        for name, socket_counts in bases:
            for eth in (False, True):
                for sockets in socket_counts:
                    for grade in GRADES:
                        yield spec(
                            group,
                            f'{_slug(name)}-{"eth-" if eth else ""}{sockets}os-{grade}',
                            f'{name} {"eth " if eth else ""}{sockets}os {grade}',
                            [name],
                            grade=grade,
                            eth=eth,
                            sockets=[sockets],
                            plain=True,
                        )


FACETS = tuple(_facets())


# -- reading the pulls


@cache
def _currencies() -> dict[str, float]:
    ladder = json.loads(LADDER.read_text())
    return {name.lower(): row['ist'] for name, row in ladder.items() if isinstance(row, dict) and 'ist' in row}


@cache
def _catalog() -> dict[str, str]:
    return {str(item['id']): item['name'] for item in json.loads(CATALOG.read_text())['items']}


@cache
def class_skills() -> dict[int, tuple[str, str]]:
    """Traderie property id -> (skill name, class code) for every '+N to <skill> (<Class> Only)' label of the classes
    the facets read (skill trees included: they count as a companion mod)."""
    found = {}
    for prop, row in json.loads(PROPERTIES.read_text())['properties'].items():
        for label in row.get('labels') or ():
            matched = SKILL_LABEL.match(label)
            if matched and matched[2] in CLASSES:
                found[int(prop)] = (matched[1], CLASSES[matched[2]])
    return found


@cache
def _props_by_skill() -> dict[str, int]:
    return {name: prop for prop, (name, _) in class_skills().items()}


def props(listing: Mapping[str, Any]) -> dict[int, Any]:
    out = {}
    for prop in listing.get('properties') or ():
        value = prop.get('number')
        if value is None:
            value = prop.get('string') if prop.get('string') is not None else prop.get('bool')
        out[int(prop['property_id'])] = value
    return out


def _row(listing: Mapping[str, Any], name: str, price: float | None, when: str) -> dict[str, Any]:
    found = props(listing)
    sockets = found.get(SOCKETS)
    return {
        'name': name,
        'rarity': found.get(RARITY),
        'eth': bool(found.get(ETHEREAL)),
        'sockets': 0 if sockets is False else sockets,
        'ed': found.get(ED_ARMOR) or found.get(ED_WEAPON) or 0,
        'res': found.get(ALL_RES) or 0,
        'p': found,
        'price': price,
        'when': when,
        'who': str(listing.get('seller_id')),
    }


def _listings(dirs: Iterable[str]) -> Iterator[tuple[Mapping[str, Any], Path]]:
    for directory in dirs:
        for path in sorted(glob.glob(str(RAW / directory / '*.json'))):
            for listing in json.loads(Path(path).read_text()).get('listings') or ():
                if isinstance(listing, dict) and 'properties' in listing:
                    yield listing, Path(path)


def asks(names: set[str]) -> list[dict[str, Any]]:
    """The active scoped sell listings of these Traderie names, one row per listing id."""
    rows, seen = [], set()
    for listing, _ in _listings(ASK_DIRS):
        name = _catalog().get(str(listing.get('item_id')))
        if name not in names or not in_scope(listing) or str(listing.get('id')) in seen:
            continue
        seen.add(str(listing.get('id')))
        if listing.get('selling') is False or listing.get('active') is False or listing.get('completed') is True:
            continue
        price, _ = convert_groups(listing.get('prices'), _currencies())
        if listing.get('amount') not in (1, None) and listing.get('stock'):
            price = None
        rows.append(_row(listing, name, price, (listing.get('updated_at') or '')[:10]))
    return rows


def _paid(prices: Iterable[Mapping[str, Any]] | None) -> float | None:
    """The cheapest OR-group of an offer's prices in Ist; None when a currency is unknown."""
    groups: dict[Any, float] = {}
    for price in prices or ():
        value = _currencies().get((price.get('name') or '').lower().removesuffix(' rune'))
        if value is None:
            return None
        group = price.get('group') or 0
        groups[group] = groups.get(group, 0) + value * (price.get('quantity') or 1)
    return min(groups.values()) if groups else None


def fills(names: set[str]) -> list[dict[str, Any]]:
    """Traderie Recent Trades (accepted and completed offers) of these names, PC/SC/NL/RotW, one row per offer id,
    since FILLS_SINCE."""
    rows, seen = [], set()
    for directory in FILL_DIRS:
        for path in sorted(glob.glob(str(RAW / directory / '*.json'))):
            doc = json.loads(Path(path).read_text())
            answers = doc.get('api', []) if 'api' in doc else [{'url': '/offers?', 'body': json.dumps(doc)}]
            for answer in answers:
                if '/offers?' not in answer['url'] or not answer.get('body'):
                    continue
                for offer in json.loads(answer['body'], strict=False).get('offers', []):
                    listing = offer.get('listing') or {}
                    item = listing.get('item') or {}
                    name = (item.get('name') if isinstance(item, dict) else None) or _catalog().get(
                        str(listing.get('item_id'))
                    )
                    if offer['id'] in seen or name not in names:
                        continue
                    found = props(listing)
                    if (found.get(PLATFORM), found.get(MODE), found.get(LADDER_PROP), found.get(VERSION)) != (
                        'PC',
                        'softcore',
                        False,
                        'reign of the warlock',
                    ):
                        continue
                    seen.add(offer['id'])
                    when = offer['updated_at'][:10]
                    if when >= FILLS_SINCE:
                        rows.append(_row(listing, name, _paid(offer.get('prices') or listing.get('prices')), when))
    return rows


def bids(names: set[str]) -> list[dict[str, Any]]:
    """The scoped buy listings (selling false) of these names, one row per listing id; `who` is the buyer."""
    rows, seen = [], set()
    for listing, _ in _listings(BID_DIRS):
        name = _catalog().get(str(listing.get('item_id')))
        if name not in names or str(listing.get('id')) in seen or not in_scope(listing):
            continue
        if listing.get('selling') is not False:
            continue
        seen.add(str(listing.get('id')))
        price, _ = convert_groups(listing.get('prices'), _currencies())
        if listing.get('amount') not in (1, None) and listing.get('stock'):
            price = None
        rows.append(_row(listing, name, price, (listing.get('updated_at') or '')[:10]))
    return rows


# -- matching and bands


def _level(row: Mapping[str, Any], prop: int) -> int:
    value = row['p'].get(prop)
    return int(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else 0


def _grade(row: Mapping[str, Any], grade: str) -> bool:
    if row['rarity'] not in ('normal', 'superior'):
        return False
    superior = row['rarity'] == 'superior' or (row['ed'] or 0) > 0
    return {
        'normal': not superior,
        'sup<15': superior and row['ed'] < PERFECT_ED,
        'sup15': row['ed'] >= PERFECT_ED,
        'superior': superior,
        'white': True,
    }[grade]


def match(spec: Mapping[str, Any], row: Mapping[str, Any]) -> bool:
    """Whether a pulled row (`asks`, `fills`, `bids`) is of the facet `spec`."""
    if row['name'] not in spec['names'] or not _grade(row, spec.get('grade', 'white')):
        return False
    if spec.get('eth') is not None and row['eth'] != spec['eth']:
        return False
    if spec.get('sockets') is not None and row['sockets'] not in spec['sockets']:
        return False
    if spec.get('res') and not spec['res'][0] <= (row['res'] or 0) <= spec['res'][1]:
        return False
    if spec.get('plain'):
        allowed = PLAIN_OK | ({ALL_RES} if row['name'] in RES_BASES else set())
        if any(prop not in allowed for prop, value in row['p'].items() if value not in (None, False, 0, '')):
            return False
    skill = _props_by_skill()
    mods = class_skills()
    if 'best' in spec and max((_level(row, prop) for prop in mods), default=0) != spec['best']:
        return False
    if any(_level(row, skill[name]) < level for name, level in spec.get('mods', ())):
        return False
    if any(_level(row, skill[name]) != level for name, level in spec.get('exact', ())):
        return False
    anymods = spec.get('anymods') or ()
    if anymods and not any(_level(row, skill[name]) >= level for name, level in anymods):
        return False
    if 'second' in spec:  # a second staff mod (a skill, as the ground's 107 stats) at this level besides the first
        levels = sorted((_level(row, prop) for prop, named in mods.items() if named in _skill_ids()), reverse=True)
        if len(levels) < 2 or levels[1] < spec['second']:
            return False
    if 'others_max' in spec:
        named = {skill[name] for name, _ in (*spec.get('mods', ()), *spec.get('exact', ()), *anymods)}
        if max((_level(row, prop) for prop in mods if prop not in named), default=0) > spec['others_max']:
            return False
    return True


def _q1(values: list[float]) -> float:
    return values[0] if len(values) < 2 else statistics.quantiles(values, n=4, method='inclusive')[0]


def _vote(rows: Iterable[Mapping[str, Any]], better: Callable[[float, float], bool]) -> dict[str, Mapping[str, Any]]:
    best: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        if row['price'] is not None and (row['who'] not in best or better(row['price'], best[row['who']]['price'])):
            best[row['who']] = row
    return best


def band_record(kind: str, rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """The facet's `kind` record ('fills', 'asks', 'bids') over its matched rows. Pure."""
    if kind == 'fills':
        paid = sorted(row['price'] for row in rows if row['price'] is not None)
        when = sorted(row['when'] for row in rows)
        found: dict[str, Any] = {'n': len(paid)}
        if paid:
            found |= {
                'q1': round(_q1(paid), 2),
                'median': round(statistics.median(paid), 2),
                'min': round(paid[0], 2),
                'max': round(paid[-1], 2),
                'dates': [when[0], when[-1]],
            }
        return found
    if kind == 'asks':
        voted = _vote(rows, lambda new, old: new < old)
        values = sorted(row['price'] for row in voted.values())
        dates = sorted({row['when'] for row in voted.values() if row['when']})
        found = {'sellers': len(values), 'listings': len(rows)}
        if values:
            found |= {
                'q1': round(_q1(values), 2),
                'median': round(statistics.median(values), 2),
                'min': round(values[0], 2),
                'max': round(values[-1], 2),
                'dates': [dates[0], dates[-1]],
            }
        return found
    voted = _vote(rows, lambda new, old: new > old)
    offers = sorted((row['price'] for row in voted.values()), reverse=True)
    dates = sorted({row['when'] for row in rows if row['when']})
    return {
        'buyers': len(offers),
        'buyers_ge4': sum(offer >= 4 for offer in offers),
        'offers': [round(offer, 2) for offer in offers[:8]],
        'dates': [dates[0], dates[-1]] if dates else None,
    }


# -- the facet's game facts (codes, skill ids) for the host


@cache
def _bases() -> dict[str, Mapping[str, Any]]:
    from inventory_tracking.items.metadata import metadata

    return {base['name']: base for base in metadata()['bases'].values()}


@cache
def _skill_ids() -> dict[tuple[str, str], int]:
    from inventory_tracking.items.metadata import metadata

    return {(row['name'], row['class']): int(skill) for skill, row in metadata()['skills'].items() if row['class']}


def _skills(pairs: Iterable[tuple[str, int]], klass: str) -> list[list[int]]:
    return [[_skill_ids()[name, klass], level] for name, level in pairs]


def facts_of(spec: Mapping[str, Any]) -> dict[str, Any]:
    """The facet's facts in game terms: base names and codes, quality grade, ethereal flag, sockets, all-res band and
    staff mods by skill id (`skills_min` all, `skills_exact` all, `skills_any_min` one of, `second`: another mod at
    least this, `others_max`: every other mod of `skill_class` at most this, `best`: the best mod exactly this)."""
    games = [NAMES.get(name, name) for name in spec['names']]
    missing = [name for name in games if name not in _bases()]
    if missing:
        raise KeyError(f'no game base named {missing} (facet {spec["id"]})')  # facet_records skips it, named
    klass = 'ass' if set(spec['names']) <= set(TALONS) else 'war'
    staff = any(part in spec for part in ('mods', 'exact', 'anymods', 'best', 'second', 'others_max'))
    return {
        'group': spec['group'],
        'label': spec['label'],
        'bases': games,
        'codes': [_bases()[name]['code'] for name in games],
        'grade': spec.get('grade', 'white'),
        'ethereal': spec.get('eth'),
        'sockets': spec.get('sockets'),
        'all_res': list(spec['res']) if spec.get('res') else None,
        'plain': bool(spec.get('plain')),
        'skill_class': klass if staff else None,
        'skills_min': _skills(spec.get('mods', ()), klass),
        'skills_exact': _skills(spec.get('exact', ()), klass),
        'skills_any_min': _skills(spec.get('anymods', ()), klass),
        'second': spec.get('second'),
        'others_max': spec.get('others_max'),
        'best': spec.get('best'),
    }


# -- the KB's bands per plain key (the allowlist builder's former triage and wp-b reads)


def _combos(base: Mapping[str, Any]) -> Iterator[tuple[str, bool, int, int]]:
    for rarity in ('normal', 'superior'):
        for ethereal in (False, True):
            for sockets in range(int(base.get('max_sockets') or 0) + 1):
                for ed in (0,) if rarity == 'normal' else (0, PERFECT_ED):
                    yield rarity, ethereal, sockets, ed


def kb_record(result: Mapping[str, Any], *, rarity: str, ethereal: bool, sockets: int) -> dict[str, Any] | None:
    """The KB asks band of a triage `result` when its bucket fits these facts exactly (sockets, ethereal flag, quality;
    no relaxed facet but the ED), None else. Pure; the sellers and price floors are the reader's."""
    band = result.get('band') or {}
    if band.get('evidence_kind') != 'asks' or band.get('median_ist') is None:
        return None
    relaxed = sorted(set(band.get('relaxed_facets') or ()))
    bucket = str(band.get('bucket') or '')
    exact = (f'"sockets":{sockets}', f'"ethereal":{"true" if ethereal else "false"}', f'"rarity":"{rarity}"')
    if set(relaxed) - {'base_ed'} or not all(part in bucket for part in exact):
        return None
    return {
        'q1_ist': round(band.get('q1_ist') or band['median_ist'], 3),
        'median_ist': round(band['median_ist'], 3),
        'n': band.get('sellers') or 0,
        'kind': 'asks',
        'observed': band.get('observed_at'),
        'relaxed': relaxed,
        'source': f'pricing/triage band {bucket}',
    }


def kb_records(tables: Any, bases: Mapping[str, Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    """Every plain key of the weapons and armor the triage prices exactly (`kb_record`): key -> record."""
    from pricing.triage.engine import assess

    found = {}
    for base in bases.values():
        if base.get('category') not in ('weapons', 'armor'):
            continue
        for rarity, ethereal, sockets, ed in _combos(base):
            result = assess(plain_item(base, rarity, ethereal, sockets, ed), tables)
            record = kb_record(result, rarity=rarity, ethereal=ethereal, sockets=sockets)
            if record is None:
                continue
            perfect = ed >= PERFECT_ED
            said = f'{rarity}{" eth" if ethereal else ""} {base["name"]} {sockets}os{" 15 ED" if perfect else ""}'
            found[key(base['code'], rarity, ethereal=ethereal, sockets=sockets, perfect=perfect)] = record | {
                'facts': said
            }
    return dict(sorted(found.items()))


def wpb_records(prices: Mapping[str, Any], bases: Mapping[str, Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    """The plain keys wp-b's plain buckets price (pricing/data/wp-b-prices.json, asks 2026-09-18, split by 15 ED), with
    WPB_LISTINGS priced listings or more, whatever their median: key -> record. Only WPB_TYPES bases (no class item,
    shield with res, circlet or gloves: their plain buckets pool affixed listings). Pure."""
    by_name = {base['name']: base for base in bases.values()}
    found: dict[str, dict[str, Any]] = {}
    for slug, entry in prices.items():
        base = by_name.get(entry.get('name')) if isinstance(entry, dict) else None
        if base is None or base.get('type') not in WPB_TYPES or 'buckets' not in entry:
            continue
        for bucket, band in entry['buckets'].items():
            matched = WPB_BUCKET.match(bucket)
            if matched is None or (band.get('n_priced') or 0) < WPB_LISTINGS or band.get('median_ist') is None:
                continue
            sockets, eth, rarity, perfect = int(matched[1]), matched[2] == 'eth', matched[3], bool(matched[4])
            if rarity == 'normal' and perfect:
                continue  # a superior labelled normal (rca/2026-10-23/base-candidates.md caveats)
            dated = sorted(str(ask.get('updated')) for ask in band.get('cheapest') or () if ask.get('updated'))
            found[key(base['code'], rarity, ethereal=eth, sockets=sockets, perfect=perfect)] = {
                'q1_ist': round(band.get('min_ist') or band['median_ist'], 3),
                'median_ist': round(band['median_ist'], 3),
                'n': band['n_priced'],
                'kind': 'asks',
                'observed': dated[-1] if dated else '2026-09-18',
                'source': f'pricing/data/wp-b-prices.json {slug} {bucket}',
                'facts': f'{rarity}{" eth" if eth else ""} {base["name"]} {sockets}os{" 15 ED" if perfect else ""}',
            }
    return found


# -- the file


def facet_records(specs: Iterable[Mapping[str, Any]]) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    """Every facet with any ask, fill or bid in scope: (id -> its game facts and its three records, id -> why a facet
    is left out: a Traderie base name the game data does not name, never guessed)."""
    specs = list(specs)
    names = {name for spec in specs for name in spec['names']}
    pulled = {'asks': asks(names), 'fills': fills(names), 'bids': bids(names)}
    found, unnamed = {}, {}
    for spec in specs:
        rows = {kind: [row for row in pulled[kind] if match(spec, row)] for kind in pulled}
        if not any(rows.values()):
            continue
        try:
            facts = facts_of(spec)
        except KeyError as error:
            unnamed[spec['id']] = str(error)
            continue
        found[spec['id']] = facts | {kind: band_record(kind, rows[kind]) for kind in ('fills', 'asks', 'bids')}
    return found, unnamed


def build(tables: Any, bases: Mapping[str, Mapping[str, Any]], prices: Mapping[str, Any]) -> dict[str, Any]:
    facets, unnamed = facet_records(FACETS)
    return {
        'built': datetime.date.today().isoformat(),
        'what': 'Plain-base price evidence per facet (pricing/knowledge/base_evidence.py); Ist = 1 by '
        'pricing/data/wp-f-ladder.json (2026-09-18). Numbers are q1/median.',
        'scope': 'Traderie softcore / non-ladder / PC / Reign of the Warlock',
        'sources': {
            'fills': f"Traderie Recent Trades (accepted + completed offers) pulled {PULLED} through the player's "
            f'browser: pricing/raw/traderie/{{{",".join(FILL_DIRS)}}}; one per offer id; since {FILLS_SINCE}',
            'asks': f'Traderie scoped sell pages pulled {PULLED}: pricing/raw/traderie/{{{",".join(ASK_DIRS)}}}; one '
            'vote per seller (their cheapest)',
            'bids': f'Traderie scoped buy pages pulled {PULLED}: pricing/raw/traderie/{{{",".join(BID_DIRS)}}}; one '
            'vote per distinct buyer (their highest)',
            'kb': 'pricing/triage bands on the offline KB (Traderie asks, 2026-09-18..10-04) fitting the facts exactly',
            'wpb': 'pricing/data/wp-b-prices.json plain buckets (asks 2026-09-18), split by 15 ED',
        },
        'pulled': PULLED,
        'fills_since': FILLS_SINCE,
        'facets': facets,
        'unnamed': unnamed,
        'kb': kb_records(tables, bases),
        'wpb': dict(sorted(wpb_records(prices, bases).items())),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.parse_args(argv)
    from inventory_tracking.items.metadata import metadata
    from pricing.triage.runtime import TABLES

    if not all((RAW / directory).is_dir() for directory in (*ASK_DIRS, *FILL_DIRS, *BID_DIRS)):
        raise SystemExit(f'the {PULLED} pulls are not under {RAW}: the evidence is built from them')
    report = build(TABLES.load(), metadata()['bases'], json.loads(WPB.read_text()))
    atomic_json(EVIDENCE_FILE, report)
    print(
        f'{len(report["facets"])} facets ({len(report["unnamed"])} unnamed), {len(report["kb"])} KB keys, '
        f'{len(report["wpb"])} wp-b keys -> {EVIDENCE_FILE}'
    )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
