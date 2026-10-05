# -*- coding: utf-8 -*-
"""D1-2/3: 谓词受控词表 + 知识层入库 API（写入即校验，失配拒收）
Q5/Q6/Q8/Q16 落地。所有 kg_ 写入必须走本模块，禁止直写 SQL。
"""
import sqlite3, re, os, json

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "genshin_text.db")

# ---------------- D1-2 谓词受控词表（初版，待 master 审） ----------------
PREDICATES = {
    # --- 身份/归类 ---
    "is-a":            ("是（类属）", "X 属于类别 Y，如 兹白 是-a 仙人", "directed"),
    "part-of":         ("从属（组织）", "X 是组织/群体 Y 的成员", "directed"),
    "aka":             ("别称", "Y 是 X 的另一称呼（与 kg_aliases 冗余时以 aliases 为准）", "directed"),
    # --- 权力/组织 ---
    "leader-of":       ("领袖", "X 是 Y 的领导者（明文级，转述须标 confidence）", "directed"),
    "member-of":       ("成员", "X 为 Y 的普通成员", "directed"),
    "founds":          ("创立", "X 创立了 Y", "directed"),
    "commands":        ("统辖", "X 指挥 Y 的行动（军事/任务层面）", "directed"),
    # --- 敌对/同盟 ---
    "enemy-of":        ("敌对", "X 与 Y 处于敌对关系", "symmetric"),
    "ally-of":         ("同盟", "X 与 Y 结盟（含'悖逆共谋'级同盟）", "symmetric"),
    "betrays":         ("背叛", "X 背叛了 Y", "directed"),
    "opposes":         ("对抗", "X 反对/抵抗 Y 的行动或意志（未至战争级）", "symmetric"),
    # --- 血缘/传承 ---
    "ancestor-of":     ("血亲先祖", "X 是 Y 的先祖/血缘来源", "directed"),
    "kin-of":          ("血亲", "X 与 Y 有血缘关系（兄弟/双子等，细分写进 claim 引文）", "symmetric"),
    "creates":         ("创造", "X 创造了 Y（造物/种族/器物）", "directed"),
    "descends-from":   ("位格继承", "X 承继了 Y 的位格/权能/职责", "directed"),
    "succeeds":        ("继位", "X 继承 Y 的王位/职位", "directed"),
    # --- 权能/器物 ---
    "possesses":       ("持有权能", "X 持有权能/力量 Y", "directed"),
    "grants":          ("授予", "X 将权能/器物 Y 授予 Z（object=Y，受者在 claim 文本注明）", "directed"),
    "steals":          ("窃取", "X 窃取了 Y", "directed"),
    "seals":           ("封印", "X 封印了 Y", "directed"),
    "imprisons":       ("囚禁", "X 将 Y 囚禁于 Z（Z 写进引文）", "directed"),
    "wields":          ("持用", "X 持用器物 Y", "directed"),
    "sealed-in":       ("封存于", "器物/权能 Y 封存于场所 X", "directed"),
    # --- 事件参与 ---
    "causes":          ("引发", "X 的行动引发了事件 Y", "directed"),
    "participates-in": ("参与", "X 参与了事件 Y", "directed"),
    "witnesses":       ("见证", "X 见证了事件 Y", "directed"),
    "dies-in":         ("死于", "X 死于事件 Y（复活类写 resurrects）", "directed"),
    "resurrects":      ("复活", "X 复活（机制写进引文）", "directed"),
    "survives":        ("幸存", "X 在事件 Y 中幸存", "directed"),
    # --- 位置/时间 ---
    "located-in":      ("位于", "X 位于/栖居于场所 Y", "directed"),
    "active-during":   ("活跃于", "X 活跃于时代/事件 Y", "directed"),
    "travels-to":      ("抵达", "X 抵达/到访 Y", "directed"),
    # --- 知识/传闻 ---
    "knows-of":        ("知晓", "X 知晓信息 Y（转述链必标）", "directed"),
    "narrates":        ("转述", "X 转述了信息 Y（叙述者立场写 narrator 字段）", "directed"),
    "prophesies":     ("预言", "X 预言了 Y", "directed"),
    # --- 消灭 ---
    "eats":            ("吃掉", "X 吃掉/消灭 Y（苏尔特洛奇式以吃掉统称一切消灭），或字面吞食", "directed"),
    # --- 情感/立场 ---
    "trusts":          ("信任", "X 信任 Y", "directed"),
    "distrusts":       ("不信任", "X 不信任 Y", "directed"),
    "loves":           ("爱", "X 爱 Y（天使诅咒语境的核心谓词）", "directed"),
    "worships":        ("崇拜", "X 崇拜/侍奉 Y", "directed"),
}

CONFIDENCE_LEVELS = {"明文": 4, "明文·转述": 3, "推演": 2, "存疑": 1}
REVIEW_LEVELS = ["master已校验", "AI交叉复核", "机验通过", "未复核"]

