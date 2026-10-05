# -*- coding: utf-8 -*-
import sqlite3
db = sqlite3.connect('genshin_text.db')
print('id=660394 ->', db.execute('select id,hash,text_zh,source from entries where id=660394').fetchone())
print('hash like ->', db.execute("select id,hash,text_zh,source from entries where hash like '%660394%'").fetchall())
print('hash 38382322 ->', db.execute("select id,hash,text_zh from entries where hash=?", ("38382322",)).fetchall())
for r in db.execute("""SELECT dc.chapter_id, dc.quest_id, dc.talk_id, s.speaker, s.role_type, e.text_zh
                       FROM entries e JOIN dialogue_chapter dc ON dc.hash=e.hash
                       LEFT JOIN dialogue_speaker s ON s.hash=e.hash AND s.talk_id=dc.talk_id
                       WHERE e.hash=?""", ("38382322",)):
    print(r)
