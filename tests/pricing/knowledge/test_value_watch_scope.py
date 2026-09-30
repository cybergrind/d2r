"""Known Hardcore demand cannot leak into the Softcore watch/report path."""

from copy import deepcopy

from inventory_tracking.appraisal.sections import value_watch_lines
from pricing.knowledge.assessment.policies.value_watch import matching_watches


def watch(priority='build_demand', variants=('Standard', 'Hardcore')):
    return {
        'kind': 'value_watch',
        'name': "Ars Dul'Mephistos",
        'rarity': 'unique',
        'details': {
            'priority': priority,
            'builds': ['abyss-warlock-build-guide'],
            'build_count': 1,
            'build_contexts': [
                {
                    'build': 'abyss-warlock-build-guide',
                    'variant': variant,
                    'side': 'player',
                    'slot': 'Off-Hand',
                    'original_label': "Ars Dul'Mephistos",
                }
                for variant in variants
            ],
        },
    }


def test_runtime_watch_keeps_softcore_context_without_mutating_source_evidence():
    row = watch()
    original = deepcopy(row)
    actual = matching_watches([row], None)
    assert [c['variant'] for c in actual[0]['details']['build_contexts']] == ['Standard']
    assert actual[0]['details']['build_count'] == 1
    assert row == original


def test_hardcore_only_demand_is_not_a_softcore_watch_or_report_heading():
    row = watch(variants=('Hardcore',))
    assert matching_watches([row], None) == []
    assert value_watch_lines({'value_watch': [row]}) == []


def test_independent_valuable_rank_survives_without_hardcore_build_claim():
    row = watch('valuable_candidate', variants=('Hardcore',))
    actual = matching_watches([row], None)
    assert len(actual) == 1
    assert actual[0]['details']['builds'] == []
    assert actual[0]['details']['build_count'] == 0
    assert actual[0]['details']['build_contexts'] == []
    assert value_watch_lines({'value_watch': [row]}) == ['VALUABLE CANDIDATE']


def test_archived_report_filters_context_before_its_three_entry_limit():
    row = watch(variants=('Hardcore', 'Hardcore budget', 'HARDCORE alternative', 'Standard'))
    lines = value_watch_lines({'value_watch': [row]})
    assert any('Standard' in line for line in lines)
    assert not any('hardcore' in line.lower() for line in lines)


def test_unqualified_guide_demand_is_preserved_when_not_known_to_be_hardcore():
    row = watch(variants=())
    assert matching_watches([row], None) == [row]
    assert value_watch_lines({'value_watch': [row]}) == ['BUILD DEMAND']


def test_published_grimoire_keeps_softcore_uses_without_hardcore_advice():
    from inventory_tracking.appraisal.text import format_appraisal
    from pricing.knowledge.publication import current_generation
    from pricing.knowledge.published_runtime import retrieve_published
    from tests.pricing.knowledge.assessment.item_bank.cases import CASES

    case = next(case for case in CASES if case.id == 'abyss/grimoires/mephistos/minimum')
    result = retrieve_published(
        case.item.capture(), current_generation('pricing/data/generations'), loadout=case.context
    )
    text = format_appraisal({'state': 'complete', 'request_id': 'grimoire-scope', 'result': result})
    assert 'VALUABLE CANDIDATE' in text
    assert 'Standard' in text
    assert 'Hardcore' not in text
    for row in result['value_watch']:
        assert all(
            not context['variant'].lower().startswith('hardcore') for context in row['details']['build_contexts']
        )


def test_explicit_hardcore_socket_labels_do_not_become_softcore_prose_demand():
    for label in (
        'Stormshield with an Eld Rune (Hardcore)',
        'Crown of Ages with 2x Ber Rune (Hardcore; table has facet/Ber versions)',
        'Stormshield with Ist Rune (Hardcore section; table has no Ist note)',
    ):
        row = watch(variants=('Prose alternatives',))
        row['details']['build_contexts'][0]['original_label'] = label
        original = deepcopy(row)
        assert matching_watches([row], None) == []
        assert value_watch_lines({'value_watch': [row]}) == []
        assert row == original


def test_softcore_and_mixed_mode_socket_prose_survives():
    for label in (
        'Stormshield with Ber Rune (Softcore)',
        'Stormshield (Hardcore or Softcore)',
        'Stormshield (not limited to Hardcore)',
    ):
        row = watch(variants=('Prose alternatives',))
        row['details']['build_contexts'][0]['original_label'] = label
        assert matching_watches([row], None) == [row]
