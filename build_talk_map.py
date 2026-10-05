# -*- coding: utf-8 -*-
"""解析 BinOutput/Talk 对话流 → talk_map 表（文本 hash → talkId/任务出处）"""
import io
import json
import os
import sqlite3
import time

ROOT = r"C:\AI Programs\genshin-text\AnimeGameData2"
DB = r"C:\AI Programs\genshin-text\genshin_text.db"
OUT = r"C:\AI Programs\genshin-text\talk_map.json"

t0 = time.time()
print("加载 TextMap 池...")
pool = set()
for fn in ("TextMapCHS.json", "TextMap_MediumCHS.json"):
    pool |= set(json.load(open(os.path.join(ROOT, "TextMap", fn), encoding="utf-8")).keys())
print(f"  {len(pool)} hashes, {time.time()-t0:.0f}s")

print("加载 Talk/MainQuest 表...")
talk_rows = []
for fn in ("TalkExcelConfigData_0.json", "TalkExcelConfigData_1.json"):
    talk_rows += json.load(open(os.path.join(ROOT, "ExcelBinOutput", fn), encoding="utf-8"))
talk_quest = {x["id"]: x.get("questId") for x in talk_rows if x.get("id")}
talk_ids = set(talk_quest)
mq = json.load(open(os.path.join(ROOT, "ExcelBinOutput", "MainQuestExcelConfigData.json"), encoding="utf-8"))
chs_titles = json.load(open(os.path.join(ROOT, "TextMap", "TextMapCHS.json"), encoding="utf-8"))
quest_title = {}
for x in mq:
    h = str(x.get("titleTextMapHash") or "")
    if h and h in chs_titles:
        quest_title[x["id"]] = chs_titles[h]
print(f"  talk {len(talk_ids)}, mainQuest {len(quest_title)}, {time.time()-t0:.0f}s")


def walk(o, nums, hits):
    if isinstance(o, dict):
        for v in o.values():
            walk(v, nums, hits)
    elif isinstance(o, list):
        for v in o:
            walk(v, nums, hits)
    elif isinstance(o, int):
        if 1_000_000_000 < o < 4_300_000_000:
            nums.append(o)
        if o in talk_ids:
            hits.add(("d", o))
        elif 100 < o and o % 100 < 50 and o // 100 in talk_ids:
            hits.add(("m", o // 100))


TALKDIR = os.path.join(ROOT, "BinOutput", "Talk")
hash_map = {}   # hash -> {talk_id, kind}
nfiles = 0
for sub in sorted(os.listdir(TALKDIR)):
    subdir = os.path.join(TALKDIR, sub)
    if os.path.isfile(subdir):
        scan_list = [(sub, subdir)]
        kind = "Free"
    else:
        scan_list = [(f, os.path.join(subdir, f))
                     for f in sorted(os.listdir(subdir)) if f.endswith(".json")]
        kind = sub
    for fname, fpath in scan_list:
        try:
            j = json.load(open(fpath, encoding="utf-8"))
        except Exception:
            continue
        nfiles += 1
        nums, hits = [], set()
        walk(j, nums, hits)
        if hits:
            direct = sorted(v for t, v in hits if t == "d")
            mode = sorted(v for t, v in hits if t == "m")
            tid = direct[0] if direct else (mode[0] if mode else None)
        else:
            tid = None
        seen = set()
        for h in nums:
            hs = str(h)
            if hs in pool and hs not in seen:
                seen.add(hs)
                hash_map[hs] = {"talk_id": tid, "kind": kind}
    if nfiles > 0 and nfiles % 5000 < 20:
        print(f"  {nfiles} 文件, {len(hash_map)} hash, {time.time()-t0:.0f}s")

print(f"扫描完成: {nfiles} 文件, {len(hash_map)} 个文本 hash 关联到 talk, {time.time()-t0:.0f}s")

rows = []
for h, e in hash_map.items():
    tid = e["talk_id"]
    qid = talk_quest.get(tid) if tid else None
    rows.append((h, tid, qid, quest_title.get(qid, ""), e["kind"]))
io.open(OUT, "w", encoding="utf-8").write(json.dumps(rows, ensure_ascii=False, indent=1))

con = sqlite3.connect(DB)
con.execute("""CREATE TABLE IF NOT EXISTS talk_map(
    hash TEXT PRIMARY KEY, talk_id INTEGER, quest_id INTEGER, quest_title TEXT, kind TEXT)""")
con.execute("DELETE FROM talk_map")
con.executemany("INSERT OR REPLACE INTO talk_map VALUES(?,?,?,?,?)", rows)
con.commit()
n = con.execute("SELECT COUNT(*) FROM talk_map").fetchone()[0]
nq = con.execute("SELECT COUNT(*) FROM talk_map WHERE quest_title != ''").fetchone()[0]
con.close()
print(f"入库 talk_map: {n} 条 (含任务名 {nq}), 耗时 {time.time()-t0:.0f}s")
