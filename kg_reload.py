# -*- coding: utf-8 -*-
"""Phase 3: 知识层重灌——从 881 份 narr 档案的断言表重建 kg_claims
用法: python kg_reload.py
"""
import glob, os, re, sqlite3, json, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kg_api

ROOT = os.path.dirname(os.path.abspath(__file__))

def main():
    db = kg_api.get_db()
    db.execute("PRAGMA busy_timeout=30000")
    db.execute("DELETE FROM kg_claims")
    db.execute("DELETE FROM kg_entities")
    db.execute("DELETE FROM kg_aliases")
    db.commit()

    obc = {}
    if os.path.exists(os.path.join(ROOT, "_obc_characters.json")):
        for r in json.load(open(os.path.join(ROOT, "_obc_characters.json"), encoding="utf-8")):
            if r.get("entry_page_id"):
                obc[r["name"]] = str(r["entry_page_id"])

    ent_cache = {}
    def resolve(name):
        name = (name or "").strip()
        if not name: return None
        if name in ent_cache: return ent_cache[name]
        row = db.execute("SELECT eid FROM kg_entities WHERE name=? AND status='active'", (name,)).fetchone()
        if not row:
            row = db.execute("""SELECT a.eid FROM kg_aliases a JOIN kg_entities e ON e.eid=a.eid
                                WHERE a.alias=? AND e.status='active'""", (name,)).fetchone()
        if row:
            eid = row["eid"]
        else:
            eid = kg_api.upsert_entity(db, name,
                                       official_category="自机角色" if name in obc else "无官方分类",
                                       obc_entry_id=obc.get(name), review_status="机验通过")
        ent_cache[name] = eid
        return eid

    def parse_md(path):
        t = open(path, encoding="utf-8").read()
        fm = {}
        fm_m = re.match(r"---\n(.*?)\n---", t, re.S)
        if fm_m:
            for ln in fm_m.group(1).split("\n"):
                if ":" in ln:
                    k, v = ln.split(":", 1)
                    fm[k.strip()] = v.strip()
        claims = []
        m = re.search(r"## 二、关键断言.*?\n(\|(?:[^\n]+\n)+)", t, re.S)
        if m:
            for line in m.group(1).strip().split("\n"):
                cells = [c.strip() for c in line.split("|")]
                if len(cells) >= 7 and cells[1] not in ("主语", "") and not set(cells[1]) <= {"-", " "}:
                    claims.append(cells)
        aliases = []
        m2 = re.search(r"别称映射表：\n((?:\s*[-·].*\n)+)", t)
        if m2:
            for ln in m2.group(1).strip().split("\n"):
                parts = [p.strip() for p in ln.lstrip(" -·").split("｜")]
                if len(parts) >= 3:
                    aliases.append(parts[:3])
        return fm, aliases, claims

    files = sorted(glob.glob(os.path.join(ROOT, "archives", "narr_*.md")))
    stats = {"files": 0, "entities": 0, "aliases": 0, "claims_ok": 0, "claims_skip": 0, "claims_fail": 0}
    t0 = time.time()
    for path in files:
        fm, aliases, claims = parse_md(path)
        chap = fm.get("章名") or os.path.basename(path)[5:].split("_", 1)[-1].rsplit(".", 1)[0]
        # 章节本身不建实体；实体=每条断言的主语（语义实体）
        stats["files"] += 1
        chap_eid = None
        for cells in claims:
            subj, pred, obj, conf, quote = cells[1], cells[2], cells[3], cells[4], cells[5]
            conf_base = conf.split("（")[0].strip()
            if conf_base not in ("明文", "明文·转述"):
                stats["claims_skip"] += 1
                continue
            eid = resolve(subj)
            if eid is None:
                stats["claims_skip"] += 1
                continue
            narrator = None
            cm = re.search(r"叙述者[：:]\s*([^）)]+)", conf)
            if cm: narrator = cm.group(1).strip()
            text_hash = None
            src = cells[6] if len(cells) > 6 else ""
            hm = re.search(r"hash\s*(\d{6,})", src)
            if hm: text_hash = hm.group(1)
            try:
                q = quote.strip()
                q = q[1:-1] if (q.startswith("「") and q.endswith("」")) else None
                kg_api.add_claim(db, eid,
                                 pred if pred in kg_api.PREDICATES else "free:" + pred[:16],
                                 obj[:60],
                                 source=(chap + "·" + src)[:60],
                                 confidence=conf_base,
                                 text_hash=text_hash, quote=q, narrator=narrator,
                                 skip_quote_check=True)
                stats["claims_ok"] += 1
            except ValueError:
                stats["claims_fail"] += 1
        db.commit()  # 每份提交一次
    db.commit()
    print("统计:", stats, f"耗时 {time.time()-t0:.0f}s")
    for t in ("kg_entities", "kg_aliases", "kg_claims"):
        print(f"  {t}:", db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0])
    db.close()

if __name__ == "__main__":
    main()
