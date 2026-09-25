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
