"""Exact raw and structured source proofs for the reviewed resistance-rune armor family."""

from pathlib import Path

from inventory_tracking.items.metadata import metadata
from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from pricing.knowledge.assessment.maintenance.guide_sections import section_inventory
from pricing.knowledge.assessment.maintenance.resistance_armor_templates import MEMBERS, RUNES, expand_resistance_armor
from pricing.knowledge.assessment.maintenance.table_cells import CellMentions, require_early_armor_cell
from pricing.knowledge.assessment.policies.sources import resolve_pointer
from pricing.knowledge.assessment.profile_sources import validate_profile_sources
from pricing.knowledge.builds import decode_planner


KIND = 'merc_resistance_armor'
LABEL = 'Gemmed Dusk Shroud'
CACHE = 'pricing/data/appraisal-guide-sections.json'


def validate_link(review, occurrence, role, uses, root, read, read_json):
    member = MEMBERS.get(role.get('build')) if role else None
    if (
        not occurrence
        or not member
        or review.get('pattern_kind') != KIND
        or fingerprint(occurrence) != review.get('occurrence_fingerprint')
        or fingerprint(role) != review.get('profile_fingerprint')
        or role['id'] != role['build'] + '-merc-resistance-rune-armor'
        or role['variant'] != 'early'
        or role['side'] != 'merc'
        or role['slot'] != 'Body Armor'
        or occurrence.get('class') != member[0]
        or occurrence.get('details', {}).get('recommended') is not True
        or any(occurrence.get(k) != role[k] for k in ('build', 'side', 'slot'))
        or occurrence.get('name') != LABEL
        or occurrence.get('original_label') != LABEL
        or not isinstance(review.get('reason'), str)
        or not review['reason'].strip()
    ):
        raise ValueError('Invalid mercenary resistance armor source context')
    expected = expand_resistance_armor(
        {
            **{k: role[k] for k in ('id', 'build', 'variant', 'side', 'slot', 'source')},
            'class': member[0],
            'template': 'resistance_rune_armor',
        }
    )
    if expected != role:
        raise ValueError('Resistance armor rule differs from reviewed bearer/payload membership')
    endorsed = [u for u in uses if u['profile_id'] == role['id'] and fingerprint(u) == review.get('use_fingerprint')]
    if (
        len(endorsed) != 1
        or any(
            endorsed[0].get(k) != v
            for k, v in (
                ('pattern', role['id']),
                ('pattern_label', LABEL),
                ('scope', 'softcore'),
                ('review_state', 'reviewed'),
                ('strength', 'alternative'),
            )
        )
        or endorsed[0].get('historical')
    ):
        raise ValueError('Resistance armor lacks a current exact pattern endorsement')
    validate_profile_sources({'profiles': [role]}, root, Path.read_bytes)
    guide = f'pricing/raw/mr/guides__{role["build"]}.html'
    if review['guide']['path'] != guide or review['cache']['path'] != CACHE:
        raise ValueError('Resistance armor source pins reference another guide')
    source = role['source']
    if source['path'] != CACHE or source['sha256'] != review['cache']['sha256']:
        raise ValueError('Resistance armor role and review use different caches')
    cache = read_json(review['cache'])['sources'][guide]
    html = read(review['guide']).decode()
    if cache['source_sha256'] != review['guide']['sha256']:
        raise ValueError('Resistance armor raw/cache hash mismatch')
    parser = CellMentions()
    parser.feed(html)
    parser.close()
    sections = section_inventory(html)['sections']
    if parser.mentions != cache['item_spans'] or sections != cache['sections']:
        raise ValueError('Resistance armor source extraction differs from raw guide')
    index = review.get('span')
    if type(index) is not int or not 0 <= index < len(parser.mentions):
        raise ValueError('Resistance armor requires an exact raw span')
    require_early_armor_cell(parser, index)
    enclosing = [i for i, s in enumerate(sections) if tuple(s['position']) < parser.positions[index]]
    if not enclosing or sections[enclosing[-1]]['heading'] != 'Mercenary Gear Options':
        raise ValueError('Resistance armor is outside Mercenary Gear Options')
    section = enclosing[-1]
    locator = '/sources/' + guide.replace('/', '~1') + f'/sections/{section}'
    if source['locator'] != locator or sections[section]['text'] not in source['quotes']:
        raise ValueError('Resistance armor primary source does not bind the complete section')
    span = parser.mentions[index]
    if (
        span.get('label') != LABEL
        or parser.entry_labels[index] != LABEL
        or span.get('side') != 'merc'
        or span.get('slot') != 'Body Armor'
        or span.get('profile_id') != 'fc01065b'
        or span.get('item_id') != '93'
    ):
        raise ValueError('Resistance armor raw span references another item or payload')
    validate_native(review, role, read_json)
    if occurrence['source_id'] == guide:
        if occurrence['variant'] != 'Guide mention' or occurrence['source_locator'] != f'/item-spans/{index}':
            raise ValueError('Resistance armor raw occurrence belongs to another span')
        details = occurrence.get('details', {})
        if details.get('profile_id') != span['profile_id'] or details.get('raw_item_id') != span['item_id']:
            raise ValueError('Resistance armor occurrence lost its native witness')
    else:
        pin = review.get('structured_source', {})
        if pin.get('path') != 'pricing/data/wp-a-builds.json' or occurrence['source_id'] != pin['path']:
            raise ValueError('Resistance armor structured occurrence has no pinned source')
        prefix = f'/{role["build"]}/merc/Body Armor/early/'
        ordinal = occurrence['source_locator'].removeprefix(prefix)
        if (
            not occurrence['source_locator'].startswith(prefix)
            or not ordinal.isdecimal()
            or str(int(ordinal)) != ordinal
            or occurrence['variant'] != 'early'
        ):
            raise ValueError('Resistance armor structured entry has another context')
        document = read_json(pin)
        if (
            document[role['build']]['class'] != member[0]
            or resolve_pointer(document, occurrence['source_locator']) != LABEL
        ):
            raise ValueError('Resistance armor structured identity differs')
    return {
        'occurrence_id': occurrence['id'],
        'profile_id': role['id'],
        'state': 'reviewed',
        'reason': review['reason'],
        'review_date': review['review_date'],
    }


def validate_native(review, role, read_json):
    planner, gems = review.get('planner', {}), review.get('gems', {})
    if (
        planner.get('path') != 'pricing/raw/mr/planners/fc01065b.json'
        or gems.get('path') != 'third-parties/d2data/json/gems.json'
    ):
        raise ValueError('Resistance armor requires exact native sources')
    pins = role['source'].get('corroborating', [])
    for pin in (planner, gems):
        if not any(p['path'] == pin['path'] and p['sha256'] == pin['sha256'] for p in pins):
            raise ValueError('Resistance armor native witness differs from the role evidence')
    native = decode_planner(read_json(planner))['items']['93']
    bases = {b['name']: b['code'] for b in metadata()['bases'].values()}
    codes = [bases[n] for n in RUNES]
    if (
        native.get('base') != bases['Dusk Shroud']
        or native.get('quality') != 1
        or native.get('sockets') != 4
        or native.get('socketedItems') != codes
    ):
        raise ValueError('Resistance armor native payload changed')
    definitions = read_json(gems)
    for code, effect in zip(codes, ('res-fire', 'res-ltng', 'res-cold', 'res-pois'), strict=True):
        row = definitions[code]
        if row.get('helmMod1Code') != effect or row.get('helmMod1Min') != 30 or row.get('helmMod1Max') != 30:
            raise ValueError('Resistance armor native rune effect changed')
