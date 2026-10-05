# -*- coding: utf-8 -*-
import sqlite3, re, sys
db=sqlite3.connect('genshin_text.db')
STRIP = re.compile(r"[\u2026\u3002\uff0c\uff01\uff1f\u3001\s\u300c\u300d\u300e\u300f\u201c\u201d\u2018\u2019\u00b7\u2014\-~!?.:;\"'()\uFF08\uFF09\n\r#\u25A0]")
def norm(s):
    s=re.sub(r"<[^>]+>","",s or ""); s=re.sub(r"\{[^}]{0,40}\}","",s); return STRIP.sub("",s)
def hit(probe):
    fn=norm(probe); cand=set()
    for n_ in (4,3):
        for i in range(max(len(fn)-n_+1,1)):
            w=fn[i:i+n_]
            for (rid,) in db.execute("SELECT rowid FROM fts WHERE text_zh LIKE ? LIMIT 400",(f"%{w}%",)):
                cand.add(rid)
    for rid in cand:
        row=db.execute("SELECT source,entry_id,field,hash,text_zh FROM entries WHERE id=?",(rid,)).fetchone()
        if fn in norm(row[4] or ""):
            return row
    return None
for probe in sys.argv[1:]:
    r=hit(probe)
    if r: print(f"OK [{probe[:16]}] -> {r[0]} {r[1]} {r[2]} hash={r[3]}")
    else: print(f"MISS [{probe[:16]}]")
