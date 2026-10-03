"""Exact table columns may support reviewed ordinary mercenary-use exclusions."""

import hashlib
import json
from copy import deepcopy

import pytest

from pricing.knowledge.assessment.maintenance.guide_sections import section_inventory
from pricing.knowledge.assessment.maintenance.value_scope import profile_fingerprint, use_exclusions


HTML = """<h2>Mercenary Gear Options</h2><table>
<tr><td>Slot</td><td>Early-Game</td><td>Mid-Game</td><td>End-Game</td></tr>
<tr><td>Body Armor</td><td><span class="d2planner-item">Smoke</span></td>
<td><span class="d2planner-item">Smoke</span></td><td>Fortitude</td></tr>
<tr><td>Helmet</td><td><span class="d2planner-item">Smoke</span></td><td></td><td></td></tr>
</table><h2>Other section</h2>Smoke"""


def fixture(tmp_path, html=HTML):
    guide = 'pricing/raw/mr/guides__sample.html'
    source = 'pricing/data/appraisal-guide-sections.json'
    path = tmp_path / guide
    path.parent.mkdir(parents=True)
    path.write_text(html)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    document = {'sources': {guide: section_inventory(html)}}
    data = tmp_path / source
    data.parent.mkdir(parents=True)
    data.write_text(json.dumps(document))
    profile = {
        'id': 'sample-smoke',
        'build': 'sample',
        'side': 'merc',
        'slot': 'Body Armor',
        'variant': 'Gear alternatives',
        'names': ['Smoke'],
        'qualities': ['normal', 'superior'],
        'source': {
            'path': source,
            'sha256': hashlib.sha256(data.read_bytes()).hexdigest(),
            'locator': '/sources/pricing~1raw~1mr~1guides__sample.html/sections/1',
            'quotes': ['Smoke'],
        },
    }
    row = {
        'profile_id': profile['id'],
        'profile_sha256': profile_fingerprint(profile),
        'classification': 'generic_leveling',
        'reviewed_at': '2026-10-03',
        'reason': 'Reviewed this exact general early mercenary progression alternative.',
        'source': deepcopy(profile['source']),
        'quote': 'Smoke',
        'table_context': {
            'path': guide,
            'sha256': digest,
            'section_locator': '/sections/1',
            'table_index': 0,
            'row_index': 1,
            'column_index': 1,
        },
    }
    review = {'schema_version': 1, 'scope': 'non_ladder_value_and_exceptional_leveling', 'uses': [row]}
    return profile, review


def test_valid_label_only_early_table_use_preserves_other_wearer(tmp_path):
    profile, review = fixture(tmp_path)
    player = {**profile, 'id': 'valuable-player-use', 'side': 'player'}
    assert set(use_exclusions([profile, player], review, tmp_path)) == {
        'use:sample-smoke:normal',
        'use:sample-smoke:superior',
    }


@pytest.mark.parametrize(
    'mutation',
    [
        'wearer',
        'slot',
        'section',
        'column',
        'row',
        'table',
        'stale',
        'wrong-guide',
        'wrong-quote',
        'classification',
        'date',
        'boolean-index',
    ],
)
def test_invalid_context_cannot_exclude_a_use(tmp_path, mutation):
    profile, review = fixture(tmp_path)
    row = review['uses'][0]
    context = row['table_context']
    if mutation == 'wearer':
        profile['side'] = 'player'
    elif mutation == 'slot':
        profile['slot'] = 'Helmet'
    elif mutation == 'section':
        context['section_locator'] = '/sections/2'
    elif mutation == 'column':
        context['column_index'] = 2
    elif mutation == 'row':
        context['row_index'] = 2
    elif mutation == 'table':
        context['table_index'] = 1
    elif mutation == 'stale':
        (tmp_path / context['path']).write_text(HTML.replace('Early-Game', 'End-Game'))
    elif mutation == 'wrong-guide':
        profile['build'] = 'another'
    elif mutation == 'wrong-quote':
        profile['names'] = ['Lionheart']
    elif mutation == 'classification':
        row['classification'] = 'ladder_only'
    elif mutation == 'date':
        row['reviewed_at'] = 'not-a-date'
    elif mutation == 'boolean-index':
        context['column_index'] = True
    row['profile_sha256'] = profile_fingerprint(profile)
    with pytest.raises(ValueError, match=r'mercenary|Table|Item|Ladder'):
        use_exclusions([profile], review, tmp_path)


@pytest.mark.parametrize(
    'html',
    [
        HTML.replace('<td>Body Armor</td>', '<td colspan="2">Body Armor</td>'),
        HTML.replace('<td>Body Armor</td>', '<td><table><tr><td>Body Armor</td></tr></table></td>'),
        HTML.replace('Mercenary Gear Options', 'Gear Options'),
        HTML.replace('Early-Game', 'End-Game'),
    ],
)
def test_rehashed_incompatible_tables_still_fail(tmp_path, html):
    profile, review = fixture(tmp_path)
    row = review['uses'][0]
    context = row['table_context']
    path = tmp_path / context['path']
    path.write_text(html)
    context['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
    source = tmp_path / profile['source']['path']
    source.write_text(json.dumps({'sources': {context['path']: section_inventory(html)}}))
    profile['source']['sha256'] = hashlib.sha256(source.read_bytes()).hexdigest()
    row['source'] = deepcopy(profile['source'])
    row['profile_sha256'] = profile_fingerprint(profile)
    with pytest.raises(ValueError, match=r'mercenary|Table|Item|Ladder'):
        use_exclusions([profile], review, tmp_path)


@pytest.mark.parametrize('header', ['Slot', 'Gear Level'])
def test_header_alias_and_unrelated_spanned_table_do_not_change_selected_cell(tmp_path, header):
    html = HTML.replace('<td>Slot</td>', f'<td>{header}</td>')
    html += '<table><tr><td colspan="2">Unrelated</td></tr></table>'
    profile, review = fixture(tmp_path, html)
    assert len(use_exclusions([profile], review, tmp_path)) == 2


def test_removing_context_cannot_downgrade_a_table_review_to_an_item_label(tmp_path):
    profile, review = fixture(tmp_path)
    review['uses'][0].pop('table_context')
    with pytest.raises(ValueError, match='Table'):
        use_exclusions([profile], review, tmp_path)
