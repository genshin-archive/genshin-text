# -*- coding: utf-8 -*-
"""任务索引重建：Chapter/QuestCodex/PersonalLine → chapters/quests 表 + 对话→章节完整链"""
import json
import os
import sqlite3
import time

ROOT = r"C:\AI Programs\genshin-text\AnimeGameData2"
DB = r"C:\AI Programs\genshin-text\genshin_text.db"

t0 = time.time()
print("加载 TextMap 合并池...")
med = json.load(open(os.path.join(ROOT, "TextMap", "TextMap_MediumCHS.json"), encoding="utf-8"))
chs = json.load(open(os.path.join(ROOT, "TextMap", "TextMapCHS.json"), encoding="utf-8"))
lookup = {**med, **chs}
print(f"  {len(lookup)} 条, {time.time()-t0:.0f}s")


def load(name):
    return json.load(open(os.path.join(ROOT, "ExcelBinOutput", name), encoding="utf-8"))


chapter = load("ChapterExcelConfigData.json")
codex = load("QuestCodexExcelConfigData.json")
personal = load("PersonalLineExcelConfigData.json")

con = sqlite3.connect(DB)
cur = con.cursor()
cur.execute("""CREATE TABLE IF NOT EXISTS chapters(
    chapter_id INTEGER PRIMARY KEY, name TEXT, num TEXT, city_id INTEGER,
    quest_type TEXT, begin_quest INTEGER, end_quest INTEGER)""")
cur.execute("""CREATE TABLE IF NOT EXISTS quests(
    quest_id INTEGER PRIMARY KEY, chapter_id INTEGER)""")

# 1. chapters：章节名解析（合并池）+ 类型判定
rows = []
for c in chapter:
    cid = c["id"]
    title = lookup.get(str(c.get("chapterTitleTextMapHash", "")), "")
    num = lookup.get(str(c.get("chapterNumTextMapHash", "")), "")
    style = c.get("IMFDDPKLIDD", "")  # CHAPTER_STYLE_TYPE_AQ 等
    if not title:
        continue
    qtype = "传说任务" if cid >= 2000 else ("魔神任务" if style.endswith("_AQ") or 1000 < cid < 2000 else "其他")
    rows.append((cid, title, num, c.get("cityId"), qtype,
                 c.get("beginQuestId"), c.get("endQuestId")))
cur.execute("DELETE FROM chapters")
cur.executemany("INSERT OR REPLACE INTO chapters VALUES(?,?,?,?,?,?,?)", rows)
print(f"chapters: {len(rows)} 章（有名字的）")

# 2. quests：QuestCodex chapterId → parentQuestId
qrows = []
for x in codex:
    qrows.append((x["parentQuestId"], x["chapterId"]))
cur.execute("DELETE FROM quests")
cur.executemany("INSERT OR REPLACE INTO quests VALUES(?,?)", qrows)
# PersonalLine 的 chapterId 也补入（部分传说任务不在 Codex）
for x in personal:
    qrows.append((x["startQuestId"], x["chapterId"]))
cur.executemany("INSERT OR IGNORE INTO quests VALUES(?,?)",
                [(x["startQuestId"], x["chapterId"]) for x in personal])
print(f"quests: {len(qrows)} 条")

# 3. 对话→章节链：talk_map.quest_id → quests.chapter_id
cur.execute("""DROP TABLE IF EXISTS dialogue_chapter""")
cur.execute("""CREATE TABLE dialogue_chapter AS
    SELECT DISTINCT t.hash, t.quest_id, q.chapter_id
    FROM talk_map t LEFT JOIN quests q ON t.quest_id = q.quest_id""")
n_all = cur.execute("SELECT COUNT(*) FROM dialogue_chapter").fetchone()[0]
n_linked = cur.execute("SELECT COUNT(*) FROM dialogue_chapter WHERE chapter_id IS NOT NULL").fetchone()[0]
print(f"dialogue_chapter: {n_all} hash, 已挂章节 {n_linked} ({n_linked*100//max(n_all,1)}%)")

# 4. 主线各章对话量验证
print("\n主线章节对话覆盖：")
main_chaps = cur.execute("""SELECT c.chapter_id, c.name, c.num, COUNT(dc.hash)
    FROM chapters c LEFT JOIN dialogue_chapter dc ON c.chapter_id = dc.chapter_id
    WHERE c.chapter_id BETWEEN 1001 AND 1999
    GROUP BY c.chapter_id ORDER BY c.chapter_id""").fetchall()
total_main = 0
for cid, name, num, n in main_chaps:
    total_main += n
    flag = "⚠️" if n == 0 else "  "
    print(f"  {flag} {cid} [{num}] {name}: {n} 条")
print(f"主线合计: {total_main} 条对话 / {len(main_chaps)} 章")

con.commit()
con.close()
print(f"\n完成, 耗时 {time.time()-t0:.0f}s")
