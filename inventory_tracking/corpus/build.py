"""Collect the distinct items captured by Alt+D into a replayable corpus.

    uv run --offline python -m inventory_tracking.corpus.build

Writes data/items.jsonl (one observation per distinct item) and data/label.html, a page for
labelling a stratified sample; save its export as data/labels.json.
"""

import argparse
import hashlib
import html
import json
import random
from pathlib import Path
from tempfile import NamedTemporaryFile


DATA = Path(__file__).parent / 'data'
RUNS = Path('inventory_tracking/runs/alt-d')
# Items of each rarity offered for labelling; named items first because rolls decide them.
SAMPLE = {'unique': 45, 'set': 25, 'rare': 35, 'magic': 35, 'crafted': 5, 'normal': 10, 'superior': 5}
LABELS = ('sell', 'slow', 'self', 'vendor', 'check')


def stat_lines(observation) -> list[str]:
    return [
        stat['text']
        for stat in observation.get('decoded_stats', [])
        if stat.get('status') == 'decoded' and stat.get('presentation') != 'internal' and stat.get('text')
    ]


def item_id(observation) -> str:
    """Same item facts → same id, so repeated captures of one drop collapse and labels survive rebuilds."""
    item = observation['item']
    facts = [item.get(key) for key in ('rarity', 'name', 'base_name', 'ethereal', 'sockets', 'runeword')]
    return hashlib.sha256(json.dumps([facts, sorted(stat_lines(observation))], sort_keys=True).encode()).hexdigest()[
        :12
    ]


def collect(runs: Path) -> dict[str, dict]:
    items = {}
    for path in sorted([*runs.glob('*/request-*/frozen.json'), *runs.glob('*/identified/*.json')]):
        try:
            observation = json.loads(path.read_text())['observation']
            items[item_id(observation)] = observation
        except OSError, ValueError, KeyError, TypeError:
            continue
    return items


def disagreements(data):
    path = data / 'disagreements.json'
    return json.loads(path.read_text()) if path.exists() else {}


def review_order(ids, feedback):
    pending = [identifier for identifier, row in feedback.items() if row.get('status') == 'pending']
    return list(dict.fromkeys([*pending, *ids]))


