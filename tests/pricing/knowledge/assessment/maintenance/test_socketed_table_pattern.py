"""A gem mention is a component only inside the complete reviewed armor entry."""

from pathlib import Path

from pricing.knowledge.assessment.maintenance.player_table_context import TableMentions


def test_entry_bounds_keep_gem_component_separate_from_the_next_table_row():
    parser = TableMentions()
    parser.feed(
        '<table><tr><td><span class="d2planner-item">Gemmed Dusk Shroud</span> '
        '(4x <span class="d2planner-item">Perfect Topaz</span>es)<br/>'
        '<span class="d2planner-item">Perfect Topaz</span></td></tr></table>'
    )
    parser.close()
    assert parser.positions[0] < parser.positions[1] < parser.entry_ends[0]
    assert parser.positions[2] > parser.entry_ends[0]


def test_repository_links_both_the_armor_and_its_topaz_component():
    import json

    from pricing.knowledge.assessment.maintenance.table_equivalence import compile_table_equivalence

    doc = json.loads(Path('pricing/knowledge/assessment/rules/table_equivalence_reviews.json').read_text())
    inv = json.loads(Path('pricing/data/appraisal-guide-inventory.json').read_text())['occurrences']
    profiles = json.loads(Path('pricing/data/appraisal-build-profiles.json').read_text())['profiles']
    uses = json.loads(Path('pricing/knowledge/assessment/rules/guide_use_reviews.json').read_text())['uses']
    rows = compile_table_equivalence(doc, inv, profiles, uses, Path.cwd())
    actual = {r['occurrence_id']: r['profile_id'] for r in rows}
    for oid in ('ee4737fc39641c54a19681b0', '8ff3e7f18db075fe8cd1b1ce'):
        assert actual.get(oid) == 'fissure-druid-perfect-topaz-general-armor'


def pattern_inputs():
    import json

    doc = json.loads(Path('pricing/knowledge/assessment/rules/table_equivalence_reviews.json').read_text())
    review = next(r for r in doc['rows'] if r['occurrence_id'] == 'ee4737fc39641c54a19681b0')
    profiles = json.loads(Path('pricing/data/appraisal-build-profiles.json').read_text())['profiles']
    role = next(p for p in profiles if p['id'] == review['profile_id'])
    # Normalize the fixture to dependency form so optional/missing mutations
    # remain meaningful after production requires the payload directly in must.
    if not role.get('depends_on'):
        payload = next(
            child
            for child in role['must']['all']
            if any(part.get('op') == 'socket_gems_equal' for part in child.get('all', []))
        )
        role['must']['all'].remove(payload)
        role['depends_on'] = [{'label': 'Verified Topaz payload', 'when': payload}]
    inv = json.loads(Path('pricing/data/appraisal-guide-inventory.json').read_text())['occurrences']
    occurrence = next(o for o in inv if o['id'] == review['occurrence_id'])
    parser = TableMentions()
    parser.feed(Path(review['guide']['path']).read_text())
    parser.close()
    return review, role, occurrence, parser


def test_pattern_rejects_changed_payload_scope_or_native_effect():
    import json
    from copy import deepcopy

    import pytest

    from pricing.knowledge.assessment.maintenance.socketed_table_pattern import validate_pattern

    inputs = pattern_inputs()
    for change in (
        'missing-gems',
        'optional-gems',
        'wrong-count',
        'wrong-base',
        'wrong-quality',
        'next-entry',
        'wrong-native-item',
        'wrong-gem-effect',
    ):
        review, role, occurrence, parser = deepcopy(inputs)
        index = 107
        if change == 'missing-gems':
            role['depends_on'] = []
        elif change == 'optional-gems':
            role['depends_on'][0]['required'] = False
        elif change in ('wrong-count', 'wrong-base'):
            field = 'sockets' if change == 'wrong-count' else 'base_code'
            next(c for c in role['must']['all'] if c.get('field') == field)['value'] = (
                3 if field == 'sockets' else 'wrong'
            )
        elif change == 'wrong-quality':
            role['qualities'] = ['magic']
        elif change == 'next-entry':
            index = 109
        elif change == 'wrong-native-item':
            parser.mentions[107]['item_id'] = '36'

        def read_json(pin, change=change):
            value = json.loads(Path(pin['path']).read_text())
            if change == 'wrong-gem-effect' and pin['path'].endswith('gems.json'):
                gem = next(v for v in value.values() if v['name'] == 'Perfect Topaz')
                gem['helmMod1Min'] = 23
            return value

        with pytest.raises(ValueError, match=r'[Ss]ocketed table pattern'):
            validate_pattern(review, role, occurrence, parser, index, read_json)


def test_pattern_rechecks_both_native_witness_hashes():
    import json
    from copy import deepcopy

    import pytest

    from pricing.knowledge.assessment.maintenance.table_equivalence import compile_table_equivalence

    doc = json.loads(Path('pricing/knowledge/assessment/rules/table_equivalence_reviews.json').read_text())
    review = next(r for r in doc['rows'] if r['occurrence_id'] == 'ee4737fc39641c54a19681b0')
    inv = json.loads(Path('pricing/data/appraisal-guide-inventory.json').read_text())['occurrences']
    profiles = json.loads(Path('pricing/data/appraisal-build-profiles.json').read_text())['profiles']
    uses = json.loads(Path('pricing/knowledge/assessment/rules/guide_use_reviews.json').read_text())['uses']
    for witness in ('planner', 'gems'):
        row = deepcopy(review)
        row[witness]['sha256'] = '0' * 64
        with pytest.raises(ValueError, match='Stale table equivalence evidence'):
            compile_table_equivalence({'schema_version': 1, 'rows': [row]}, inv, profiles, uses, Path.cwd())
