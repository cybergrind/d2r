"""Per-zone Tier 1 / Tier 5 first-spawn chances and probability charts for the guide.

Uses the same unvalidated article approximation as diagnostic.py: fully populated,
equally weighted monsters, zero base chance, continuous pre-kill completion. The
"Tier 5 chance" is the chance of at least one Tier 5 Herald in a full clear of a
fresh group when Tier 5 is already the next tier. Populations are article means.
"""

import argparse
import json
from pathlib import Path

from terror_zones.diagnostic import first_spawn, hazard


ZONES = Path(__file__).with_name('data') / 'article-zones.json'
OUTPUT = Path(__file__).with_name('data') / 'zone-table.json'
TIERS = (1, 2, 3, 4, 5)
POPULATION_AXIS = 600
# Categorical palette slots 1..5 (light, dark), see dataviz reference palette.
SERIES = ('#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4')
SERIES_DARK = ('#3987e5', '#d95926', '#199e70', '#c98500', '#d55181')


def load_zones(path: Path = ZONES) -> dict[str, list[tuple[str, int]]]:
    data = json.loads(path.read_text())
    return {act: [(name, int(n)) for name, n in groups] for act, groups in data['acts'].items()}


def zone_rows(zones: dict[str, list[tuple[str, int]]]) -> dict[str, list[dict]]:
    """Rows per act, largest population first."""
    table = {}
    for act, groups in zones.items():
        rows = []
        for name, total in groups:
            t1 = first_spawn(total, 1)
            t5 = first_spawn(total, 5)
            rows.append(
                {
                    'group': name,
                    'monsters': total,
                    'tier1_chance': t1['spawn_probability'],
                    'tier1_expected_kills': t1['expected_kills_until_spawn_or_exhaustion'],
                    'tier5_chance': t5['spawn_probability'],
                    'tier5_expected_kills': t5['expected_kills_until_spawn_or_exhaustion'],
                }
            )
        table[act] = sorted(rows, key=lambda row: (-row['monsters'], row['group']))
    return table


def hazard_curves() -> dict[int, list[tuple[float, float]]]:
    return {tier: [(x, 100 * hazard(tier, x)) for x in range(101)] for tier in TIERS}


def spawn_curves(limit: int = POPULATION_AXIS, tiers: tuple[int, ...] = (1, 5)) -> dict[int, list[tuple[int, float]]]:
    return {tier: [(n, 100 * first_spawn(n, tier)['spawn_probability']) for n in range(1, limit + 1)] for tier in tiers}


# ---------------------------------------------------------------- SVG rendering

W, H = 720, 360
PAD = {'l': 52, 'r': 64, 't': 18, 'b': 40}


def _scale(lo: float, hi: float, a: float, b: float):
    return lambda v: a + (v - lo) / (hi - lo) * (b - a)


def _path(points, sx, sy) -> str:
    return ' '.join(f'{"M" if i == 0 else "L"}{sx(x):.1f},{sy(y):.1f}' for i, (x, y) in enumerate(points))


