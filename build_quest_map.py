# -*- coding: utf-8 -*-
"""补充扫描 BinOutput/Quest（任务文件）→ 补齐 talk_map 中缺失 hash 的任务出处"""
import json
import os
import sqlite3
import time

ROOT = r"C:\AI Programs\genshin-text\AnimeGameData2"
DB = r"C:\AI Programs\genshin-text\genshin_text.db"

t0 = time.time()
pool = set()
for fn in ("TextMapCHS.json", "TextMap_MediumCHS.json"):
    pool |= set(json.load(open(os.path.join(ROOT, "TextMap", fn), encoding="utf-8")).keys())
mq = json.load(open(os.path.join(ROOT, "ExcelBinOutput", "MainQuestExcelConfigData.json"), encoding="utf-8"))
mq_ids = {x["id"] for x in mq}
chs = json.load(open(os.path.join(ROOT, "TextMap", "TextMapCHS.json"), encoding="utf-8"))
quest_title = {}
for x in mq:
    h = str(x.get("titleTextMapHash") or "")
    if h and h in chs:
        quest_title[x["id"]] = chs[h]
print(f"pool {len(pool)}, mainQuest {len(mq_ids)}, {time.time()-t0:.0f}s")


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
        if o in mq_ids:
            hits.add(o)


QDIR = os.path.join(ROOT, "BinOutput", "Quest")
extra, nfiles = {}, 0
for fn in sorted(os.listdir(QDIR)):
    if not fn.endswith(".json"):
        continue
    try:
        j = json.load(open(os.path.join(QDIR, fn), encoding="utf-8"))
    except Exception:
        continue
    nfiles += 1
    nums, hits = [], set()
    walk(j, nums, hits)
    if not hits:
        continue
    qid = min(hits)
    for h in nums:
        hs = str(h)
        if hs in pool:
            extra.setdefault(hs, qid)
    if nfiles % 1000 == 0:
        print(f"  {nfiles} 文件, {len(extra)} hash, {time.time()-t0:.0f}s")

print(f"扫描 {nfiles} 文件, 新候选 {len(extra)} hash, {time.time()-t0:.0f}s")

con = sqlite3.connect(DB)
cur = con.cursor()
added = 0
for hs, qid in extra.items():
    # 只补 talk_map 里没有的（不覆盖已有 talk 出处）
    cur.execute(
        "INSERT OR IGNORE INTO talk_map(hash, talk_id, quest_id, quest_title, kind) VALUES(?,?,?,?,?)",
        (hs, None, qid, quest_title.get(qid, ""), "Quest"))
    added += cur.rowcount
con.commit()
n = con.execute("SELECT COUNT(*) FROM talk_map").fetchone()[0]
nq = con.execute("SELECT COUNT(*) FROM talk_map WHERE quest_title != ''").fetchone()[0]
con.close()
print(f"新增 {added} 条, talk_map 共 {n} 条 (带任务名 {nq}), 耗时 {time.time()-t0:.0f}s")
