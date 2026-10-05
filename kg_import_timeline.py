# -*- coding: utf-8 -*-
"""D3: timeline.md v2.3 → kg_eras + kg_timeline_nodes（Q10 两级结构）
解析规则：'## ' 级且含纪元词 → era；era 内 '- ' 首层 bullet → node（限 400 字/条）。
narrative_mode 从行内标注【明文·回忆】等提取；axes 暂置空（多轴标注在 v2.3 内联，后续补）。
"""
import re, os, sqlite3, sys, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kg_api

ROOT = os.path.dirname(os.path.abspath(__file__))

ERA_PAT = re.compile(r"^##\s+(.+)$")
ERA_KEYWORDS = ("纪元", "时期", "之战", "现代", "月亮倒影")

MODE_PAT = re.compile(r"【(明文(?:·[^】]+)?|回忆|预言|倒流|改写|叠加|矛盾对|应验)】")

def main():
    text = open(os.path.join(ROOT, "timeline.md"), encoding="utf-8").read()
    lines = text.split("\n")
    db = kg_api.get_db()
    db.execute("DELETE FROM kg_timeline_nodes")
    db.execute("DELETE FROM kg_eras")

    cur_era = None
    era_order = 0
    node_order = 0
    stats = {"eras": 0, "nodes": 0, "with_quote": 0, "skipped_long": 0}
    buffer = None  # (title, detail_lines)

    def flush_node():
        nonlocal node_order, buffer
        if not buffer or cur_era is None:
            buffer = None
            return
        title, dlines = buffer
        body = "\n".join(dlines).strip()
        if not body or len(body) < 10:
            buffer = None
            return
        if len(body) > 500:
            stats["skipped_long"] += 1
            buffer = None
            return
        m = MODE_PAT.search(title + " " + body[:200])
        mode = m.group(1) if m else "明文"
        # 首个「引文」回查 hash
        q = None; h = None
        qm = re.search(r"「([^「」]{8,60})」", body)
        if qm:
            qn = kg_api._norm(qm.group(1))
            rows = db.execute("SELECT hash, text_zh FROM entries WHERE text_zh LIKE ? LIMIT 10",
                              (f"%{qn[:6]}%",)).fetchall()
            for r in rows:
                if qn in kg_api._norm(r[1] or ""):
                    h, q = r[0], qm.group(1)
                    stats["with_quote"] += 1
                    break
        db.execute("""INSERT INTO kg_timeline_nodes(era_id, title, detail, text_hash, quote, source,
                      narrative_mode, ord) VALUES(?,?,?,?,?,?,?,?)""",
                   (cur_era, title[:120], body, h, q, "timeline.md v2.3", mode, node_order))
        node_order += 1
        stats["nodes"] += 1
        buffer = None

    for ln in lines:
        m = ERA_PAT.match(ln)
        if m:
            title = m.group(1).strip()
            flush_node()
            if any(k in title for k in ERA_KEYWORDS) and not title.startswith(("【", "主线", "时间异常", "待定位", "书籍隐喻", "非线性时间")):
                era_order += 1
                cur_era = db.execute("INSERT INTO kg_eras(name, ord, source) VALUES(?,?,?)",
                                     (title, era_order, "timeline.md v2.3")).lastrowid
                stats["eras"] += 1
            continue
        if cur_era is None:
            continue
        if re.match(r"- ", ln):
            flush_node()
            buffer = [ln.lstrip("- ").strip()[:100], [ln.lstrip("- ").strip()]]
            flush_node()  # 单行 bullet 直接入库
        elif buffer is not None:
            if ln.startswith("  ") or (ln and not ln.startswith(("#", "##", "###"))):
                buffer[1].append(ln.strip())
                flush_node()
            else:
                flush_node()
    flush_node()
    db.commit()
    print("统计:", stats)
    for r in db.execute("SELECT era_id, name, ord FROM kg_eras ORDER BY ord"):
        n = db.execute("SELECT COUNT(*) FROM kg_timeline_nodes WHERE era_id=?", (r[0],)).fetchone()[0]
        print(f"  [{r[2]}] {r[1]}: {n} nodes")
    db.close()

if __name__ == "__main__":
    main()