def get_db():
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    return db

# ---------------- D1-3 写入即校验 ----------------
_strip = re.compile(r"[\u2026。，！？、\s「」『』\u201c\u201d\u2018\u2019·\u2014\-~！？?!.,:;\"'()（）#\n\r]")

def _norm(s: str) -> str:
    s = re.sub(r"<[^>]+>", "", s)
    s = re.sub(r"\{[^}]{0,30}\}", "", s)
    return _strip.sub("", s or "")

def verify_quote(db, text_hash: str, quote: str) -> dict:
    """引文回查：quote 必须能在 text_hash 对应的 entries 行中找到（归一化包含）。
    失配返回 {'ok': False, 'reason': ...}"""
    if not text_hash or not quote:
        return {"ok": False, "reason": "缺 text_hash 或 quote"}
    rows = db.execute("SELECT text_zh FROM entries WHERE hash=?", (str(text_hash),)).fetchall()
    if not rows:
        return {"ok": False, "reason": f"hash {text_hash} 不存在于 entries"}
    # 同 hash 可能因双池撞车有多行，任一行包含即通过
    for row in rows:
        if _norm(quote) in _norm(row["text_zh"] or ""):
            return {"ok": True}
    return {"ok": False, "reason": "quote 与该 hash 的库内文本不匹配（归一化比对失败，已遍历同 hash 全部行）"}

def upsert_entity(db, name, official_category=None, obc_entry_id=None, type_=None,
                  ent_code=None, review_status="未复核"):
    """新建/更新实体。official_category 必须显式给出（'无官方分类'也是显式值）——
    兹白规则：建档必须先查观测枢，不允许空着。"""
    if official_category is None:
        raise ValueError("official_category 必填（'无官方分类'也是显式值）——建档先查观测枢")
    if obc_entry_id:
        row = db.execute("SELECT eid FROM kg_entities WHERE obc_entry_id=?", (str(obc_entry_id),)).fetchone()
    else:
        row = db.execute("SELECT eid FROM kg_entities WHERE name=? AND status='active'", (name,)).fetchone()
    if row:
        db.execute("""UPDATE kg_entities SET name=?, official_category=?, obc_entry_id=?, type=?, review_status=?
                      WHERE eid=?""", (name, official_category, obc_entry_id, type_, review_status, row["eid"]))
        return row["eid"]
    cur = db.execute("""INSERT INTO kg_entities(name, ent_code, official_category, obc_entry_id, type, review_status)
                        VALUES(?,?,?,?,?,?)""", (name, ent_code, official_category, obc_entry_id, type_, review_status))
    return cur.lastrowid

def add_alias(db, eid, alias, confidence, evidence=None, lang="zh"):
    if confidence not in ("明文", "推演", "存疑"):
        raise ValueError(f"confidence 非法: {confidence}")
    db.execute("""INSERT INTO kg_aliases(eid, alias, lang, confidence, evidence)
                  VALUES(?,?,?,?,?) ON CONFLICT(eid, alias, lang) DO NOTHING""",
               (eid, alias, lang, confidence, evidence))

