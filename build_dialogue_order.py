# -*- coding: utf-8 -*-
"""dialogue_chapter 演出序重建：加 sort_key 列
依据（全部官方配置，无猜测）：
  main_seq   — 章内 mainQuest 顺序：suggestTrackMainQuestList 链贪心（官方"下一步推荐"），断链回退数字序
  talk_order — talk 触发条件 beginCond 指向的 subId 的 order（官方演出条件）；无则用 talk_id 对应 sub 的 order；再无则兜底
  doc_order  — BinOutput/Talk 对话文件内遍历序（保持不动）
sort_key = main_seq*1e12 + talk_order*1e6 + doc_order
"""
import json
import os
import sqlite3

BASE = r"C:\AI Programs\genshin-text"
ROOT = os.path.join(BASE, "AnimeGameData2")
DB = os.path.join(BASE, "genshin_text.db")

def jload(p):
    return json.load(open(p, encoding="utf-8"))

# 1) subId → (mainId, order)
qe = jload(os.path.join(ROOT, "ExcelBinOutput", "QuestExcelConfigData.json"))
sub_order, sub_main = {}, {}
for q in qe:
    sid = q.get("subId")
    if sid:
        sub_order[sid] = q.get("order", 0)
        sub_main[sid] = q.get("mainId")

# 2) mainQuest: id → suggestTrack
mq = jload(os.path.join(ROOT, "ExcelBinOutput", "MainQuestExcelConfigData.json"))
mtrack = {m.get("id"): m.get("suggestTrackMainQuestList") or [] for m in mq}

# 3) Talk 表：id → beginCond 里的候选 subId（QUEST_COND_STATE_EQUAL param[0]）
talk_rows = []
for fn in ("TalkExcelConfigData_0.json", "TalkExcelConfigData_1.json"):
    talk_rows += jload(os.path.join(ROOT, "ExcelBinOutput", fn))
talk_cond_sub = {}
for t in talk_rows:
    tid = t.get("id")
    if not tid:
        continue
    cand = []
    for cond in t.get("beginCond") or []:
        if cond.get("type") == "QUEST_COND_STATE_EQUAL":
            p0 = cond.get("param", ["", "", "", "", ""])[0]
            if p0 and str(p0).isdigit():
                n = int(p0)
                if n in sub_order:
                    cand.append((sub_order[n], n))
    talk_cond_sub[tid] = min(cand) if cand else None

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row

# 4) 章内 mainQuest 演出序：
#    优先 quest_play_order（双源互证人工录入）；未录入的章回退数字序（官方未给单一线性序，不猜）
main_seq_map = {}  # (chapter_id, quest_id) → seq
chapters = [r["chapter_id"] for r in con.execute(
    "SELECT DISTINCT chapter_id FROM dialogue_chapter WHERE chapter_id IS NOT NULL")]
manual = {(r["chapter_id"], r["quest_id"]): r["seq"]
          for r in con.execute("SELECT chapter_id, quest_id, seq FROM quest_play_order")}
from collections import defaultdict
by_chapter = defaultdict(list)
for (ch, qid), seq in manual.items():
    by_chapter[ch].append(qid)
covered_ch = set(by_chapter.keys())
n_manual = 0
for ch in chapters:
    mids = sorted({r["quest_id"] for r in con.execute(
        "SELECT DISTINCT quest_id FROM dialogue_chapter WHERE chapter_id=? AND quest_id IS NOT NULL", (ch,))})
    if ch in covered_ch:
        seqs = sorted([(manual[(ch, m)], m) for m in mids if (ch, m) in manual])
        for i, (s, m) in enumerate(seqs):
            main_seq_map[(ch, m)] = i
            n_manual += 1
        # 录入表外的 quest 挂章尾
        rest = [m for m in mids if (ch, m) not in manual]
        for j, m in enumerate(rest):
            main_seq_map[(ch, m)] = len(seqs) + j
    else:
        for i, m in enumerate(mids):
            main_seq_map[(ch, m)] = i

# 5) 重建 dialogue_chapter：加 sort_key
cur = con.cursor()
cur.execute("DROP TABLE IF EXISTS dialogue_chapter_new")
cur.execute("""CREATE TABLE dialogue_chapter_new(
    hash TEXT, quest_id INTEGER, chapter_id INTEGER,
    talk_id INTEGER, doc_order INTEGER, file_id INTEGER, sort_key REAL)""")
rows = cur.execute("SELECT hash, quest_id, chapter_id, talk_id, doc_order, file_id FROM dialogue_chapter").fetchall()
out, no_main, no_talkord = [], 0, 0
for r in rows:
    ch, qid, tid = r["chapter_id"], r["quest_id"], r["talk_id"]
    ms = main_seq_map.get((ch, qid))
    if ms is None:
        ms = 5000  # 未挂章行排最后
        no_main += 1
    to = None
    if tid in talk_cond_sub and talk_cond_sub[tid]:
        to = talk_cond_sub[tid][0]
    elif tid in sub_order:
        to = sub_order[tid]
    if to is None:
        # 无官方触发条件的 talk：排在可解析者之后，彼此按 talk_id 数字序
        to = 20000 + (tid or 0)
        no_talkord += 1
    sk = ms * 1e12 + to * 1e6 + r["doc_order"]
    out.append((r["hash"], qid, ch, tid, r["doc_order"], r["file_id"], sk))
cur.executemany("INSERT INTO dialogue_chapter_new VALUES(?,?,?,?,?,?,?)", out)
cur.execute("DROP TABLE dialogue_chapter")
cur.execute("ALTER TABLE dialogue_chapter_new RENAME TO dialogue_chapter")
cur.execute("CREATE INDEX idx_dc_ch ON dialogue_chapter(chapter_id, sort_key)")
con.commit()
print(f"重建 {len(out)} 行 | 未挂章 main_seq 兜底 {no_main} | talk_order 兜底 {no_talkord}")

# 6) 验证章 1001 前 35 行（修复后顺序）
print("\n== 章 1001 修复后前 35 行 ==")
rows = cur.execute("""
    SELECT s.speaker AS sp, e.text_zh AS t FROM (
        SELECT e2.hash AS h, MIN(dc.sort_key) AS ord
        FROM dialogue_chapter dc JOIN entries e2 ON e2.hash = dc.hash
        WHERE dc.chapter_id = 1001 GROUP BY e2.text_zh ORDER BY ord LIMIT 35) t2
    JOIN dialogue_chapter dc2 ON dc2.hash = t2.h AND dc2.sort_key = t2.ord
    JOIN entries e ON e.hash = t2.h AND e.id = (SELECT MIN(id) FROM entries WHERE hash = t2.h)
    LEFT JOIN dialogue_speaker s ON s.talk_id = dc2.talk_id AND s.hash = t2.h
    ORDER BY t2.ord""").fetchall()
for x in rows:
    print(f"  {(x['sp'] or '')}|{x['t'][:44]}".replace(chr(10), " / "))
con.close()
