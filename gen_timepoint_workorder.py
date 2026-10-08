# -*- coding: utf-8 -*-
"""生成时点复核工单：按档案分组的高危断言清单（人工/模型逐条核对）
输出 _batches/timepoint_review.md
"""
import re
import sqlite3

con = sqlite3.connect(r"C:\AI Programs\genshin-text\genshin_text.db")
con.row_factory = sqlite3.Row

# 高危模式（只留真的会随时间失效的）
HIGH = [
    ("时长类", re.compile(r"认识才|相识.{0,6}[0-9一二三四五六七八九十]+\s*个?月|才认识|刚认识|初遇.{0,10}(时|才)")),
    ("关系快照", re.compile(r"(旅伴|最好的朋友|挚友).{0,12}(才|刚|初|仅|只有)|(才|刚|初|仅|只有).{0,8}(旅伴|朋友)")),
    ("临时状态", re.compile(r"临时(?!收容|居住|安置)|暂(?!停|时)[代为]?(任|代|由)|过渡期")),
]

rows = con.execute("""
    SELECT c.cid, e.name AS subj, c.object_text, c.source, c.confidence, c.as_of
    FROM kg_claims c JOIN kg_entities e ON e.eid = c.subject_id
""").fetchall()

hits = []
for r in rows:
    t = r["object_text"] or ""
    if r["as_of"]:
        continue
    for label, pat in HIGH:
        if pat.search(t):
            hits.append((label, r))
            break

# 输出工单
with open(r"C:\AI Programs\genshin-text\_batches\timepoint_review.md", "w", encoding="utf-8") as f:
    f.write("# 时点复核工单（高危断言）\n\n")
    f.write(f"生成时间：2026-10-08 · 命中 {len(hits)} 条\n\n")
    f.write("复核方式：对每条断言，回查原文是否依赖说话时点；若是，在宾语加「（时点：XXX）」或降级。\n\n")
    cur_label = None
    for label, r in hits:
        if label != cur_label:
            f.write(f"\n## {label}\n\n")
            cur_label = label
        f.write(f"- [ ] `{r['cid']}` **[{r['subj']}]** {r['object_text']}  \n")
        f.write(f"      出处：{r['source']} · {r['confidence']}\n")

print(f"工单已生成：{len(hits)} 条待复核")
for label in set(l for l, _ in hits):
    n = sum(1 for l, _ in hits if l == label)
    print(f"  {label}: {n}")
con.close()
