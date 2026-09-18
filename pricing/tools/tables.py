#!/usr/bin/env python3
"""tables.py FILE.html [--tsv] — dump every <table> as rows (cells separated by ' | ' or tabs).
Verified 2026-09-18 on maxroll build guides: the gear tables have header row 'Slot | Item Options | Desirable Stats'
and the mercenary table 'Slot | Early-Game | Mid-Game | End-Game'. Item names inside a cell are space-separated
(each <a> becomes ' Name '), so split on double spaces or match against a known item list."""
import sys
from html.parser import HTMLParser
class TP(HTMLParser):
    def __init__(s): super().__init__(); s.tables=[]; s.cur=None; s.row=None; s.cell=None
    def handle_starttag(s,tag,a):
        if tag=='table': s.cur=[]
        elif tag=='tr' and s.cur is not None: s.row=[]
        elif tag in('td','th') and s.row is not None: s.cell=[]
    def handle_endtag(s,tag):
        if tag in('td','th') and s.cell is not None: s.row.append(' '.join(''.join(s.cell).split())); s.cell=None
        elif tag=='tr' and s.row is not None: s.cur.append(s.row); s.row=None
        elif tag=='table' and s.cur is not None: s.tables.append(s.cur); s.cur=None
    def handle_data(s,d):
        if s.cell is not None: s.cell.append('  '+d+'  ')
p=TP(); p.feed(open(sys.argv[1],encoding='utf8',errors='ignore').read())
sep='\t' if '--tsv' in sys.argv else ' | '
for i,t in enumerate(p.tables):
    print(f'### table {i} ({len(t)} rows)')
    for r in t: print(sep.join(r))
    print()
