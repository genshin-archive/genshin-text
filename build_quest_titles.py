# -*- coding: utf-8 -*-
"""quest_titles：mainQuest 官方标题表（TextMap 直查，零猜测），供 browse 任务分组显示"""
import json
import os
import sqlite3

BASE = r"C:\AI Programs\genshin-text"
TM = json.load(open(os.path.join(BASE, r"AnimeGameData2\TextMap\TextMapCHS.json"), encoding="utf-8"))
TMm = json.load(open(os.path.join(BASE, r"AnimeGameData2\TextMap\TextMap_MediumCHS.json"), encoding="utf-8"))
mq = json.load(open(os.path.join(BASE, r"AnimeGameData2\ExcelBinOutput\MainQuestExcelConfigData.json"), encoding="utf-8"))

def zh(h):
    k = str(h or "")
    return TM.get(k) or TMm.get(k) or ""

con = sqlite3.connect(os.path.join(BASE, "genshin_text.db"))
cur = con.cursor()
cur.execute("""CREATE TABLE IF NOT EXISTS quest_titles(
    quest_id INTEGER PRIMARY KEY, title TEXT, chapter_id INTEGER)""")
cur.execute("DELETE FROM quest_titles")
n = 0
for m in mq:
    t = zh(m.get("titleTextMapHash"))
    if t:
        cur.execute("INSERT OR REPLACE INTO quest_titles VALUES(?,?,?)",
                    (m["id"], t, m.get("chapterId")))
        n += 1
con.commit()
print(f"quest_titles: {n} 行")
# 抽查
for qid in (306, 351, 357):
    r = cur.execute("SELECT title FROM quest_titles WHERE quest_id=?", (qid,)).fetchone()
    print(f"  {qid}: {r[0] if r else '<无>'}")
con.close()
