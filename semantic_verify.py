# -*- coding: utf-8 -*-
"""semantic_verify.py — 断言语义验证器（解读层质量闸）
==========================================================
背景：check_claims.py 管「事实层」（引文逐字回查），本工具管「解读层」——
断言（主语-谓词-宾语）是否忠实于引文，含时点/语境/过度归纳类错误。

用法：
  1. 生成批次
     python semantic_verify.py batch --mode pilot --n 30 --out _batches/sem_pilot.jsonl
     python semantic_verify.py batch --mode sample --n 200 --out _batches/sem_sample.jsonl
     python semantic_verify.py batch --mode p0 --out _batches/sem_p0.jsonl
       （p0 = 世界观关键词命中断言，约 800 条，自动分块 _p0_c01.jsonl …）
  2. 审核（任何法官：人工/模型/社区）读 JSONL，逐条产出：
     {"cid": 123, "verdict": "pass|fail|uncertain", "reason": "…", "fix": "可选修正"}
  3. 吸收结果
     python semantic_verify.py ingest --in _batches/sem_pilot_verdicts.jsonl --round "E1-pilot" --reviewer "zcode"
  4. 查看进展
     python semantic_verify.py stats
"""
import argparse
import json
import os
import random
import re
import sqlite3
import sys

ROOT = r"C:\AI Programs\genshin-text"
DB = os.path.join(ROOT, "genshin_text.db")

# P0 世界观关键词（错误代价最高：时间线/宇宙观级）
P0_KEYWORDS = ["降临者", "三月", "天理", "尼伯龙根", "葬火", "坎瑞亚", "深渊", "神之心",
               "月髓", "虚假之天", "天空岛", "龙王", "世界树", "星之楔", "仙灵", "妖精",
               "天使", "王座", "第一降临者", "法涅斯", "葬火之战", "原初"]

def get_con():
    con = sqlite3.connect(DB, timeout=30)
    con.row_factory = sqlite3.Row
    return con

def ensure_log_table(con):
    con.execute("""CREATE TABLE IF NOT EXISTS kg_review_log(
        rid INTEGER PRIMARY KEY,
        cid INTEGER,
        round TEXT,
        method TEXT,
        verdict TEXT,
        reason TEXT,
        fix TEXT,
        reviewer TEXT,
        created_at TEXT DEFAULT (datetime('now')))""")
    con.commit()

def fetch_context(con, quote, source):
    """按引文头部粗查邻近上下文（best-effort）"""
    if not quote or len(quote) < 6:
        return ""
    head = quote[:10].replace("「", "").replace("」", "")
    try:
        rows = con.execute(
            "SELECT text_zh FROM entries WHERE text_zh LIKE ? LIMIT 2",
            (f"%{head}%",)).fetchall()
        return " ｜ ".join((r["text_zh"] or "").replace("\n", " ")[:120] for r in rows if r["text_zh"])
    except sqlite3.Error:
        return ""

def emit_batch(con, rows, out_path, method):
    with open(out_path, "w", encoding="utf-8") as f:
        for r in rows:
            obj = {
                "cid": r["cid"], "subject": r["subj"], "predicate": r["predicate"],
                "object": r["object_text"], "quote": r["quote"] or "",
                "source": r["source"] or "", "confidence": r["confidence"],
            }
            ctx = fetch_context(con, r["quote"], r["source"])
            if ctx:
                obj["context"] = ctx
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")
    print(f"  写出 {len(rows)} 条 → {out_path}")

