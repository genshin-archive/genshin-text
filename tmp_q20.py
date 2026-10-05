# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import sqlite3
db = sqlite3.connect('genshin_text.db')
if len(sys.argv) > 1 and sys.argv[1] == 'find':
    for eid in sys.argv[2:]:
        rows = db.execute('SELECT id,category,source,entry_id,title FROM entries WHERE entry_id=?', (eid,)).fetchall()
        print(eid, '->', rows[:6])
elif len(sys.argv) > 1 and sys.argv[1] == 'dump':
    eid = sys.argv[2]
    rows = db.execute('SELECT id,category,source,entry_id,field,hash,title,text_zh FROM entries WHERE entry_id=? ORDER BY id', (eid,)).fetchall()
    for r in rows:
        print('### id=%s cat=%s src=%s eid=%s field=%s hash=%s title=%s' % (r[0], r[1], r[2], r[3], r[4], r[5], r[6]))
        print(r[7])
        print()
elif len(sys.argv) > 1 and sys.argv[1] == 'grep':
    pat = sys.argv[2]
    rows = db.execute('SELECT id,category,source,entry_id,title,SUBSTR(text_zh,1,200) FROM entries WHERE text_zh LIKE ? LIMIT 20', ('%'+pat+'%',)).fetchall()
    for r in rows:
        print(r)