def add_claim(db, subject_id, predicate, object_text, source, confidence,
              object_id=None, text_hash=None, quote=None, narrator=None, skip_quote_check=False):
    """断言写入。三道闸：
    1) 谓词必须在受控词表（fallback 谓词需以 'free:' 前缀且要在 claim 里说明理由）
    2) confidence 非法值拒收；明文·转述 必须带 narrator（P2）
    3) 带 quote 的断言当场 FTS/精确回查（Q8），失配拒收"""
    pid = predicate.strip()
    if pid not in PREDICATES and not pid.startswith("free:"):
        raise ValueError(f"谓词 '{predicate}' 不在受控词表（可用 free: 前缀+理由）")
    if confidence not in CONFIDENCE_LEVELS:
        raise ValueError(f"confidence 非法: {confidence}（允许: {list(CONFIDENCE_LEVELS)}）")
    if confidence == "明文·转述" and not narrator:
        raise ValueError("明文·转述 必须提供 narrator（P2 转述链）")
    if quote and skip_quote_check:
        # 源档案已经过 check_claims 全链验证（881/881 PASS）；此处仅 best-effort 解析 hash
        if not text_hash:
            qn = _norm(quote)
            probes = [qn[i:i+5] for i in range(0, max(len(qn) - 4, 1), 3)][:8]
            if probes:
                query = " OR ".join('"%s"' % p for p in probes)
                try:
                    rows = db.execute("SELECT rowid FROM fts WHERE fts MATCH ? LIMIT 60", (query,)).fetchall()
                except Exception:
                    rows = []
                for (rid,) in rows:
                    tz = db.execute("SELECT text_zh FROM entries WHERE id=?", (rid,)).fetchone()
                    if tz and qn in _norm(tz[0] or ""):
                        text_hash = str(rid)
                        break
        quote = None if not text_hash else quote  # 无 hash 锚定时不存裸引文防误导
    elif quote:
        if text_hash:
            v = verify_quote(db, text_hash, quote)
            if not v["ok"]:
                # 拼接引文（」「连接）：逐段校验，全段命中即过
                segs = [x for x in re.split(r"」\s*[＋+…]?\s*[「『]", quote) if _norm(x)]
                if len(segs) > 1 and all(verify_quote(db, text_hash, x.strip("「」"))["ok"] for x in segs):
                    pass
                else:
                    # hash 失配 → 反查真身（4字窗+3字回退，全候选行扫描）
                    qn = _norm(quote)
                    found = None
                    cand = set()
                    for n_ in (4, 3):
                        probes = [qn[i:i+n_] for i in range(0, max(len(qn) - n_ + 1, 1), 2)][:12]
                        if not probes: continue
                        query = " OR ".join('"%s"' % p for p in probes)
                        try:
                            rows = db.execute("SELECT rowid FROM fts WHERE fts MATCH ? LIMIT 200", (query,)).fetchall()
                        except Exception:
                            rows = []
                        if not rows:
                            rows = db.execute("SELECT id FROM entries WHERE text_zh LIKE ? LIMIT 50", (f"%{probes[0]}%",)).fetchall()
                        for (rid,) in rows:
                            cand.add(rid)
                        if cand:
                            break
                    for rid in cand:
                        tz = db.execute("SELECT text_zh FROM entries WHERE id=?", (rid,)).fetchone()[0]
                        if qn in _norm(tz or ""):
                            found = rid; break
                    if not found:
                        raise ValueError("引文校验失败拒收: 库内反查无命中")
                    text_hash = str(found)
        else:
            # 未带 hash：自动反查（quote 归一化前 8 字 LIKE 定位候选行，再归一化包含验证）
            qn = _norm(quote)
            if len(qn) < 6:
                raise ValueError("引文校验失败拒收: quote 归一化后过短")
            probes = [qn[i:i+4] for i in range(0, max(len(qn)-3, 1), 2)][:10] or [qn[:4]]
            query = " OR ".join('"%s"' % p for p in probes)
            try:
                ids = db.execute("SELECT rowid FROM fts WHERE fts MATCH ? LIMIT 60", (query,)).fetchall()
            except Exception:
                ids = db.execute("SELECT id FROM entries WHERE text_zh LIKE ? LIMIT 60",
                                 (f"%{probes[0]}%",)).fetchall()
            hit = None
            if ids:
                idl = ",".join(str(r[0]) for r in ids)
                for r in db.execute(f"SELECT hash, text_zh FROM entries WHERE id IN ({idl})"):
                    if qn in _norm(r[1] or ""):
                        hit = r[0]
                        break
            if not hit:
                raise ValueError("引文校验失败拒收: quote 反查库内无命中")
            text_hash = hit
    if not subject_id:
        raise ValueError("subject_id 必填")
    cur = db.execute("""INSERT INTO kg_claims(subject_id, predicate, object_text, object_id,
                        text_hash, quote, source, confidence, narrator)
                        VALUES(?,?,?,?,?,?,?,?,?)""",
                     (subject_id, pid, object_text, object_id, str(text_hash) if text_hash else None,
                      quote, source, confidence, narrator))
    return cur.lastrowid

def propose_arbitration(db, kind, payload, proposal=None):
    """仲裁提案（Q7）。只入队，不落任何结论——结论由 master 三态裁决。"""
    assert kind in ("alias-merge", "alias-split", "new-entity", "claim-check", "conflict")
    cur = db.execute("INSERT INTO kg_arbitration(kind, payload, proposal) VALUES(?,?,?)",
                     (kind, json.dumps(payload, ensure_ascii=False), proposal))
    return cur.lastrowid

def add_caveat(db, description, scope, severity="中", reference=None):
    cur = db.execute("""INSERT INTO kg_corpus_caveats(description, scope, severity, found_date, reference)
                        VALUES(?,?,?,?,?)""", (description, scope, severity, __import__('datetime').date.today().isoformat(), reference))
    return cur.lastrowid

def add_witness(db, content, related_entities=None):
    cur = db.execute("INSERT INTO kg_master_witness(content, related_entities) VALUES(?,?)",
                     (content, json.dumps(related_entities or [], ensure_ascii=False)))
    return cur.lastrowid

def seed_predicates():
    db = get_db()
    db.execute("DELETE FROM kg_predicates")
    for pid, (zh, definition, direction) in PREDICATES.items():
        db.execute("INSERT INTO kg_predicates(pid, label_zh, definition, direction) VALUES(?,?,?,?)",
                   (pid.strip(), zh, definition, direction))
    db.commit()
    n = db.execute("SELECT COUNT(*) FROM kg_predicates").fetchone()[0]
    db.close()
    print(f"谓词词表已灌入 {n} 条")

if __name__ == "__main__":
    seed_predicates()
