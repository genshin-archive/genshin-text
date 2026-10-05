# -*- coding: utf-8 -*-
import sqlite3, sys
from check_claims import norm, DB
conn = sqlite3.connect(DB)
rows = [r[0] for r in conn.execute("SELECT text_zh FROM entries")]
blob = "\x00".join(norm(t or "") for t in rows)
cands = sys.argv[1:]
for c in cands:
    n = norm(c)
    print(("OK   " if n and n in blob else "MISS "), c)