def merge(runs: Path, data: Path) -> dict[str, dict]:
    """Retain archived/labelled cases and add live captures without touching labels."""
    path = data / 'items.jsonl'
    previous = path.read_text() if path.exists() else ''
    records = [json.loads(line) for line in previous.splitlines() if line.strip()]
    items = {row['id']: row['observation'] for row in records}
    items.update(collect(runs))
    items.update({identifier: row['observation'] for identifier, row in disagreements(data).items()})
    contents = ''.join(
        json.dumps({'id': key, 'observation': items[key]}, separators=(',', ':')) + '\n' for key in sorted(items)
    )
    if contents != previous or not path.exists():
        data.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(mode='w', dir=data, prefix='.items-', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(contents)
        temporary.replace(path)
    return items


def sample(items: dict[str, dict], seed=20261003) -> list[str]:
    """A fixed stratified sample; per rarity, distinct names before repeats of one name."""
    chosen = []
    for rarity, count in SAMPLE.items():
        ids = sorted(i for i, o in items.items() if o['item'].get('rarity') == rarity)
        random.Random(seed).shuffle(ids)
        seen, first, rest = set(), [], []
        for identifier in ids:
            name = items[identifier]['item'].get('name')
            (rest if name in seen else first).append(identifier)
            seen.add(name)
        chosen.extend((first + rest)[:count])
    return chosen


def label_page(items: dict[str, dict], ids: list[str], *, labels=None) -> str:
    cards = []
    for identifier in ids:
        observation = items[identifier]
        item = observation['item']
        title = item.get('name', '?')
        if item.get('base_name') and item['base_name'] != title:
            title += f' ({item["base_name"]})'
        flags = [item.get('rarity', '?')]
        if item.get('ethereal'):
            flags.append('ethereal')
        if item.get('sockets'):
            flags.append(f'{item["sockets"]} sockets')
        stats = ''.join(f'<li>{html.escape(line)}</li>' for line in stat_lines(observation))
        buttons = ''.join(
            f'<button data-label="{label}">{index} {label}</button>' for index, label in enumerate(LABELS, 1)
        )
        cards.append(
            f'<section id="{identifier}" class="{html.escape(item.get("rarity", ""))}"><h2>{html.escape(title)}</h2>'
            f'<p>{html.escape(" · ".join(flags))}</p><ul>{stats}</ul><div>{buttons}</div></section>'
        )
    return PAGE.replace('{{cards}}', '\n'.join(cards)).replace(
        '{{labels}}', json.dumps(labels or {}).replace('<', '\\u003c')
    )


PAGE = """<!doctype html><meta charset="utf-8"><title>D2R drop labels</title>
<style>
body{font:15px system-ui;background:#16161a;color:#ddd;max-width:760px;margin:0 auto;padding:16px 16px 90px}
section{border:1px solid #333;border-radius:6px;padding:10px 14px;margin:10px 0}
section.current{border-color:#e0c060}section[data-done]{opacity:.55}
h2{font-size:17px;margin:0}.unique h2{color:#c7b377}.set h2{color:#3fd63f}
.rare h2{color:#f5f56b}.magic h2{color:#7b7bff}
p{margin:2px 0;color:#999}ul{margin:6px 0;padding-left:18px}
button{font:inherit;margin-right:6px;padding:4px 10px;background:#2a2a30;color:#ddd;
border:1px solid #555;border-radius:4px;cursor:pointer}
button.on{background:#e0c060;color:#000}
#bar{position:fixed;bottom:0;left:0;right:0;background:#000;padding:10px 16px;border-top:1px solid #444}
</style>
<h1>Label drops</h1>
<p>Softcore / Non-Ladder. <b>sell</b>: I would keep it to trade and it sells easily · <b>slow</b>: valuable but
few buyers · <b>self</b>: keep for my own characters only · <b>vendor</b>: not worth stash space.<br>
Keys 1-5 label the highlighted item and move on; arrows move. Labels are kept in this browser until exported.</p>
{{cards}}
<div id="bar"><span id="count"></span> <button id="save">Download labels.json</button>
<button id="copy">Copy JSON</button></div>
<script>
const KEY = 'd2r-drop-labels', LABELS = ['sell', 'slow', 'self', 'vendor', 'check'];
const cards = [...document.querySelectorAll('section')];
let labels = {{labels}};
try { labels = {...labels, ...JSON.parse(localStorage.getItem(KEY) || '{}')}; } catch (e) {}
let current = Math.max(0, cards.findIndex(c => !labels[c.id]));
function paint() {
  cards.forEach((card, index) => {
    card.classList.toggle('current', index === current);
    if (labels[card.id]) card.dataset.done = '1'; else delete card.dataset.done;
    card.querySelectorAll('button').forEach(b => b.classList.toggle('on', labels[card.id] === b.dataset.label));
  });
  document.getElementById('count').textContent = Object.keys(labels).length + ' / ' + cards.length + ' labelled';
}
function setLabel(index, label) {
  labels[cards[index].id] = label;
  try { localStorage.setItem(KEY, JSON.stringify(labels)); } catch (e) {}
  move(index + 1);
}
function move(index) {
  current = Math.min(cards.length - 1, Math.max(0, index));
  paint();
  cards[current].scrollIntoView({block: 'center'});
}
cards.forEach((card, index) => card.addEventListener('click', event => {
  if (event.target.dataset.label) setLabel(index, event.target.dataset.label); else { current = index; paint(); }
}));
document.addEventListener('keydown', event => {
  if ('12345'.includes(event.key)) setLabel(current, LABELS[+event.key - 1]);
  if (event.key === 'ArrowDown') { event.preventDefault(); move(current + 1); }
  if (event.key === 'ArrowUp') { event.preventDefault(); move(current - 1); }
});
document.getElementById('save').onclick = () => {
  const link = document.createElement('a');
  link.href = URL.createObjectURL(new Blob([JSON.stringify(labels, null, 1)], {type: 'application/json'}));
  link.download = 'labels.json';
  link.click();
};
document.getElementById('copy').onclick = () => navigator.clipboard.writeText(JSON.stringify(labels, null, 1));
paint();
</script>
"""


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runs', type=Path, default=RUNS)
    parser.add_argument('--data', type=Path, default=DATA)
    args = parser.parse_args(argv)
    items = merge(args.runs, args.data)
    args.data.mkdir(parents=True, exist_ok=True)
    ids = sample(items)
    labels_path = args.data / 'labels.json'
    labels = json.loads(labels_path.read_text()) if labels_path.exists() else {}
    (args.data / 'label.html').write_text(label_page(items, ids, labels=labels))
    print(
        f'{len(items)} distinct items → {args.data / "items.jsonl"}; {len(ids)} to label → {args.data / "label.html"}'
    )


if __name__ == '__main__':
    main()
