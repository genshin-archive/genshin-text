# -*- coding: utf-8 -*-
import sqlite3
db = sqlite3.connect("genshin_text.db")
hs = ["1123504874", "1729661778", "4036086746", "1341204370", "3308573642", "2847917842",
      "2818777930", "4224202738", "1016743914", "3586169682", "1314254618", "3037000000"]
for h in hs:
    rows = db.execute("SELECT id, text_zh FROM entries WHERE hash=?", (h,)).fetchall()
    for rid, tz in rows:
        print("%-12s id=%-8s %s" % (h, rid, tz))
# 找出所有 8018 + MATE_AVATAR 原文里含占位符的
print("=== 801818/801819 原文")
for r in db.execute("""SELECT e.hash, e.text_zh FROM dialogue_speaker s JOIN entries e ON e.hash=s.hash
                       WHERE s.role_type='TALK_ROLE_MATE_AVATAR' AND s.talk_id IN (801818,801819)"""):
    print("  %s | %s" % (r[0], r[1]))
