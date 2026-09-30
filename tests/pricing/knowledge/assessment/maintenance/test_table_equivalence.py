"""Independent table snapshots may share a rule only under an exact reviewed link."""

import hashlib
import json
from copy import deepcopy

import pytest

from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from pricing.knowledge.assessment.maintenance.guide_sections import section_inventory


def inputs(tmp_path, name='Skullder', label=None, slot='Body Armors', native_id='unique217', suffix=''):
    label = label or name
    build = 'example-build'
    guide = 'pricing/raw/mr/guides__example-build.html'
    html = (
        f'<h2>Gear Options</h2><table><tr><td>{slot}</td><td>'
        f'<span class="d2-planner-tooltip" data-d2-id="{native_id}">{label}</span>{suffix}</td></tr></table>'
    )

    def save(path, value):
        raw = value.encode() if isinstance(value, str) else json.dumps(value).encode()
        p = tmp_path / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(raw)
        return {'path': path, 'sha256': hashlib.sha256(raw).hexdigest()}

    raw_pin = save(guide, html)
    guide_data = section_inventory(html)
    # The production guide cache stores item spans separately from section text.
    from pricing.knowledge.assessment.maintenance.guide_positions import PositionedMentions

    parser = PositionedMentions()
    parser.feed(html)
    parser.close()
    guide_data['item_spans'] = parser.mentions
    cache = save('pricing/data/appraisal-guide-sections.json', {'sources': {guide: guide_data}})
    wp = save('pricing/data/wp-a-builds.json', {build: {'class': 'Warlock', 'slots': {slot: [label + suffix]}}})
    source = {**wp, 'locator': f'/example-build/slots/{slot}/0'}
    role = {
        'id': 'armor',
        'names': [name],
        'build': build,
        'side': 'player',
        'slot': slot,
        'variant': 'Main alternatives',
        'review_status': 'reviewed_candidate_rule',
        'must': {'op': 'context_eq', 'field': 'player_class', 'value': 'Warlock'},
        'source': source,
    }
    use = {
        'profile_id': 'armor',
        'item': name,
        **{k: role[k] for k in ('build', 'side', 'variant', 'source')},
        'profile_fingerprint': fingerprint(role),
        'review_state': 'reviewed',
        'scope': 'softcore',
        'strength': 'alternative',
    }
    occurrence = {
        'id': 'o',
        'source_id': guide,
        'source_locator': '/item-spans/0',
        'build': build,
        'class': 'Warlock',
        'side': 'player',
        'slot': slot,
        'name': name,
        'original_label': label,
        'identity_status': 'resolved',
        'variant': 'Guide mention',
    }
    row = {
        'occurrence_id': 'o',
        'occurrence_fingerprint': fingerprint(occurrence),
        'guide': raw_pin,
        'cache': cache,
        'profile_id': 'armor',
        'profile_fingerprint': fingerprint(role),
        'use_fingerprint': fingerprint(use),
        'review_date': '2026-09-28',
        'reason': 'Same standalone armor alternative in both tables.',
    }
    return {'schema_version': 1, 'rows': [row]}, [occurrence], [role], [use]


def test_equivalent_named_table_entry_reuses_existing_rule(tmp_path):
    from pricing.knowledge.assessment.maintenance.table_equivalence import compile_table_equivalence

    result = compile_table_equivalence(*inputs(tmp_path), tmp_path)
    assert result[0]['occurrence_id'] == 'o'
    assert result[0]['profile_id'] == 'armor'


