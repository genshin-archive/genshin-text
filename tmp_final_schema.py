# -*- coding: utf-8 -*-
import sqlite3
db = sqlite3.connect('genshin_text.db')
for name, sql in db.execute("select name,sql from sqlite_master where type in ('table','view')"):
    print("==", name)
    print((sql or "")[:600].replace("\n", " "))
print("---- counts")
for t in ("entries", "talks", "fts"):
    try:
        print(t, db.execute("select count(*) from %s" % t).fetchone()[0])
    except Exception as e:
        print(t, "ERR", e)
print("---- entries sample")
cur = db.execute("select * from entries limit 3")
print([d[0] for d in cur.description])
for r in cur:
    print(r)
