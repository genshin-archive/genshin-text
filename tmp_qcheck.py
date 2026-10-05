# -*- coding: utf-8 -*-
"""引文预检：tmp_qcheck.py <quotes.txt>  每行一条候选引文（可含「」），输出 HIT/MISS"""
import sys, os, sqlite3
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_claims import norm, seg_hit

db = sqlite3.connect(os.path.join(os.path.dirname(os.path.abspath(__file__)), "genshin_text.db"))
for line in open(sys.argv[1], encoding="utf-8"):
    s = line.strip()
    if not s:
        continue
    s = s[1:-1] if s.startswith(("「", "『")) and s.endswith(("」", "』")) else s
    print(("HIT  " if seg_hit(db, s) else "MISS ") + s[:60])
