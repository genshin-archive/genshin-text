# -*- coding: utf-8 -*-
"""断言复核器：找出"时点敏感"断言（随时间变化但未标时点的内容）
分类：
  A 相对时长类（含"N个月/N年"等）
  B 关系状态类（旅伴/好友/相识等随时间变化的关系）
  C 相对时点词（才/刚/起初/首次/至今）
  D 状态描述类（当前状态词：现在/目前）
输出：分类清单供逐条回查
"""
import re
import sqlite3

con = sqlite3.connect(r"C:\AI Programs\genshin-text\genshin_text.db")
con.row_factory = sqlite3.Row

PAT_A = re.compile(r"[一二三四五六七八九十百千0-9]+\s*(?:个)?(?:月|年|天|日|周|小时)")
PAT_B = re.compile(r"(旅伴|挚友|好友|朋友|同伴|相识|认识|结伴|搭档)")
PAT_C = re.compile(r"(才|刚|初|首次|起初|最近|新近)")
PAT_D = re.compile(r"(至今|现在|目前|如今|当前)")

rows = con.execute("""
    SELECT c.cid, e.name AS subj, c.predicate, c.object_text, c.quote, c.source, c.confidence
    FROM kg_claims c JOIN kg_entities e ON e.eid = c.subject_id
""").fetchall()
print(f"断言总数: {len(rows)}")

buckets = {"A": [], "B": [], "C": [], "D": []}
for r in rows:
    t = r["object_text"] or ""
    # 已带时点限定的跳过
    if re.search(r"[（(][^)）]*时点|截至|时点[:：]", t):
        continue
    if PAT_A.search(t):
        buckets["A"].append(r)
    elif PAT_B.search(t):
        buckets["B"].append(r)
    elif PAT_C.search(t):
        buckets["C"].append(r)
    elif PAT_D.search(t):
        buckets["D"].append(r)

for k, label in [("A", "相对时长类"), ("B", "关系状态类"), ("C", "相对时点词类"), ("D", "状态词类")]:
    print(f"\n=== {k} {label}: {len(buckets[k])} 条 ===")
    for r in buckets[k][:12]:
        print(f"  [{r['subj']}] {r['object_text'][:65]} | {r['source'][:35]}")

con.close()
