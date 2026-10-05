# -*- coding: utf-8 -*-
import sqlite3, re, sys
db=sqlite3.connect('genshin_text.db')
STRIP = re.compile(r"[\u2026\u3002\uff0c\uff01\uff1f\u3001\s\u300c\u300d\u300e\u300f\u201c\u201d\u2018\u2019\u00b7\u2014\-~!?.:;\"'()\uFF08\uFF09\n\r#\u25A0]")
def norm(s):
    s = re.sub(r"<[^>]+>", "", s or "")
    s = re.sub(r"\{[^}]{0,40}\}", "", s)
    return STRIP.sub("", s)
def find_story(probe):
    fp=norm(probe)
    for (rid,) in db.execute("SELECT rowid FROM fts WHERE text_zh LIKE ? LIMIT 300",(f"%{fp[:6]}%",)):
        tz=db.execute("SELECT text_zh,source FROM entries WHERE id=?",(rid,)).fetchone()
        if tz[1]=='FetterStory' and fp in norm(tz[0] or ""):
            return db.execute("SELECT entry_id FROM entries WHERE id=?",(rid,)).fetchone()[0]
    return None
probe=sys.argv[1]
eid=find_story(probe)
if not eid:
    print("NOT FOUND"); sys.exit(1)
n=int(eid[1:])
for i in range(n-1, n+9):
    rows=db.execute("SELECT field,hash,text_zh FROM entries WHERE source='FetterStory' AND entry_id=?", (f"#{i}",)).fetchall()
    if not rows: continue
    title=ctx=None; th=ch=None
    for f,h,t in rows:
        if f=='storyTitle': title,th=t,h
        elif f=='storyContext': ctx,ch=t,h
    print(f"### entry#{i}  [{title}]  title_hash={th}")
    print(f"ctx_hash={ch}")
    print((ctx or '').replace('\n','\n   '))
    print()
