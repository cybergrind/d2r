import json
from pathlib import Path

from inventory_tracking.appraisal.text import roll_styles, value_watch_lines
from pricing.knowledge.valuable import build_watchlist


def test_valuable_watchlist_combines_guide_and_rotw_build_research():
    root = Path(__file__).parents[3]
    document = build_watchlist(root)
    rows = {r['name']: r for r in document['rows']}
    assert rows["Griffon's Eye"]['details']['priority'] == 'valuable_candidate'
    assert rows["Griffon's Eye"]['details']['build_count'] > 0
    assert rows['Harlequin Crest']['details']['guide_source']['source_date'] == '2024-03-06'
    assert rows["Ars Tor'Baalos"]['details']['local_tier']
    assert all('estimate_ist' not in r for r in document['rows'])
    # Portable maintenance is reproducible; it does not fetch prices during appraisal.
    assert document == json.loads((root / 'pricing/data/appraisal-value-watch.json').read_text())


def test_valuable_candidate_is_highlighted_even_without_price():
    result = {
        'value_watch': [
            {
                'source': {'source_date': '2026-09-18'},
                'details': {'priority': 'valuable_candidate', 'build_count': 7, 'guide_tier': 'High'},
            }
        ]
    }
    lines = value_watch_lines(result)
    styles = roll_styles({'result': result})
    assert styles[lines[0]] == 'bold bright_magenta'
    assert not any('Guide priority:' in line for line in lines)


def test_sazabi_uber_merc_context_survives_into_report():
    root = Path(__file__).parents[3]
    rows = {r['name']: r for r in build_watchlist(root)['rows']}
    row = rows["Sazabi's Mental Sheath"]
    context = next(
        c
        for c in row['details']['build_contexts']
        if c['build'] == 'echoing-strike-warlock-guide' and c['variant'] == 'Ubers'
    )
    assert context['side'] == 'merc'
    assert 'Cham Rune' in context['original_label']
    text = '\n'.join(value_watch_lines({'value_watch': [row]}))
    assert 'Ubers' in text
    assert 'merc' in text
    assert 'Sazabi' in text
    assert 'Cham Rune' in text


def test_shaftstop_watch_requires_matching_softcore_ethereal_build():
    from types import SimpleNamespace

    from pricing.knowledge.assessment.policies.value_watch import matching_watches

    rows = json.loads(Path('pricing/data/appraisal-value-watch.json').read_text())['rows']
    shaft = [r for r in rows if r['name'] == 'Shaftstop']
    assert not matching_watches(shaft, SimpleNamespace(ethereal=False))
    matched = matching_watches(shaft, SimpleNamespace(ethereal=True))
    assert len(matched) == 1
    assert matched[0]['details']['priority'] == 'build_demand'
    assert all('ethereal' in c['original_label'] for c in matched[0]['details']['build_contexts'])


def test_perfect_roll_watch_prose_does_not_qualify_an_unchecked_copy():
    from types import SimpleNamespace

    from pricing.knowledge.assessment.policies.value_watch import matching_watches

    watch = {
        'kind': 'value_watch',
        'name': 'Example',
        'rarity': 'unique',
        'details': {'priority': 'valuable_candidate', 'local_conditions': 'Value in perfect rolls'},
    }
    assert not matching_watches([watch], SimpleNamespace(ethereal=False))