def cmd_batch(args):
    con = get_con()
    if args.mode == "sample":
        rows = con.execute("""
            SELECT c.cid, e.name AS subj, c.predicate, c.object_text, c.quote, c.source, c.confidence
            FROM kg_claims c JOIN kg_entities e ON e.eid=c.subject_id
            WHERE c.quote IS NOT NULL AND c.quote != ''
            ORDER BY RANDOM() LIMIT ?""", (args.n,)).fetchall()
        emit_batch(con, rows, args.out, "sample")
    elif args.mode == "pilot":
        # 固定种子，可复现
        random.seed(20261008)
        rows = con.execute("""
            SELECT c.cid, e.name AS subj, c.predicate, c.object_text, c.quote, c.source, c.confidence
            FROM kg_claims c JOIN kg_entities e ON e.eid=c.subject_id
            WHERE c.quote IS NOT NULL AND c.quote != ''
            ORDER BY c.cid""").fetchall()
        pick = random.sample(list(rows), min(args.n, len(rows)))
        emit_batch(con, pick, args.out, "pilot")
    elif args.mode == "p0":
        cond = " OR ".join([f"c.object_text LIKE '%{k}%'" for k in P0_KEYWORDS])
        rows = con.execute(f"""
            SELECT DISTINCT c.cid, e.name AS subj, c.predicate, c.object_text, c.quote, c.source, c.confidence
            FROM kg_claims c JOIN kg_entities e ON e.eid=c.subject_id
            WHERE ({cond})
            ORDER BY c.cid""").fetchall()
        # 分块，每块 100
        chunk = 100
        base = args.out.rsplit(".", 1)[0]
        for i in range(0, len(rows), chunk):
            out = f"{base}_c{i//chunk+1:02d}.jsonl"
            emit_batch(con, rows[i:i+chunk], out, "p0")
    con.close()

def cmd_ingest(args):
    con = get_con()
    ensure_log_table(con)
    n = {"pass": 0, "fail": 0, "uncertain": 0}
    with open(args.infile, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            v = d.get("verdict", "uncertain")
            n[v] = n.get(v, 0) + 1
            con.execute("""INSERT INTO kg_review_log(cid, round, method, verdict, reason, fix, reviewer)
                           VALUES(?,?,?,?,?,?,?)""",
                        (d.get("cid"), args.round, args.method, v,
                         d.get("reason", ""), d.get("fix", ""), args.reviewer))
            # 状态回写
            status = {"pass": "已复核·通过", "fail": "待修正", "uncertain": "待仲裁"}.get(v, "待仲裁")
            con.execute("UPDATE kg_claims SET review_status=? WHERE cid=?", (status, d.get("cid")))
    con.commit()
    print(f"吸收 {sum(n.values())} 条：pass {n['pass']} / fail {n['fail']} / uncertain {n['uncertain']}")
    con.close()

def cmd_stats(args):
    con = get_con()
    ensure_log_table(con)
    print("=== 复核状态分布 ===")
    for r in con.execute("SELECT review_status, COUNT(*) AS n FROM kg_claims GROUP BY review_status ORDER BY n DESC"):
        print(f"  {r['n']:6d}  {r['review_status']}")
    print("\n=== 复核轮次 ===")
    for r in con.execute("""SELECT round, reviewer, COUNT(*) AS n,
                                   SUM(verdict='pass') AS p, SUM(verdict='fail') AS f, SUM(verdict='uncertain') AS u
                            FROM kg_review_log GROUP BY round, reviewer ORDER BY MIN(rid)"""):
        print(f"  {r['round']}（{r['reviewer']}）: {r['n']} 条 → 通过 {r['p']} / 失败 {r['f']} / 存疑 {r['u']}")
    con.close()

def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")

    b = sub.add_parser("batch")
    b.add_argument("--mode", choices=["pilot", "sample", "p0"], required=True)
    b.add_argument("--n", type=int, default=100)
    b.add_argument("--out", required=True)
    b.set_defaults(func=cmd_batch)

    i = sub.add_parser("ingest")
    i.add_argument("--in", dest="infile", required=True)
    i.add_argument("--round", required=True)
    i.add_argument("--method", default="manual")
    i.add_argument("--reviewer", default="zcode")
    i.set_defaults(func=cmd_ingest)

    s = sub.add_parser("stats")
    s.set_defaults(func=cmd_stats)

    args = ap.parse_args()
    if not args.cmd:
        ap.print_help()
        return
    args.func(args)

if __name__ == "__main__":
    main()
