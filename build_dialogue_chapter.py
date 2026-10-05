# -*- coding: utf-8 -*-
"""用官方映射重建 dialogue_chapter：hash→talk_id→(Talk表)questId→chapter"""
import json
import os
import sqlite3

ROOT = r"C:\AI Programs\genshin-text\AnimeGameData2"
DB = r"C:\AI Programs\genshin-text\genshin_text.db"

# Talk 表官方映射：talk_id → questId
talk2quest = {}
for fn in ("TalkExcelConfigData_0.json", "TalkExcelConfigData_1.json"):
    for x in json.load(open(os.path.join(ROOT, "ExcelBinOutput", fn), encoding="utf-8")):
        if x.get("id") and x.get("questId"):
            talk2quest[x["id"]] = x["questId"]
print(f"Talk 官方映射: {len(talk2quest)} 条")

con = sqlite3.connect(DB)
cur = con.cursor()
cur.execute("DROP TABLE IF EXISTS dialogue_chapter")
cur.execute("""CREATE TABLE dialogue_chapter(
    hash TEXT, quest_id INTEGER, chapter_id INTEGER,
    talk_id INTEGER, doc_order INTEGER, file_id INTEGER)""")

rows = cur.execute("SELECT hash, talk_id, kind, file_id, doc_order FROM dialogue_seq").fetchall()
out = []
seen = set()
skipped = 0
for h, tid, kind, fid, order in rows:
    if kind == "Activity":
        # 修复 v2.2：Activity 目录对话的 Talk 表 questId 会误挂主线 quest
        #（1204 曾混入 1222 行活动文本），全部排除
        skipped += 1
        continue
    qid = talk2quest.get(tid)
    if qid is None:
        continue
    ch = cur.execute("SELECT chapter_id FROM quests WHERE quest_id=?", (qid,)).fetchone()
    ch = ch[0] if ch else None
    key = (h, qid, tid)
    if key in seen:
        continue
    seen.add(key)
    out.append((h, qid, ch, tid, order, fid))
print(f"跳过 Activity 行: {skipped}")

cur.executemany("INSERT INTO dialogue_chapter VALUES(?,?,?,?,?,?)", out)
cur.execute("CREATE INDEX idx_dc_ch ON dialogue_chapter(chapter_id, quest_id, doc_order)")
con.commit()

n = cur.execute("SELECT COUNT(*) FROM dialogue_chapter").fetchone()[0]
nlinked = cur.execute("SELECT COUNT(*) FROM dialogue_chapter WHERE chapter_id IS NOT NULL").fetchone()[0]
# 验证：魈的台词是否还在序章
bad = cur.execute("""SELECT COUNT(*) FROM dialogue_chapter dc JOIN entries e ON e.hash=dc.hash
  WHERE dc.chapter_id=1001 AND e.text_zh LIKE '%百无禁忌箓%'""").fetchone()[0]
# 验证：序章第一幕开头
head = cur.execute("""SELECT e.text_zh FROM dialogue_chapter dc JOIN entries e ON e.hash=dc.hash
  WHERE dc.chapter_id=1001 ORDER BY dc.quest_id, dc.doc_order LIMIT 5""").fetchall()
con.close()
print(f"dialogue_chapter: {n} 行, 挂章节 {nlinked} ({nlinked*100//max(n,1)}%)")
print(f"序章残留魈台词: {bad} 条（应为 0）")
print("序章开头 5 行:")
for (t,) in head:
    print(f"  {t[:70]}".replace(chr(10), " / "))
