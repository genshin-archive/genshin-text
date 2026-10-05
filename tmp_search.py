# -*- coding: utf-8 -*-
import sqlite3, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
db = sqlite3.connect(r'C:\AI Programs\genshin-text\genshin_text.db')

kws = sys.argv[1:]
for kw in kws:
    print("=" * 20, "关键词:", kw, "=" * 20)
    rows = db.execute(
        "SELECT id, source, entry_id, title, text_zh FROM entries WHERE text_zh LIKE ? LIMIT 40",
        ('%' + kw + '%',)).fetchall()
    print("命中条数(截取40):", len(rows))
    for r in rows:
        t = r[4].replace('\n', ' ')
        if len(t) > 120:
            t = t[:120] + '...'
        print(f"[{r[0]}] src={r[1]} entry={r[2]} title={r[3]} | {t}")
