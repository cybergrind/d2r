"""Link plain structured named alternatives to the exact reviewed HTML table."""

from pathlib import Path

from inventory_tracking.items.stat_constants import CLASS_NAMES
from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from pricing.knowledge.assessment.maintenance.guide_sections import section_inventory
from pricing.knowledge.assessment.maintenance.player_table_context import TableMentions, require_player_table
from pricing.knowledge.assessment.maintenance.source_matching import requires_eq
from pricing.knowledge.assessment.policies.sources import resolve_pointer
from pricing.knowledge.assessment.profile_sources import validate_profile_sources


KIND = 'structured_main_table'


def compact(text):
    return ''.join(c for c in text.casefold() if c.isalnum())


def reviewed_span(review, source, guide_path, parser, sections, read_json):
    prefix = '/sources/' + guide_path.replace('/', '~1')
    section_source = source['locator'].startswith(prefix + '/sections/')
    ref = review.get('raw_span', {}) if section_source else source
    locator = ref.get('locator', '')
    index = locator.removeprefix(prefix + '/item_spans/')
    if (
        ref.get('path') != source['path']
        or ref.get('sha256') != source['sha256']
        or not locator.startswith(prefix + '/item_spans/')
        or not index.isdecimal()
        or str(int(index)) != index
        or int(index) >= len(parser.mentions)
    ):
        raise ValueError('Structured main table lacks its exact reviewed HTML span')
    n = int(index)
    if section_source:
        section = source['locator'].removeprefix(prefix + '/sections/')
        if (
            not review.get('native_definition')
            or not section.isdecimal()
            or str(int(section)) != section
            or int(section) >= len(sections)
        ):
            raise ValueError('Structured main table lacks reviewed section identity evidence')
        containing = [i for i, s in enumerate(sections) if tuple(s['position']) < parser.positions[n]]
        if (
            not containing
            or containing[-1] != int(section)
            or sections[int(section)] != resolve_pointer(read_json(source), source['locator'])
            or parser.mentions[n]['label'] not in source.get('quotes', [])
        ):
            raise ValueError('Structured main table span is outside its quoted reviewed section')
    return n, locator


def native_identity(review, source, span, name, category, read_json):
    native_id = span.get('item_id', '')
    prefix = 'unique' if category == 'unique' else 'set'
    proof = review.get('native_definition')
    if proof is None:
        return span.get('label') == name and native_id.startswith(prefix) and native_id[len(prefix) :].isdecimal()
    fields = ('path', 'sha256', 'locator')
    table = 'uniqueitems' if category == 'unique' else 'setitems'
    if proof.get('path') != f'third-parties/d2data/json/{table}.json' or not any(
        all(p.get(k) == proof.get(k) for k in fields) for p in source.get('corroborating', [])
    ):
        raise ValueError('Structured main table native identity was not reviewed with this source')
    record = resolve_pointer(read_json(proof), proof['locator'])
    identity = record.get('*ID')

    return (
        compact(record.get('index', '')) == compact(name)
        and type(identity) is int
        and proof['locator']
        == (f'/{identity}' if category == 'unique' else '/' + record['index'].replace('~', '~0').replace('/', '~1'))
        and compact(span.get('label', '')) == compact(name)
        and (
            not native_id
            or (
                native_id.startswith(prefix)
                and native_id[len(prefix) :].isdecimal()
                and int(native_id[len(prefix) :]) == identity
            )
        )
    )


def validate_link(review, occurrence, role, uses, root, read, read_json):
    if (
        not occurrence
        or not role
        or fingerprint(occurrence) != review['occurrence_fingerprint']
        or fingerprint(role) != review['profile_fingerprint']
        or not isinstance(review.get('reason'), str)
        or not review['reason'].strip()
        or occurrence.get('kind') != 'demand'
        or occurrence.get('source_status') != 'verified'
        or occurrence.get('details', {}).get('recommended') is not True
        or occurrence.get('identity_status') != 'resolved'
        or occurrence.get('category') not in ('unique', 'set')
        or occurrence.get('variant') != 'Main alternatives'
        or occurrence.get('side') != 'player'
        or role.get('side') != 'player'
        or any(occurrence.get(k) != role.get(k) for k in ('build', 'slot'))
        or role.get('review_status') != 'reviewed_candidate_rule'
        or role.get('names') != [occurrence.get('name')]
        or role.get('qualities') != [occurrence.get('category')]
        or (
            occurrence.get('original_label') != occurrence.get('name')
            and (
                not review.get('native_definition')
                or compact(occurrence.get('original_label', '')) != compact(occurrence.get('name', ''))
            )
        )
    ):
        raise ValueError('Incompatible structured main table context')
    structured = review['structured']
    build, slot, name = occurrence['build'], occurrence['slot'], occurrence['name']
    prefix = f'/{build}/slots/{slot.replace("~", "~0").replace("/", "~1")}/'
    locator = occurrence['source_locator']
    index = locator.removeprefix(prefix)
    if (
        structured['path'] != 'pricing/data/wp-a-builds.json'
        or occurrence['source_id'] != structured['path']
        or structured.get('locator') != locator
        or not locator.startswith(prefix)
        or not index.isdecimal()
        or str(int(index)) != index
    ):
        raise ValueError('Structured main table needs an exact primary entry')
    data = read_json(structured)
    klass = data.get(build, {}).get('class')
    if (
        klass not in CLASS_NAMES
        or occurrence.get('class') != klass
        or not requires_eq(role.get('must', {}), 'context_eq', 'player_class', klass)
        or resolve_pointer(data, locator) != occurrence['original_label']
    ):
        raise ValueError('Structured main table identity or wearer differs')
    source, guide, cache = role['source'], review['guide'], review['cache']
    guide_path = f'pricing/raw/mr/guides__{build}.html'
    if (
        guide['path'] != guide_path
        or cache['path'] != 'pricing/data/appraisal-guide-sections.json'
        or source['path'] != cache['path']
        or source['sha256'] != cache['sha256']
    ):
        raise ValueError('Structured main table lacks its exact reviewed HTML source')
    validate_profile_sources({'profiles': [role]}, root, Path.read_bytes)
    html = read(guide).decode()
    parser = TableMentions()
    parser.feed(html)
    parser.close()
    sections = section_inventory(html)['sections']
    n, span_locator = reviewed_span(review, source, guide_path, parser, sections, read_json)
    require_player_table(parser, sections, n)
    span = parser.mentions[n]
    if (
        span != resolve_pointer(read_json(cache), span_locator)
        or parser.entry_labels.get(n) != span.get('label')
        or span.get('slot') != slot
        or span.get('side') != 'player'
        or span.get('profile_id')
        or not native_identity(review, source, span, name, occurrence['category'], read_json)
    ):
        raise ValueError('Structured main table has another identity, slot or decorated entry')
    endorsed = [
        u
        for u in uses
        if u['profile_id'] == role['id']
        and fingerprint(u) == review['use_fingerprint']
        and u.get('item') == name
        and u.get('review_state') == 'reviewed'
        and u.get('scope') == 'softcore'
        and u.get('strength') in ('required', 'preferred', 'alternative')
        and not u.get('historical')
        and not u.get('source_coverage')
    ]
    if len(endorsed) != 1:
        raise ValueError('Structured main table lacks an exact reviewed endorsement')
    return {
        'occurrence_id': occurrence['id'],
        'profile_id': role['id'],
        'state': 'reviewed',
        'reason': review['reason'],
        'review_date': review['review_date'],
    }