@pytest.mark.parametrize('change', ['name', 'side', 'slot', 'build', 'variant', 'fingerprint', 'source', 'duplicate'])
def test_table_link_rejects_incompatible_context_even_with_new_fingerprints(tmp_path, change):
    from pricing.knowledge.assessment.maintenance.table_equivalence import compile_table_equivalence

    doc, occ, roles, uses = inputs(tmp_path)
    if change == 'name':
        roles[0]['names'] = ['Other']
        uses[0]['item'] = 'Other'
    elif change in ('side', 'slot', 'build', 'variant'):
        roles[0][change] = 'other'
        uses[0][change] = 'other'
    elif change == 'fingerprint':
        doc['rows'][0]['occurrence_fingerprint'] = 'stale'
    elif change == 'source':
        roles[0]['source']['locator'] = '/example-build/slots/Body Armors/1'
    else:
        doc['rows'].append(deepcopy(doc['rows'][0]))
    uses[0]['profile_fingerprint'] = fingerprint(roles[0])
    doc['rows'][0]['profile_fingerprint'] = fingerprint(roles[0])
    doc['rows'][0]['use_fingerprint'] = fingerprint(uses[0])
    with pytest.raises(ValueError, match=r'[Tt]able'):
        compile_table_equivalence(doc, occ, roles, uses, tmp_path)


@pytest.mark.parametrize('source', ['guide', 'cache'])
def test_table_equivalence_rejects_changed_source(tmp_path, source):
    from pricing.knowledge.assessment.maintenance.table_equivalence import compile_table_equivalence

    doc, occurrences, roles, uses = inputs(tmp_path)
    path = tmp_path / doc['rows'][0][source]['path']
    path.write_text(path.read_text() + ' ')
    with pytest.raises(ValueError, match='Stale table'):
        compile_table_equivalence(doc, occurrences, roles, uses, tmp_path)


def test_table_review_changes_completion_scope(tmp_path):
    from pricing.knowledge.assessment.maintenance.completion import scope_fingerprint

    document, _, _, _ = inputs(tmp_path)
    before = scope_fingerprint({}, {}, {}, [], [], table_reviews=document)
    document['rows'][0]['reason'] += ' Changed review.'
    assert scope_fingerprint({}, {}, {}, [], [], table_reviews=document) != before


def test_table_link_rejects_changed_corroborating_planner(tmp_path):
    from pricing.knowledge.assessment.maintenance.table_equivalence import compile_table_equivalence

    doc, occurrences, roles, uses = inputs(tmp_path)
    planner = tmp_path / 'planner.json'
    planner.write_text('{"identity": "original"}')
    doc['rows'][0]['corroborating'] = [
        {'path': 'planner.json', 'sha256': hashlib.sha256(planner.read_bytes()).hexdigest()}
    ]
    assert compile_table_equivalence(doc, occurrences, roles, uses, tmp_path)[0]['state'] == 'reviewed'
    planner.write_text('{"identity": "crafted"}')
    with pytest.raises(ValueError, match='Stale table'):
        compile_table_equivalence(doc, occurrences, roles, uses, tmp_path)


@pytest.mark.parametrize('change', ['mercenary-subheading', 'other-section', 'outside-table', 'forged-section-cache'])
def test_table_equivalence_requires_an_actual_player_gear_table(tmp_path, change):
    from pricing.knowledge.assessment.maintenance.guide_positions import PositionedMentions
    from pricing.knowledge.assessment.maintenance.table_equivalence import compile_table_equivalence

    doc, occurrences, roles, uses = inputs(tmp_path)
    row = doc['rows'][0]
    guide_path = tmp_path / row['guide']['path']
    html = guide_path.read_text()
    if change == 'mercenary-subheading':
        # The legacy item extractor sees h2/h3, so this h4 leaves side='player'.
        html = html.replace('<table>', '<h4>Mercenary Gear Options</h4><table>')
    elif change == 'other-section':
        html = html.replace('Gear Options', 'Other Recommendations')
    elif change == 'outside-table':
        html = html.replace('<table>', '').replace('</table>', '')
    guide_path.write_text(html)
    row['guide']['sha256'] = hashlib.sha256(guide_path.read_bytes()).hexdigest()
    cache = section_inventory(html)
    parser = PositionedMentions()
    parser.feed(html)
    parser.close()
    cache['item_spans'] = parser.mentions
    if change == 'forged-section-cache':
        cache['sections'][1]['heading'] = 'Different section'
    cache_path = tmp_path / row['cache']['path']
    cache_path.write_text(json.dumps({'sources': {row['guide']['path']: cache}}))
    row['cache']['sha256'] = hashlib.sha256(cache_path.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match=r'[Tt]able'):
        compile_table_equivalence(doc, occurrences, roles, uses, tmp_path)


