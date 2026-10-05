# -*- coding: utf-8 -*-
"""quest_play_order：章内 mainQuest 演出序表（数据来源见各章备注，只有双源互证才录入）
当前录入：
  章 1001 捕风的异乡人 — suggestTrackMainQuestList 链 + B站官方剧情回顾分集序互证
"""
import sqlite3

DB = r"C:\AI Programs\genshin-text\genshin_text.db"

# (chapter_id, quest_id, seq, evidence)
DATA = [
    (1001, 351, 1, "链头：无人track；开场（钓鱼遇派蒙）"),
    (1001, 352, 2, "351.track=[352]；B站剧情回顾第1节"),
    (1001, 353, 3, "352.track=[353]；B站第2节"),
    (1001, 355, 4, "353.track=[355]；B站第3节（林间相会）"),
    (1001, 354, 5, "355.track=[354]；B站第4节"),
    (1001, 360, 6, "354.track=[360]；B站第5节"),
    (1001, 356, 7, "360.track=[356]；B站第6节（自由之都）"),
    (1001, 357, 8, "356.track=[357]；B站第7节（龙灾）"),
    (1001, 358, 9, "357.track=[358]；B站第8节（西风骑士团）"),
    (1001, 306, 10, "358.track含306；B站第9节（昔日的风·风龙废墟）"),
    (1001, 307, 11, "306.track=[307,308]；B站第10节（安柏教学）"),
    (1001, 308, 12, "307后；B站第11节（丽莎教学）"),
]

con = sqlite3.connect(DB)
cur = con.cursor()
cur.execute("""CREATE TABLE IF NOT EXISTS quest_play_order(
    chapter_id INTEGER, quest_id INTEGER, seq INTEGER, evidence TEXT,
    PRIMARY KEY(chapter_id, quest_id))""")
cur.execute("DELETE FROM quest_play_order")
cur.executemany("INSERT INTO quest_play_order VALUES(?,?,?,?)",
                [(c, q, s, e) for c, q, s, e in DATA])
con.commit()
n = cur.execute("SELECT COUNT(*) FROM quest_play_order").fetchone()[0]
con.close()
print(f"quest_play_order: {n} 行")
