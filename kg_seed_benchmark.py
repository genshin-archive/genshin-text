# -*- coding: utf-8 -*-
"""D2-2/3: 标杆数据抽取器
从 archives/ent_*.md 解析模板字段 → kg_api 入库（走三道闸）。
解析目标（模板结构固定，见 _batches/batch_*.md）：
  # 实体档案：<主名>          → kg_entities.name
  - 实体ID：ent_NN            → ent_code
  - 类型：X                   → type_
  - 别称映射表：行格式 "别称｜出处｜置信" → kg_aliases
  - 关系/事迹行中的「引文」    → kg_claims（带 quote+hash 回查）
official_category 启发式：
  avatar 档案存在 → 自机角色；类型=神/龙/文明 → 无官方分类；
  其余 → 无官方分类（后续观测枢比对升级）
"""
import re, os, glob, sqlite3, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kg_api

ROOT = os.path.dirname(os.path.abspath(__file__))
AR = os.path.join(ROOT, "archives")

# 兹白规则：自机角色白名单（观测枢可查的名字集合——首批用 avatar 档案名代替，D2-1 拉完后再精确校正）
def avatar_names():
    return {os.path.basename(f)[len("avatar_"):-3] for f in glob.glob(os.path.join(AR, "avatar_*.md"))}

def obc_map():
    """观测枢命中表: name -> entry_page_id"""
    p = os.path.join(ROOT, "_obc_characters.json")
    if not os.path.exists(p):
        return {}
    import json
    return {r["name"]: str(r["entry_page_id"]) for r in json.load(open(p, encoding="utf-8")) if r.get("entry_page_id")}

TYPE_MAP = {"神": "神", "人": "人", "天使": "天使", "龙": "龙", "文明": "文明",
            "种族群像": "种族群像", "器灵": "器灵"}

def parse_ent_file(path, avatars):
    text = open(path, encoding="utf-8").read()
    out = {"name": None, "ent_code": None, "type": None, "aliases": [], "claims_raw": []}
    m = re.match(r"# 实体档案：(.+)", text)
    if m: out["name"] = m.group(1).strip()
    m = re.search(r"- 实体ID：\s*(ent_\d+)", text)
    if m: out["ent_code"] = m.group(1)
    m = re.search(r"- 类型：([^\n｜]+)", text)
    if m:
        t = m.group(1).strip()
        out["type"] = next((v for k, v in TYPE_MAP.items() if k in t), None)
    # 别称行：  - 别称｜出处｜置信
    for m in re.finditer(r"-\s+([^\n｜*]{1,20})｜([^｜\n]{1,80})｜(明文|推演|存疑)", text):
        alias = m.group(1).strip().lstrip("- ")
        if alias and alias != out["name"]:
            out["aliases"].append((alias, m.group(2).strip(), m.group(3)))
    # 关系/事迹行中的「引文」→ claims 原料
    for ln in re.finditer(r"^(\s*)-\s+(.+)$", text, re.M):
        line = ln.group(2).strip()
        for q in re.findall(r"「([^「」]{8,})」", line):
            # 找该行的谓词提示（带【明文】等标注的行才算断言行）
            conf = "明文" if re.search(r"【明文】|\【明文·|\(arch_|（arch_|\(talk |\（talk ", line) else None
            if conf:
                src_m = re.search(r"[\(（]((?:arch|talk|book|relic|weapon|avatar)[^\)）]{0,40})[\)）]", line)
                out["claims_raw"].append({"quote": q, "line": line[:200],
                                          "source": src_m.group(1) if src_m else os.path.basename(path),
                                          "confidence": conf})
    return out

def resolve_hash(db, quote):
    """quote → entries.hash（归一化包含回查，复用 verify_quotes 思路的单条版）"""
    qn = kg_api._norm(quote)
    probe = qn[:4]
    rows = db.execute("SELECT hash, text_zh FROM entries WHERE text_zh LIKE ? LIMIT 20", (f"%{probe}%",)).fetchall()
    for r in rows:
        if qn in kg_api._norm(r[1] or ""):
            return r[0]
    return None

def main():
    db = kg_api.get_db()
    avatars = avatar_names()
    obc = obc_map()
    files = sorted(glob.glob(os.path.join(AR, "ent_*.md")))
    print(f"待解析 ent 档案: {len(files)}")
    stats = {"entities": 0, "aliases": 0, "claims_ok": 0, "claims_noquote_hash": 0, "claims_fail": 0}
    claim_budget = 200  # D2 标杆量：够了就停（先按 ent_code 顺序，每份上限 8 条）
    for path in files:
        d = parse_ent_file(path, avatars)
        if not d["name"]:
            print("  跳过（无主名）:", os.path.basename(path)); continue
        # official_category：avatar 档案同名 → 自机角色；否则无官方分类
        base = d["name"].split("（")[0].strip()
        obc_id = obc.get(base)
        cat = "自机角色" if obc_id else "无官方分类"
        try:
            eid = kg_api.upsert_entity(db, d["name"], official_category=cat,
                                       obc_entry_id=obc_id, type_=d["type"], ent_code=d["ent_code"])
        except ValueError as e:
            print("  实体拒收:", d["name"], e); continue
        stats["entities"] += 1
        for alias, ev, conf in d["aliases"]:
            kg_api.add_alias(db, eid, alias, conf, ev); stats["aliases"] += 1
        # claims：每份档案限量，标杆期优先质
        taken = 0
        for c in d["claims_raw"]:
            if taken >= 8 or stats["claims_ok"] >= claim_budget: break
            h = resolve_hash(db, c["quote"])
            if not h:
                stats["claims_noquote_hash"] += 1
                continue
            try:
                kg_api.add_claim(db, eid, "free:parsed-relation", c["line"], source=c["source"],
                                 confidence=c["confidence"], text_hash=h, quote=c["quote"])
                stats["claims_ok"] += 1; taken += 1
            except ValueError as e:
                stats["claims_fail"] += 1
                print(f"  claim 拒收 [{d['name']}]: {e}")
    db.commit()
    print("统计:", stats)
    n = db.execute("SELECT COUNT(*) FROM kg_entities").fetchone()[0]
    print(f"kg_entities={n}")
    db.close()

if __name__ == "__main__":
    main()
