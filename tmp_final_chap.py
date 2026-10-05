# -*- coding: utf-8 -*-
import sqlite3, json
db = sqlite3.connect('genshin_text.db')
db.row_factory = sqlite3.Row
for cid in (1405, 1500, 1501, 1502, 1503, 1504, 1505, 1506, 1600, 1700, 1701, 1702, 1703):
    r = db.execute("select * from chapters where chapter_id=?", (cid,)).fetchone()
    print(dict(r) if r else (cid, None))
    qs = [x[0] for x in db.execute("select quest_id from quests where chapter_id=? order by quest_id", (cid,))]
    print("   quests:", qs)
