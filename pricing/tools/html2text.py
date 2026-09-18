#!/usr/bin/env python3
"""html2text.py FILE [KEYWORD [CONTEXT]] — strip tags, print plain text (or ±CONTEXT chars around every KEYWORD hit).
Good enough for maxroll / diablo2.io / d2runes.io pages, which are server-rendered."""
import re, html, sys
s = open(sys.argv[1], encoding='utf8', errors='ignore').read()
t = re.sub(r'<script.*?</script>|<style.*?</style>', '', s, flags=re.S)
t = html.unescape(re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', t)))
if len(sys.argv) > 2:
    kw = sys.argv[2]; ctx = int(sys.argv[3]) if len(sys.argv) > 3 else 300
    for m in re.finditer(re.escape(kw), t):
        print('…', t[max(0, m.start()-ctx):m.start()+ctx], '…\n')
else:
    print(t)
