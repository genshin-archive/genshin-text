# -*- coding: utf-8 -*-
"""重建对话顺序与多归属 v2：扫描 BinOutput/Talk → dialogue_seq 表
   输出：dialogue_seq(hash, talk_id, kind, file_id, doc_order) —— 保留叙事顺序、允许一个 hash 归属多个 talk
   browse 排序：quest_id → talk_id → doc_order
"""
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
print(f"pool {len(pool)}, {time.time()-t0:.0f}s")

talk_rows = []
for fn in ("TalkExcelConfigData_0.json", "TalkExcelConfigData_1.json"):
    talk_rows += json.load(open(os.path.join(ROOT, "ExcelBinOutput", fn), encoding="utf-8"))
talk_ids = {x["id"] for x in talk_rows if x.get("id")}

# 低段 TextMap hash（<1e9）精确集合——值域过滤会漏掉这 20 万个合法 hash
import json as _json
LOW_HASH = set(_json.load(open("low_hash_pool.json")))


def walk(o, nums, tids, doc):
    """doc 计数器模拟文档顺序；nums=[(hash,doc)], tids=[(talk_id,doc)]
    talk_id 判定优先级：talkId*100+句序模式（可靠） > 直接命中（易被小整数污染，仅兜底）"""
    if isinstance(o, dict):
        for v in o.values():
            walk(v, nums, tids, doc)
    elif isinstance(o, list):
        for v in o:
            walk(v, nums, tids, doc)
    elif isinstance(o, int):
        doc[0] += 1
        if 1_000_000_000 < o < 4_300_000_000:
            nums.append((str(o), doc[0]))
        elif o < 1_000_000_000 and o > 1000 and str(o) in LOW_HASH:
            nums.append((str(o), doc[0]))
        elif o >= 10000 and o % 100 < 50 and o // 100 in talk_ids:
            tids.append((o // 100, doc[0]))
        elif o >= 10000 and o in talk_ids:
            tids.append((o, doc[0]))


TALKDIR = os.path.join(ROOT, "BinOutput", "Talk")
records = []
nfiles = 0
file_id = 0
for sub in sorted(os.listdir(TALKDIR)):
    subdir = os.path.join(TALKDIR, sub)
    if os.path.isfile(subdir):
        scan_list = [(subdir, "Free")]
    else:
        scan_list = [(os.path.join(subdir, f), sub)
                     for f in sorted(os.listdir(subdir)) if f.endswith(".json")]
    for fpath, kind in scan_list:
        try:
            j = json.load(open(fpath, encoding="utf-8"))
        except Exception:
            continue
        nfiles += 1
        file_id += 1
        nums, tids, doc = [], [], [0]
        walk(j, nums, tids, doc)
        tid = None
        # 修复 v2.1：优先读文件顶层明文 talkId 字段（Quest 类对话流自带）；
        # 无则兜底取 doc_order 最早的 talk 声明（文件开头最可靠）——旧"取值最小"会让
        # 文件内其他撞库数字（如 101003）抢走归属（603403.json 错并进璃月 quest1010 即此因）
        if isinstance(j, dict) and isinstance(j.get("talkId"), int):
            tid = j["talkId"]
        elif tids:
            first = min(tids, key=lambda tv: (tv[1], tv[0]))
            tid = first[0]
        seen = set()
        for hs, order in nums:
            if hs in pool and hs not in seen:
                seen.add(hs)
                records.append((hs, tid, kind, file_id, order))
    if nfiles and nfiles % 8000 < 30:
        print(f"  {nfiles} 文件, {len(records)} 记录, {time.time()-t0:.0f}s")

print(f"扫描 {nfiles} 文件, {len(records)} 记录, {time.time()-t0:.0f}s")

con = sqlite3.connect(DB)
cur = con.cursor()
cur.execute("""CREATE TABLE IF NOT EXISTS dialogue_seq(
    hash TEXT, talk_id INTEGER, kind TEXT, file_id INTEGER, doc_order INTEGER,
    PRIMARY KEY(hash, talk_id, file_id))""")
cur.execute("DELETE FROM dialogue_seq")
cur.executemany("INSERT OR REPLACE INTO dialogue_seq VALUES(?,?,?,?,?)", records)
con.commit()

n = cur.execute("SELECT COUNT(*) FROM dialogue_seq").fetchone()[0]
nm = cur.execute("SELECT COUNT(DISTINCT hash) FROM dialogue_seq").fetchone()[0]
con.close()
print(f"dialogue_seq 入库: {n} 行, 覆盖 {nm} 个 hash, 总耗时 {time.time()-t0:.0f}s")