@pytest.mark.parametrize(
    ('name', 'native_id'),
    [
        ('Gimmershred', 'unique335'),
        ('Warshrike', 'unique292'),
        ('Lacerator', 'unique321'),
        ("Demon's Arch", 'unique340'),
    ],
)
def test_ethereal_table_entry_requires_matching_qualification_and_rule(tmp_path, name, native_id):
    from pricing.knowledge.assessment.maintenance.table_equivalence import compile_table_equivalence

    label = 'Ethereal ' + name
    doc, occurrences, roles, uses = inputs(tmp_path, name, label, 'Weapon', native_id)
    roles[0]['must'] = {'all': [roles[0]['must'], {'op': 'fact_eq', 'field': 'ethereal', 'value': True}]}
    uses[0]['profile_fingerprint'] = fingerprint(roles[0])
    row = doc['rows'][0]
    row.update(
        qualified_label=label,
        profile_fingerprint=fingerprint(roles[0]),
        use_fingerprint=fingerprint(uses[0]),
    )
    assert compile_table_equivalence(doc, occurrences, roles, uses, tmp_path)[0]['state'] == 'reviewed'
    for mutation in ('plain-rule', 'wrong-qualified-label', 'missing-qualified-label', 'forged-occurrence-label'):
        d, o, r, u = deepcopy((doc, occurrences, roles, uses))
        if mutation == 'plain-rule':
            r[0]['must'] = r[0]['must']['all'][0]
        elif mutation == 'wrong-qualified-label':
            d['rows'][0]['qualified_label'] = 'Ethereal Other Weapon'
        elif mutation == 'missing-qualified-label':
            del d['rows'][0]['qualified_label']
        else:
            o[0]['original_label'] = 'Ethereal Other Weapon'
        u[0]['profile_fingerprint'] = fingerprint(r[0])
        d['rows'][0].update(
            profile_fingerprint=fingerprint(r[0]),
            use_fingerprint=fingerprint(u[0]),
            occurrence_fingerprint=fingerprint(o[0]),
        )
        with pytest.raises(ValueError, match=r'[Tt]able'):
            compile_table_equivalence(d, o, r, u, tmp_path)


def test_ethereal_deathbit_upgrade_outside_item_span_requires_both_facts(tmp_path):
    from pricing.knowledge.assessment.maintenance.table_equivalence import compile_table_equivalence
    from tests.pricing.knowledge.assessment.test_family_contracts import facts

    doc, occurrences, roles, uses = inputs(
        tmp_path, 'Deathbit', 'Ethereal Deathbit', 'Weapon', 'unique291', ' (Upgraded)'
    )
    ethereal = {'op': 'fact_eq', 'field': 'ethereal', 'value': True}
    upgraded = {'op': 'fact_eq', 'field': 'base_code', 'value': facts('Flying Knife').base_code}
    base_class = roles[0]['must']
    for predicates, valid in (([ethereal, upgraded], True), ([ethereal], False), ([upgraded], False)):
        roles[0]['must'] = {'all': [base_class, *predicates]}
        uses[0]['profile_fingerprint'] = fingerprint(roles[0])
        doc['rows'][0].update(
            qualified_label='Ethereal Deathbit (Upgraded)',
            profile_fingerprint=fingerprint(roles[0]),
            use_fingerprint=fingerprint(uses[0]),
        )
        if valid:
            assert compile_table_equivalence(doc, occurrences, roles, uses, tmp_path)[0]['state'] == 'reviewed'
        else:
            with pytest.raises(ValueError, match=r'[Tt]able'):
                compile_table_equivalence(doc, occurrences, roles, uses, tmp_path)
