"""Reverse table links prove both source contexts, not just a matching name."""

import hashlib
import json
from copy import deepcopy

import pytest

from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from pricing.knowledge.assessment.maintenance.table_equivalence import compile_table_equivalence
from tests.pricing.knowledge.assessment.maintenance.test_table_equivalence import inputs


def reverse_inputs(tmp_path, **kwargs):
    doc, occurrences, roles, uses = inputs(tmp_path, **kwargs)
    row, occurrence, role, use = doc['rows'][0], occurrences[0], roles[0], uses[0]
    structured = deepcopy(role['source'])
    raw_source = occurrence['source_id']
    role.update(variant='Gear Options', qualities=['unique'])
    role['source'] = {**row['cache'], 'locator': '/sources/' + raw_source.replace('/', '~1') + '/item_spans/0'}
    occurrence.update(
        source_id=structured['path'],
        source_locator=structured['locator'],
        variant='Main alternatives',
        category='unique',
        kind='demand',
        source_status='verified',
        details={'recommended': True},
    )
    use.update(variant=role['variant'], source=role['source'], profile_fingerprint=fingerprint(role))
    row.update(
        pattern_kind='structured_main_table',
        structured=structured,
        occurrence_fingerprint=fingerprint(occurrence),
        profile_fingerprint=fingerprint(role),
        use_fingerprint=fingerprint(use),
    )
    return doc, occurrences, roles, uses


def test_exact_structured_main_table_reuses_reviewed_html_rule(tmp_path):
    result = compile_table_equivalence(*reverse_inputs(tmp_path), tmp_path)
    assert result[0]['occurrence_id'] == 'o'
    assert result[0]['profile_id'] == 'armor'
    assert result[0]['state'] == 'reviewed'


@pytest.mark.parametrize(
    'change', ['class', 'slot', 'side', 'variant', 'label', 'source', 'recommendation', 'historical', 'quality']
)
def test_changed_context_cannot_be_approved_by_rehashing(tmp_path, change):
    doc, occurrences, roles, uses = reverse_inputs(tmp_path)
    o, r, u = occurrences[0], roles[0], uses[0]
    if change in ('class', 'slot', 'side', 'variant'):
        o[change] = 'other'
    elif change == 'label':
        o['original_label'] += ' (socketed)'
    elif change == 'source':
        o['source_locator'] = '/example-build/slots/Body Armors/1'
    elif change == 'recommendation':
        o['details']['recommended'] = False
    elif change == 'historical':
        u['historical'] = True
    else:
        r['qualities'] = ['rare']
    u['profile_fingerprint'] = fingerprint(r)
    doc['rows'][0].update(
        occurrence_fingerprint=fingerprint(o), profile_fingerprint=fingerprint(r), use_fingerprint=fingerprint(u)
    )
    with pytest.raises(ValueError, match=r'Structured|structured'):
        compile_table_equivalence(doc, occurrences, roles, uses, tmp_path)


@pytest.mark.parametrize('suffix', [' (Um)', ' (ethereal)', ' with 3 sockets'])
def test_decorated_html_entry_is_not_a_plain_named_alternative(tmp_path, suffix):
    with pytest.raises(ValueError, match=r'Structured|structured'):
        compile_table_equivalence(*reverse_inputs(tmp_path, suffix=suffix), tmp_path)


@pytest.mark.parametrize('source', ['guide', 'cache', 'structured'])
def test_stale_source_cannot_close_occurrence(tmp_path, source):
    args = reverse_inputs(tmp_path)
    path = tmp_path / args[0]['rows'][0][source]['path']
    path.write_text(path.read_text() + ' ')
    with pytest.raises(ValueError, match='Source changed; review required' if source == 'cache' else 'Stale table'):
        compile_table_equivalence(*args, tmp_path)


@pytest.mark.parametrize('native_id', ['', '123', 'set123'])
def test_missing_or_incompatible_native_identity_stays_pending(tmp_path, native_id):
    with pytest.raises(ValueError, match='Structured main table'):
        compile_table_equivalence(*reverse_inputs(tmp_path, native_id=native_id), tmp_path)


def alias_inputs(tmp_path, name='Skullder', label='skullder', native_name=None):
    doc, occurrences, roles, uses = reverse_inputs(tmp_path, name=name, label=label, native_id='')
    row, o, r, u = doc['rows'][0], occurrences[0], roles[0], uses[0]
    wp = tmp_path / row['structured']['path']
    data = json.loads(wp.read_text())
    data['example-build']['slots']['Body Armors'][0] = name
    wp.write_text(json.dumps(data))
    row['structured']['sha256'] = hashlib.sha256(wp.read_bytes()).hexdigest()
    o['original_label'] = name
    row['raw_span'] = deepcopy(r['source'])
    r['source']['locator'] = r['source']['locator'].replace('/item_spans/0', '/sections/1')
    r['source']['quotes'] = [label]
    native = tmp_path / 'third-parties/d2data/json/uniqueitems.json'
    native.parent.mkdir(parents=True)
    native.write_text(json.dumps({'217': {'index': native_name or name, '*ID': 217}}))
    pin = {
        'path': str(native.relative_to(tmp_path)),
        'locator': '/217',
        'sha256': hashlib.sha256(native.read_bytes()).hexdigest(),
    }
    r['source']['corroborating'] = [pin]
    row['native_definition'] = pin
    u.update(source=r['source'], profile_fingerprint=fingerprint(r))
    row.update(
        occurrence_fingerprint=fingerprint(o), profile_fingerprint=fingerprint(r), use_fingerprint=fingerprint(u)
    )
    return doc, occurrences, roles, uses


