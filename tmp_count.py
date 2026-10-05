# -*- coding: utf-8 -*-
"""统计断言表行数：tmp_count.py <file> [...]"""
import sys, re

for f in sys.argv[1:]:
    t = open(f, encoding="utf-8").read()
    m = re.search(r"## 二、关键断言.*?\n(\|(?:[^\n]+\n)+)", t, re.S)
    n = 0
    if m:
        for line in m.group(1).strip().split("\n"):
            cells = [c.strip() for c in line.split("|")]
            if len(cells) < 7 or cells[1] in ("主语", "") or set(cells[1]) <= {"-", " "}:
                continue
            n += 1
    print(n, f)