def line_chart(
    chart_id: str,
    title: str,
    series: dict[int, list[tuple[float, float]]],
    *,
    x_label: str,
    y_label: str,
    x_max: float,
    y_max: float,
    x_ticks: list[float],
    y_ticks: list[float],
    x_unit: str = '',
) -> str:
    sx = _scale(0, x_max, PAD['l'], W - PAD['r'])
    sy = _scale(0, y_max, H - PAD['b'], PAD['t'])
    grid = ''.join(
        f'<line class="grid" x1="{PAD["l"]}" x2="{W - PAD["r"]}" y1="{sy(t):.1f}" y2="{sy(t):.1f}"/>'
        f'<text class="tick" x="{PAD["l"] - 6}" y="{sy(t) + 4:.1f}" text-anchor="end">{t:g}%</text>'
        for t in y_ticks
    )
    xt = ''.join(
        f'<text class="tick" x="{sx(t):.1f}" y="{H - PAD["b"] + 16}" text-anchor="middle">{t:g}{x_unit}</text>'
        for t in x_ticks
    )
    paths = ''.join(
        f'<path class="s{tier}" d="{_path(points, sx, sy)}"><title>Tier {tier}</title></path>'
        for tier, points in series.items()
    )
    # Direct labels at the right end, nudged apart so they never overlap.
    ends = sorted(((sy(points[-1][1]), tier) for tier, points in series.items()))
    placed = []
    for y, tier in ends:
        if placed and y - placed[-1][0] < 13:
            y = placed[-1][0] + 13
        placed.append((y, tier))
    labels = ''.join(
        f'<text class="lbl s{tier}" x="{W - PAD["r"] + 6}" y="{y + 4:.1f}">T{tier}</text>' for y, tier in placed
    )
    data = json.dumps({tier: [round(y, 4) for _, y in points] for tier, points in series.items()})
    legend = ''.join(f'<span><i class="dot s{t}"></i>Tier {t}</span>' for t in series)
    return (
        f'<figure class="viz" id="{chart_id}"><figcaption>{title}</figcaption>'
        f'<div class="legend viz-legend">{legend}</div><div class="vizwrap">'
        f'<svg viewBox="0 0 {W} {H}" role="img" aria-labelledby="{chart_id}-t" '
        f'data-series=\'{data}\' data-xmax="{x_max}" data-xunit="{x_unit}">'
        f'<title id="{chart_id}-t">{title}</title>{grid}{xt}'
        f'<line class="axis" x1="{PAD["l"]}" x2="{W - PAD["r"]}" y1="{H - PAD["b"]}" y2="{H - PAD["b"]}"/>'
        f'<text class="tick" x="{(PAD["l"] + W - PAD["r"]) / 2:.0f}" y="{H - 6}" text-anchor="middle">{x_label}</text>'
        f'<text class="tick" transform="translate(12,{(PAD["t"] + H - PAD["b"]) / 2:.0f}) rotate(-90)" '
        f'text-anchor="middle">{y_label}</text>'
        f'{paths}{labels}'
        f'<line class="cross" x1="0" x2="0" y1="{PAD["t"]}" y2="{H - PAD["b"]}" visibility="hidden"/>'
        f'<rect class="hit" x="{PAD["l"]}" y="{PAD["t"]}" width="{W - PAD["l"] - PAD["r"]}" '
        f'height="{H - PAD["t"] - PAD["b"]}" fill="transparent"/>'
        f'</svg><div class="tip" hidden="hidden"></div></div></figure>'
    )


def hazard_chart_html() -> str:
    return line_chart(
        'fig-hazard',
        'Chance per ordinary kill that the next Herald spawns, by completion (article model, zero base chance)',
        hazard_curves(),
        x_label='Group completion, % of original population killed since the last reset',
        y_label='Chance on this kill',
        x_max=100,
        y_max=4.5,
        x_ticks=[0, 20, 40, 60, 80, 100],
        y_ticks=[0, 1, 2, 3, 4],
        x_unit='%',
    )


def spawn_chart_html() -> str:
    return line_chart(
        'fig-spawn',
        'Chance of at least one Tier 1 or Tier 5 Herald in a full clear of a fresh group, by population',
        spawn_curves(),
        x_label='Ordinary monsters in the group (article mean population)',
        y_label='Chance of at least one spawn',
        x_max=POPULATION_AXIS,
        y_max=100,
        x_ticks=[0, 100, 200, 300, 400, 500, 600],
        y_ticks=[0, 25, 50, 75, 100],
    )


def charts_html() -> str:
    return hazard_chart_html() + spawn_chart_html()


def table_html(table: dict[str, list[dict]]) -> str:
    body = ''
    for act, rows in table.items():
        body += (
            f'<tr class="act"><th colspan="4">Act {act} · {len(rows)} groups · '
            f'{sum(r["monsters"] for r in rows):,} monsters</th></tr>'
        )
        for r in rows:
            body += (
                f'<tr><td>{r["group"]}</td><td class="num">{r["monsters"]}</td>'
                f'<td class="num">{100 * r["tier1_chance"]:.1f}%</td>'
                f'<td class="num">{100 * r["tier5_chance"]:.1f}%</td></tr>'
            )
    return (
        '<div class="tblwrap"><table class="zones"><thead><tr><th>Zone group (shared counter)</th>'
        '<th>Monsters</th><th>Tier 1 chance</th><th>Tier 5 chance</th></tr></thead>'
        f'<tbody>{body}</tbody></table></div>'
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--html', action='store_true', help='print the guide fragment instead of JSON')
    parser.add_argument('--write', action='store_true', help=f'save JSON to {OUTPUT}')
    args = parser.parse_args()
    table = zone_rows(load_zones())
    if args.html:
        print(charts_html())
        print(table_html(table))
        return
    payload = {
        'model': 'unvalidated article approximation; fresh fully populated group, zero base chance',
        'source': str(ZONES.name),
        'tier5_chance_meaning': 'at least one Tier 5 Herald in a full clear when Tier 5 is already the next tier',
        'acts': table,
    }
    text = json.dumps(payload, indent=2)
    if args.write:
        OUTPUT.write_text(text + '\n')
    print(text)


if __name__ == '__main__':
    main()
