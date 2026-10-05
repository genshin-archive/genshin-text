# -*- coding: utf-8 -*-
"""tmp_z5_find.py —— 关键词查库（FTS），打印命中原文（带 hash/出处）"""
import sys, os, sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
db = sqlite3.connect(os.path.join(HERE, "genshin_text.db"))
kw = sys.argv[1]
limit = int(sys.argv[2]) if len(sys.argv) > 2 else 12
rows = []
try:
    rows = db.execute("SELECT rowid FROM fts WHERE text_zh LIKE ? LIMIT ?", (f"%{kw}%", limit)).fetchall()
except Exception as e:
    print("fts err", e)
for (rid,) in rows:
    eid, src, f, h, t = db.execute(
        "SELECT entry_id,source,field,hash,text_zh FROM entries WHERE id=?", (rid,)).fetchone()
    print(f"--- {src}/{f} {eid} h={h}\n{(t or '')[:300]}\n")
