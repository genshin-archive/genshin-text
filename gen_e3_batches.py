# -*- coding: utf-8 -*-
"""E3 全量批次生成：未复核断言 → 每 200 条一块
输出 _batches/e3_cXXX.jsonl（输入）供子代理审核
"""
import json
import os
import sqlite3

ROOT = r"C:\AI Programs\genshin-text"
OUT_DIR = os.path.join(ROOT, "_batches")
CHUNK = 200

con = sqlite3.connect(os.path.join(ROOT, "genshin_text.db"), timeout=30)
con.row_factory = sqlite3.Row

rows = con.execute("""
    SELECT c.cid, e.name AS subj, c.predicate, c.object_text, c.quote, c.source, c.confidence
    FROM kg_claims c JOIN kg_entities e ON e.eid=c.subject_id
    WHERE c.review_status='未复核'
    ORDER BY c.cid""").fetchall()
print(f"未复核: {len(rows)} 条")

n_chunks = 0
for i in range(0, len(rows), CHUNK):
    n_chunks += 1
    out = os.path.join(OUT_DIR, f"e3_c{n_chunks:03d}.jsonl")
    if os.path.exists(out):
        continue
    with open(out, "w", encoding="utf-8") as f:
        for r in rows[i:i+CHUNK]:
            obj = {
                "cid": r["cid"], "subject": r["subj"], "predicate": r["predicate"],
                "object": r["object_text"], "quote": r["quote"] or "",
                "source": r["source"] or "", "confidence": r["confidence"],
            }
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")
print(f"批次: {n_chunks} 块（每块 {CHUNK} 条）→ {OUT_DIR}\\e3_c*.jsonl")
con.close()
