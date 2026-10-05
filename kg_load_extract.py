# -*- coding: utf-8 -*-
"""D5 灌库器：kg_extract_batch*.json → kg_ 表（统一走 kg_api 三道闸）
subject 名解析：kg_entities 主名 → 别名 → 新建（official_category 按观测枢表，查不到='无官方分类'）
拒收记录：_batches/load_rejected.json（供人工复核）
"""
import os, glob, json, sqlite3, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kg_api

ROOT = os.path.dirname(os.path.abspath(__file__))

def load_obc():
    p = os.path.join(ROOT, "_obc_characters.json")
    if not os.path.exists(p):
        return {}
    return {r["name"]: str(r["entry_page_id"]) for r in json.load(open(p, encoding="utf-8")) if r.get("entry_page_id")}

def main():
    db = kg_api.get_db()
    obc = load_obc()
    # 实体解析缓存
    ent_cache = {}  # name -> eid or None
    def resolve_or_create(name):
        name = (name or "").strip()
        if not name:
            return None
        if name in ent_cache:
            return ent_cache[name]
        row = db.execute("SELECT eid FROM kg_entities WHERE name=? AND status='active'", (name,)).fetchone()
        if not row:
            row = db.execute("""SELECT a.eid FROM kg_aliases a JOIN kg_entities e ON e.eid=a.eid
                                WHERE a.alias=? AND e.status='active'""", (name,)).fetchone()
        if row:
            eid = row["eid"]
        else:
            obc_id = obc.get(name)
            eid = kg_api.upsert_entity(db, name,
                                       official_category="自机角色" if obc_id else "无官方分类",
                                       obc_entry_id=obc_id, review_status="未复核")
        ent_cache[name] = eid
        return eid

    stats = {"files": 0, "claims": 0, "ok": 0, "no_subject": 0, "rej_quote": 0, "rej_other": 0,
             "new_entities": 0, "alias_rows": 0}
    rejected = []
    before_e = db.execute("SELECT COUNT(*) FROM kg_entities").fetchone()[0]

    for f in sorted(glob.glob(os.path.join(ROOT, "kg_extract_batch*.json"))):
        try:
            data = json.load(open(f, encoding="utf-8"))
        except Exception as e:
            print("跳过坏文件:", f, e)
            continue
        if not isinstance(data, list):
            continue
        for it in data:
            stats["claims"] += 1
            subj = (it.get("subject") or "").strip()
            if not subj:
                stats["no_subject"] += 1
                continue
            eid = resolve_or_create(subj)
            if eid is None:
                stats["no_subject"] += 1
                continue
            # 别名记录（抽取器的 alias 字段=三段式）
            if it.get("alias"):
                parts = it["alias"].split("｜")
                if len(parts) >= 2:
                    try:
                        kg_api.add_alias(db, eid, parts[0].strip()[:40],
                                         parts[-1].strip() if parts[-1].strip() in ("明文","推演","存疑") else "存疑",
                                         parts[1].strip()[:80])
                        stats["alias_rows"] += 1
                    except ValueError:
                        pass
            pred = (it.get("predicate_hint") or "free").strip()
            if pred not in kg_api.PREDICATES:
                pred = "free:" + pred[:20]
            conf = (it.get("confidence") or "存疑").strip()
            if conf not in kg_api.CONFIDENCE_LEVELS:
                conf = "存疑"
            try:
                kg_api.add_claim(db, eid, pred, (it.get("object_text") or "")[:80],
                                 source=(it.get("source") or it.get("file") or "")[:60],
                                 confidence=conf,
                                 object_id=None,
                                 text_hash=None,   # 抽取器不带 hash，quote 可解析时由下轮批量补
                                 quote=it.get("quote"),
                                 narrator=it.get("narrator"))
                stats["ok"] += 1
            except ValueError as e:
                msg = str(e)
                if "引文校验失败" in msg:
                    stats["rej_quote"] += 1
                    rejected.append({"file": it.get("file"), "subject": subj, "quote": (it.get("quote") or "")[:60], "why": msg})
                else:
                    stats["rej_other"] += 1
                    if stats["rej_other"] <= 10:
                        rejected.append({"file": it.get("file"), "subject": subj, "why": msg})
        stats["files"] += 1
    db.commit()
    after_e = db.execute("SELECT COUNT(*) FROM kg_entities").fetchone()[0]
    stats["new_entities"] = after_e - before_e
    json.dump(rejected, open(os.path.join(ROOT, "_batches", "load_rejected.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("统计:", stats)
    n = db.execute("SELECT COUNT(*) FROM kg_claims").fetchone()[0]
    print("kg_claims 总数:", n)
    db.close()

if __name__ == "__main__":
    main()