def test_compact_table_label_requires_exact_reviewed_native_definition(tmp_path):
    assert compile_table_equivalence(*alias_inputs(tmp_path), tmp_path)[0]['state'] == 'reviewed'


def test_native_spacing_can_match_canonical_display_name(tmp_path):
    args = alias_inputs(tmp_path, name='War Traveler', label='wartraveler', native_name='Wartraveler')
    assert compile_table_equivalence(*args, tmp_path)[0]['state'] == 'reviewed'


def test_structured_entry_can_repeat_the_reviewed_compact_alias(tmp_path):
    doc, occ, roles, uses = alias_inputs(tmp_path)
    row = doc['rows'][0]
    p = tmp_path / row['structured']['path']
    data = json.loads(p.read_text())
    data['example-build']['slots']['Body Armors'][0] = 'skullder'
    p.write_text(json.dumps(data))
    row['structured']['sha256'] = hashlib.sha256(p.read_bytes()).hexdigest()
    occ[0]['original_label'] = 'skullder'
    row['occurrence_fingerprint'] = fingerprint(occ[0])
    assert compile_table_equivalence(doc, occ, roles, uses, tmp_path)[0]['state'] == 'reviewed'


@pytest.mark.parametrize(
    'change', ['missing-native', 'wrong-native', 'unreviewed-native', 'wrong-section', 'wrong-span', 'missing-quote']
)
def test_alias_evidence_cannot_be_invented_by_rehashing(tmp_path, change):
    doc, occ, roles, uses = alias_inputs(tmp_path)
    row, role, use = doc['rows'][0], roles[0], uses[0]
    if change == 'missing-native':
        del row['native_definition']
    elif change == 'wrong-native':
        p = tmp_path / row['native_definition']['path']
        p.write_text(json.dumps({'217': {'index': 'Different Item', '*ID': 217}}))
        row['native_definition']['sha256'] = hashlib.sha256(p.read_bytes()).hexdigest()
    elif change == 'unreviewed-native':
        role['source']['corroborating'] = []
    elif change == 'wrong-section':
        role['source']['locator'] = role['source']['locator'].replace('/sections/1', '/sections/0')
    elif change == 'wrong-span':
        row['raw_span']['locator'] = row['raw_span']['locator'].replace('/item_spans/0', '/item_spans/1')
    else:
        role['source']['quotes'] = []
    use['profile_fingerprint'] = fingerprint(role)
    row.update(profile_fingerprint=fingerprint(role), use_fingerprint=fingerprint(use))
    with pytest.raises(ValueError, match=r'Structured|structured|Source'):
        compile_table_equivalence(doc, occ, roles, uses, tmp_path)


def test_native_set_table_uses_the_item_name_as_key(tmp_path):
    doc, occ, roles, uses = alias_inputs(tmp_path, name="Natalya's Soul", label='natalyassoul')
    row, role, use = doc['rows'][0], roles[0], uses[0]
    occ[0]['category'] = 'set'
    role['qualities'] = ['set']
    native = tmp_path / 'third-parties/d2data/json/setitems.json'
    native.write_text(json.dumps({"Natalya's Soul": {'index': "Natalya's Soul", '*ID': 65}}))
    row['native_definition'].update(
        path=str(native.relative_to(tmp_path)),
        locator="/Natalya's Soul",
        sha256=hashlib.sha256(native.read_bytes()).hexdigest(),
    )
    use['profile_fingerprint'] = fingerprint(role)
    row.update(
        occurrence_fingerprint=fingerprint(occ[0]),
        profile_fingerprint=fingerprint(role),
        use_fingerprint=fingerprint(use),
    )
    assert compile_table_equivalence(doc, occ, roles, uses, tmp_path)[0]['state'] == 'reviewed'


@pytest.mark.parametrize('suffix', [' (Um)', ' ethereal', ' with 3 sockets'])
def test_native_proof_does_not_erase_structured_conditions(tmp_path, suffix):
    doc, occ, roles, uses = alias_inputs(tmp_path)
    row = doc['rows'][0]
    label = 'skullder' + suffix
    p = tmp_path / row['structured']['path']
    data = json.loads(p.read_text())
    data['example-build']['slots']['Body Armors'][0] = label
    p.write_text(json.dumps(data))
    row['structured']['sha256'] = hashlib.sha256(p.read_bytes()).hexdigest()
    occ[0]['original_label'] = label
    row['occurrence_fingerprint'] = fingerprint(occ[0])
    with pytest.raises(ValueError, match='Incompatible structured main table context'):
        compile_table_equivalence(doc, occ, roles, uses, tmp_path)
