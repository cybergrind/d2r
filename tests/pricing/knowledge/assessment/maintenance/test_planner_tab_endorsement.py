"""A planner is endorsed by its own named tab, never a neighboring variant."""

import pytest

from pricing.knowledge.assessment.maintenance.planner_tab_endorsement import tab_endorses
from tests.pricing.knowledge.assessment.maintenance.test_planner_endorsement import ROOT


HTML = """<div class="_tabsV2_hash_1"><div class="_header_hash_2">Starter</div>
<div class="_header_hash_2">Ubers</div><div class="_tab_hash_1">
<p>Use <strong>Cannot Be Frozen</strong> for this setup.</p>
<span class="d2-player" data-d2-id="guide123" data-d2-set-id="starter1"></span>
</div><div class="_tab_hash_1"><p>Different setup.</p>
<span class="d2-player" data-d2-id="guide123" data-d2-set-id="ubers1"></span></div></div>"""
QUOTE = 'Use Cannot Be Frozen for this setup.'


def test_tab_binds_label_quote_and_actual_planner_profile():
    assert tab_endorses(HTML, 'Starter', 'guide123', 'starter1', QUOTE)


@pytest.mark.parametrize(
    ('label', 'planner', 'profile', 'quote'),
    [
        ('Ubers', 'guide123', 'starter1', QUOTE),
        ('Starter', 'guide123', 'ubers1', QUOTE),
        ('Starter', 'other', 'starter1', QUOTE),
        ('Starter', 'guide123', 'starter1', 'Different setup.'),
    ],
)
def test_neighboring_tab_or_unrelated_planner_is_not_endorsed(label, planner, profile, quote):
    assert not tab_endorses(HTML, label, planner, profile, quote)


def test_raw_mirrored_starter_embeds_its_exact_profile():
    html = (ROOT / 'pricing/raw/mr/guides__mirrored-blades-warlock-guide.html').read_text()
    quote = 'As a Warlock, keep in mind that you can wield a 2-Handed Weapon in a single hand.'
    assert tab_endorses(html, 'Starter', 'rg2je0ld', '8IRFWTHa', quote)
    assert not tab_endorses(html, 'Ubers', 'rg2je0ld', '8IRFWTHa', quote)


@pytest.mark.parametrize(
    'html',
    [
        HTML + HTML,
        HTML.replace('<div class="_header_hash_2">Ubers</div>', ''),
        HTML.rsplit('</div>', 1)[0],
        HTML.replace('class="d2-player"', 'class="tooltip"'),
    ],
)
def test_ambiguous_incomplete_or_nonplanner_tab_fails_closed(html):
    assert not tab_endorses(html, 'Starter', 'guide123', 'starter1', QUOTE)
