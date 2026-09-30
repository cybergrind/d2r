"""Table qualifiers must survive HTML markup and remain mandatory role dependencies."""

import pytest

from pricing.knowledge.assessment.maintenance.player_table_context import TableMentions


def test_complete_table_label_keeps_nested_rune_and_stops_at_next_item():
    parser = TableMentions()
    parser.feed(
        '<table><tr><td>Weapons</td><td><span class="d2planner-item">Rune Master</span> '
        '(5x <span class="d2planner-item">Ist Rune</span><span>s</span>)<br/>'
        '<span class="d2planner-item">Other</span></td></tr></table>'
    )
    parser.close()
    assert parser.entry_labels[0] == 'Rune Master (5x Ist Rune s )'
    assert 'Other' not in parser.entry_labels[0]


@pytest.mark.parametrize('change', ['none', 'missing-dependency', 'wrong-rune', 'wrong-label'])
def test_qualified_stormlash_requires_full_label_and_shael_dependency(change):
    from pricing.knowledge.assessment.maintenance.qualified_table_context import require_qualification

    condition = {
        'all': [
            {'op': 'fact_eq', 'field': 'sockets', 'value': 1},
            {'op': 'socket_runes_equal', 'value': ['Shael Rune']},
        ]
    }
    role = {'names': ['Stormlash'], 'depends_on': [{'when': condition}]}
    label = 'Stormlash ( Shael Rune )'
    if change == 'missing-dependency':
        role['depends_on'] = []
    elif change == 'wrong-rune':
        condition['all'][1]['value'] = ['Ist Rune']
    elif change == 'wrong-label':
        label = 'Stormlash ( Ist Rune )'
    if change == 'none':
        require_qualification(role, label)
    else:
        with pytest.raises(ValueError, match='qualification'):
            require_qualification(role, label)


def test_qualified_links_validate_against_pinned_html_and_required_dependencies():
    import json
    from pathlib import Path

    from pricing.knowledge.assessment.maintenance.table_equivalence import compile_table_equivalence
    from tests.pricing.knowledge.assessment.item_bank.cases.qualified_tables import SPECS

    doc = json.loads(Path('pricing/knowledge/assessment/rules/table_equivalence_reviews.json').read_text())
    inventory = json.loads(Path('pricing/data/appraisal-guide-inventory.json').read_text())['occurrences']
    profiles = json.loads(Path('pricing/data/appraisal-build-profiles.json').read_text())['profiles']
    uses = json.loads(Path('pricing/knowledge/assessment/rules/guide_use_reviews.json').read_text())['uses']
    linked = compile_table_equivalence(doc, inventory, profiles, uses, Path.cwd())
    by_occurrence = {o['id']: o for o in inventory}
    qualified = {r['occurrence_id'] for r in doc['rows'] if r.get('qualified_label')}
    actual = {
        (by_occurrence[r['occurrence_id']]['build'], by_occurrence[r['occurrence_id']]['name'])
        for r in linked
        if r['occurrence_id'] in qualified
    }
    assert actual == {(build, name) for build, _, name, *_ in SPECS} | {
        ('double-throw-barbarian-guide', name)
        for name in (
            'Deathbit',
            'The Scalper',
            'Lacerator',
            'Warshrike',
            'Gimmershred',
            "Demon's Arch",
            "Gargoyle's Bite",
        )
    }
    assert len(qualified) == 30


@pytest.mark.parametrize('upgraded', [True, False])
def test_deathbit_qualification_requires_upgraded_base(upgraded):
    from inventory_tracking.items.metadata import metadata
    from pricing.knowledge.assessment.maintenance.qualified_table_context import require_qualification

    base = 'Flying Knife' if upgraded else 'Battle Dart'
    code = next(row['code'] for row in metadata()['bases'].values() if row['name'] == base)
    role = {'names': ['Deathbit'], 'must': {'op': 'fact_eq', 'field': 'base_code', 'value': code}}
    if upgraded:
        require_qualification(role, 'Deathbit (Upgraded)')
    else:
        with pytest.raises(ValueError, match='qualification'):
            require_qualification(role, 'Deathbit (Upgraded)')
