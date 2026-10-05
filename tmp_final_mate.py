# -*- coding: utf-8 -*-
import sqlite3
db = sqlite3.connect('genshin_text.db')
db.row_factory = sqlite3.Row
print("== role_type 分布")
for r in db.execute("SELECT role_type, COUNT(*) FROM dialogue_speaker GROUP BY role_type ORDER BY 2 DESC"):
    print("  ", r[0], r[1])
print("== MATE_AVATAR 样例（按章节）")
for r in db.execute("""SELECT dc.chapter_id, dc.quest_id, dc.talk_id, e.text_zh, dc.hash
                       FROM dialogue_speaker s JOIN entries e ON e.hash=s.hash
                       JOIN dialogue_chapter dc ON dc.hash=s.hash AND dc.talk_id=s.talk_id
                       WHERE s.role_type='TALK_ROLE_MATE_AVATAR'
                       GROUP BY dc.chapter_id, dc.talk_id LIMIT 60"""):
    print("  ch=%s q=%s talk=%s | %s" % (r[0], r[1], r[2], (r[3] or "")[:110]))
