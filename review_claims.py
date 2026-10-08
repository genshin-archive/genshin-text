# -*- coding: utf-8 -*-
"""断言复核器 v2：精准分级扫描时点敏感断言
P0 必查：关系/身份快照且带"才/刚/仅/只有"类限定（最易过时）
P1 抽查：含"现在/目前/如今/至今"+状态描述（可能过时）
P2 提示：其余含时间量词（多为历史固定事实，低风险）
"""
import re
import sqlite3

con = sqlite3.connect(r"C:\AI Programs\genshin-text\genshin_text.db")
con.row_factory = sqlite3.Row

# P0：关系快照 + 限定词（"认识才两个月"型）
P0 = re.compile(r"(才|刚|刚刚|仅|只有|最初|新)[^，。；]{0,10}(认识|相识|结伴|旅伴|朋友|成为|加入|获得|担任)|"
                r"(旅伴|朋友|同伴|搭档)[^，。；]{0,8}(才|刚|仅|只有)")

# P1：当前状态断言（"目前是/现在是/如今"）
P1 = re.compile(r"(现在|目前|如今|当前|时至今日)[^，。；]{0,14}(是|为|担任|任职|属于|效力|掌管|代理)")

# P2：其他时间量词（历史固定事实为多）
P2 = re.compile(r"[0-9一二三四五六七八九十百千万]+\s*(?:个)?(?:月|年)(?!前)")

rows = con.execute("""
    SELECT c.cid, e.name AS subj, c.object_text, c.source, c.confidence, c.as_of
    FROM kg_claims c JOIN kg_entities e ON e.eid = c.subject_id
""").fetchall()

p0, p1, p2 = [], [], []
for r in rows:
    t = r["object_text"] or ""
    if r["as_of"]:
        continue
    if P0.search(t):
        p0.append(r)
    elif P1.search(t):
        p1.append(r)
    elif P2.search(t):
        p2.append(r)

print(f"== P0 必查（关系/身份快照+限定词）: {len(p0)} 条 ==")
for r in p0[:25]:
    print(f"  [{r['cid']}] [{r['subj']}] {r['object_text'][:70]}")
print()
print(f"== P1 抽查（当前状态断言）: {len(p1)} 条 ==")
for r in p1[:20]:
    print(f"  [{r['cid']}] [{r['subj']}] {r['object_text'][:70]}")
print()
print(f"== P2 提示（时间量词，多为历史事实）: {len(p2)} 条（略）")

# 输出工单
with open(r"C:\AI Programs\genshin-text\_batches\timepoint_review_v2.md", "w", encoding="utf-8") as f:
    f.write("# 时点复核工单 v2（精准分级）\n\n")
    f.write(f"生成：2026-10-08 · P0 {len(p0)} / P1 {len(p1)} / P2 {len(p2)}\n\n")
    f.write("## P0 必查\n\n")
    for r in p0:
        f.write(f"- [ ] `{r['cid']}` **[{r['subj']}]** {r['object_text']}  \n      出处：{r['source']} · {r['confidence']}\n")
    f.write("\n## P1 抽查\n\n")
    for r in p1:
        f.write(f"- [ ] `{r['cid']}` **[{r['subj']}]** {r['object_text']}  \n      出处：{r['source']} · {r['confidence']}\n")
print()
print("工单已写入 _batches/timepoint_review_v2.md")
con.close()
