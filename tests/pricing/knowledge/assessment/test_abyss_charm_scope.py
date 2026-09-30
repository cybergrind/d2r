"""Softcore charm contributions must not inherit the guide's Hardcore priorities."""

import json

from pricing.knowledge.publication import current_generation


def test_published_abyss_charm_evidence_keeps_hardcore_priority_out_of_softcore():
    bundle = current_generation('pricing/data/generations')
    profiles = json.loads(bundle.artifact('pricing/data/appraisal-build-profiles.json').read_text())['profiles']
    guide = json.loads(bundle.artifact('pricing/data/appraisal-guide-sections.json').read_text())['sources'][
        'pricing/raw/mr/guides__abyss-warlock-build-guide.html'
    ]
    assert guide['sections'][44]['heading'] == 'Hardcore'
    assert 'Prioritize Life on Charms over Magic Find' in guide['sections'][46]['text']
    for slug in ('small', 'large', 'grand'):
        role = next(p for p in profiles if p['id'] == 'abyss-warlock-table-charm-' + slug)
        evidence = role['source']['corroborating']
        assert not any(r['locator'].endswith('/sections/46') for r in evidence)
        if slug == 'grand':
            assert any(r['locator'] == '/abyss-warlock-build-guide/variants/1/player/Charms/4' for r in evidence)
            builds = json.loads(bundle.artifact('pricing/data/wp-a-builds.json').read_text())
            standard = builds['abyss-warlock-build-guide']['variants'][1]
            assert standard['name'] == 'Standard'
            assert standard['player']['Charms'][4] == '6x Grand Charm +1 to Chaos Skills (Warlock) / +45 Life'
        else:
            assert '7:0' not in role['important_stats']
