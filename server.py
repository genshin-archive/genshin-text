# -*- coding: utf-8 -*-
"""原神文本资料库 — 本地查询服务 (FastAPI + SQLite FTS5 trigram)"""
import os
import sqlite3
import time

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, JSONResponse

BASE = os.environ.get("GENSHIN_BASE", os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "genshin_text.db")
INDEX = os.path.join(BASE, "index.html")
ARCHIVES = os.path.join(BASE, "archives")
PER_PAGE = 20

app = FastAPI(title="原神文本资料库")


def db():
    con = sqlite3.connect(DB, check_same_thread=False)
    con.row_factory = sqlite3.Row
    return con


@app.get("/")
def home():
    return FileResponse(INDEX, media_type="text/html; charset=utf-8")


@app.get("/theme.css")
def theme_css():
    return FileResponse(os.path.join(BASE, "theme.css"), media_type="text/css; charset=utf-8")


@app.get("/index.html")
def home_alias():
    return FileResponse(INDEX, media_type="text/html; charset=utf-8")


@app.get("/browse.html")
def browse_page():
    return FileResponse(os.path.join(BASE, "browse.html"), media_type="text/html; charset=utf-8")


@app.get("/timeline.html")
def timeline_page():
    return FileResponse(os.path.join(BASE, "timeline.html"), media_type="text/html; charset=utf-8")


@app.get("/archive.html")
def archive_page():
    return FileResponse(os.path.join(BASE, "archive.html"), media_type="text/html; charset=utf-8")


@app.get("/hypothesis.html")
def hypothesis_page():
    return FileResponse(os.path.join(BASE, "hypothesis.html"), media_type="text/html; charset=utf-8")


@app.get("/api/timeline")
def timeline_api():
    """兼容路由：旧 v1.6 结构化表已冻结，转发到 v3 数据（kg_eras + kg_timeline_nodes）"""
    return kg_timeline()


@app.get("/api/timeline_legacy")
def timeline_api_legacy():
    con = db()
    axes = con.execute("SELECT * FROM time_axes ORDER BY axis_id").fetchall()
    ev_rows = con.execute("SELECT * FROM events ORDER BY event_id").fetchall()
    amap = con.execute("SELECT * FROM event_axis_map").fetchall()
    links = con.execute("""
        SELECT l.link_id, l.relation, l.note,
               a.event_id AS from_id, a.title AS from_title,
               b.event_id AS to_id, b.title AS to_title
        FROM event_links l
        JOIN events a ON a.event_id = l.from_event
        JOIN events b ON b.event_id = l.to_event""").fetchall()
    metaphors = con.execute("SELECT * FROM metaphors ORDER BY id").fetchall()
    con.close()
    pos = {}
    for r in amap:
        pos.setdefault(r["event_id"], []).append({"axis": r["axis_id"], "position": r["position"]})
    events = []
    for r in ev_rows:
        events.append({"id": r["event_id"], "title": r["title"], "detail": r["detail"],
                       "mode": r["narrative_mode"], "evidence": r["evidence"],
                       "source": r["source"], "axes": pos.get(r["event_id"], [])})
    return JSONResponse({
        "axes": [dict(r) for r in axes],
        "events": events,
        "links": [dict(r) for r in links],
        "metaphors": [dict(r) for r in metaphors],
    })


@app.get("/api/hypothesis/list")
def hypothesis_list():
    items = []
    path = os.path.join(BASE, "hypothesis.md")
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            content = f.read()
        items.append({"file": "hypothesis.md", "title": "假说库（全部）"})
    return JSONResponse({"items": items})


@app.get("/api/hypothesis/get")
def hypothesis_get(file: str = Query(...)):
    safe = os.path.basename(file)
    if safe != "hypothesis.md":
        return JSONResponse({"error": "bad file"}, status_code=400)
    path = os.path.join(BASE, safe)
    if not os.path.isfile(path):
        return JSONResponse({"error": "not found"}, status_code=404)
    with open(path, encoding="utf-8") as f:
        return JSONResponse({"file": safe, "content": f.read()})


@app.get("/api/archive/list")
def archive_list():
    from archive_index import build_archive_index
    return JSONResponse(build_archive_index(ARCHIVES))


@app.get("/api/archive/get")
def archive_get(file: str = Query(...)):
    safe = os.path.basename(file)
    if not safe.endswith(".md"):
        return JSONResponse({"error": "bad file"}, status_code=400)
    path = os.path.join(ARCHIVES, safe)
    if not os.path.isfile(path):
        return JSONResponse({"error": "not found"}, status_code=404)
    with open(path, encoding="utf-8") as f:
        return JSONResponse({"file": safe, "content": f.read()})


@app.get("/api/browse/chapters")
def browse_chapters():
    con = db()
    rows = con.execute("""
        SELECT c.chapter_id, c.name, c.num, c.quest_type,
               COUNT(dc.hash) AS n
        FROM chapters c LEFT JOIN dialogue_chapter dc ON c.chapter_id = dc.chapter_id
        GROUP BY c.chapter_id HAVING n > 0 ORDER BY c.chapter_id""").fetchall()
    con.close()
    return JSONResponse([{"chapter_id": r["chapter_id"], "name": r["name"], "num": r["num"],
                          "type": r["quest_type"], "count": r["n"]} for r in rows])


@app.get("/api/browse/dialogs")
def browse_dialogs(chapter_id: int, page: int = 1):
    offset = (page - 1) * 200
    con = db()
    total = con.execute("""
        SELECT COUNT(*) FROM (
            SELECT 1 FROM dialogue_chapter dc JOIN entries e ON e.hash = dc.hash
            WHERE dc.chapter_id = ? GROUP BY e.text_zh)""",
        (chapter_id,)).fetchone()[0]
    # 同一 hash 在 entries 可能有多行（Dialog 源 + TextMap 源各灌一次），
    # join 时必须钉住每 hash 的 MIN(id) 行，否则对话翻倍；
    # 排序用 sort_key = mainQuest演出序 * 1e12 + talk官方触发序 * 1e6 + 文件内序
    rows = con.execute("""
        SELECT e.text_zh AS text_zh, s.speaker AS speaker, dc2.quest_id AS quest_id FROM (
            SELECT e2.hash AS h, MIN(dc.sort_key) AS ord
            FROM dialogue_chapter dc JOIN entries e2 ON e2.hash = dc.hash
            WHERE dc.chapter_id = ? GROUP BY e2.text_zh
            ORDER BY ord LIMIT ? OFFSET ?) t
        JOIN dialogue_chapter dc2 ON dc2.hash = t.h AND dc2.sort_key = t.ord
        JOIN entries e ON e.hash = t.h
             AND e.id = (SELECT MIN(id) FROM entries WHERE hash = t.h)
        LEFT JOIN dialogue_speaker s ON s.talk_id = dc2.talk_id AND s.hash = t.h
        ORDER BY t.ord""",
        (chapter_id, 200, offset)).fetchall()
    con.close()
    return JSONResponse({"total": total, "page": page,
                         "lines": [(r["speaker"] or "") + "|" + r["text_zh"]
                                   + "|" + str(r["quest_id"] or "") for r in rows]})


@app.get("/api/browse/quests")
def browse_quests(chapter_id: int):
    """章内 quest 列表（官方演出序/数字序 + 官方标题），供前端任务分组显示"""
    con = db()
    rows = con.execute("""
        SELECT q.quest_id, q.title FROM (
            SELECT DISTINCT quest_id FROM dialogue_chapter
            WHERE chapter_id = ? AND quest_id IS NOT NULL) d
        LEFT JOIN quest_play_order po ON po.chapter_id = ? AND po.quest_id = d.quest_id
        LEFT JOIN quest_titles q ON q.quest_id = d.quest_id
        ORDER BY COALESCE(po.seq, 9999), d.quest_id""", (chapter_id, chapter_id)).fetchall()
    con.close()
    return {str(r["quest_id"]): r["title"] or "" for r in rows}


@app.get("/api/categories")
def categories():
    con = db()
    rows = con.execute(
        "SELECT category, COUNT(*) AS n FROM entries GROUP BY category ORDER BY n DESC"
    ).fetchall()
    con.close()
    return [{"name": r["category"], "count": r["n"]} for r in rows]


@app.get("/api/search")
def search(q: str, cat: str = "", page: int = 1):
    q = q.strip()
    if not q:
        return JSONResponse({"total": 0, "page": 1, "pages": 0, "items": [], "took": 0})
    page = max(1, page)
    offset = (page - 1) * PER_PAGE
    t0 = time.time()
    con = db()

    cat_sql, cat_args = ("", [])
    if cat:
        cat_sql = " AND e.category = ?"
        cat_args = [cat]

    def get_talks(rows):
        hashes = [r["hash"] for r in rows if r["hash"]]
        talks = {}
        if hashes:
            ph = ",".join("?" * len(hashes))
            for r in con.execute(
                f"SELECT hash, quest_title, talk_id, kind FROM talk_map WHERE hash IN ({ph})",
                hashes).fetchall():
                talks[r["hash"]] = r
        return talks

    def finalize(rows, total, mode, keyword, talks):
        items = []
        for r in rows:
            zh, en = r["hz"], r["he"]
            if mode == "like":
                zh = zh.replace(keyword, f"<mark>{keyword}</mark>")
                en = en.replace(keyword, f"<mark>{keyword}</mark>") if en else ""
            elif r["title"] and keyword in r["title"]:
                r = dict(r)
                r["title"] = r["title"].replace(keyword, f"<mark>{keyword}</mark>")
            talk = ""
            t = talks.get(r["hash"]) if r["hash"] else None
            if t:
                talk = t["quest_title"] or (f"{t['kind']}·talk{t['talk_id']}" if t["talk_id"] else "")
            items.append({
                "category": r["category"], "source": r["source"],
                "entry_id": r["entry_id"], "field": r["field"], "hash": r["hash"],
                "title": r["title"], "talk": talk,
                "text_zh": zh, "text_en": en,
            })
        return JSONResponse({
            "total": total, "page": page,
            "pages": max(1, (total + PER_PAGE - 1) // PER_PAGE),
            "items": items, "took": round(time.time() - t0, 3),
        })

    try:
        if len(q) >= 3:
            match_expr = '"' + q.replace('"', '""') + '"'
            total = con.execute(
                "SELECT COUNT(*) FROM fts JOIN entries e ON e.id = fts.rowid "
                "WHERE fts MATCH ?" + cat_sql,
                [match_expr] + cat_args).fetchone()[0]
            rows = con.execute(
                "SELECT e.category, e.source, e.entry_id, e.field, e.hash, e.title, "
                "highlight(fts, 0, '<mark>', '</mark>') AS hz, "
                "highlight(fts, 1, '<mark>', '</mark>') AS he "
                "FROM fts JOIN entries e ON e.id = fts.rowid "
                "WHERE fts MATCH ?" + cat_sql + " ORDER BY rank LIMIT ? OFFSET ?",
                [match_expr] + cat_args + [PER_PAGE, offset]).fetchall()
            talks = get_talks(rows)
            con.close()
            return finalize(rows, total, "fts", q, talks)
    except sqlite3.OperationalError:
        pass  # FTS 语法问题 → 回退 LIKE

    like = f"%{q.replace('%', r'\%').replace('_', r'\_')}%"
    total = con.execute(
        "SELECT COUNT(*) FROM entries e WHERE (e.text_zh LIKE ? ESCAPE '\\' "
        "OR e.text_en LIKE ? ESCAPE '\\' OR e.title LIKE ? ESCAPE '\\')" + cat_sql,
        [like, like, like] + cat_args).fetchone()[0]
    rows = con.execute(
        "SELECT e.category, e.source, e.entry_id, e.field, e.hash, e.title, "
        "e.text_zh AS hz, e.text_en AS he FROM entries e "
        "WHERE (e.text_zh LIKE ? ESCAPE '\\' OR e.text_en LIKE ? ESCAPE '\\' "
        "OR e.title LIKE ? ESCAPE '\\')" + cat_sql +
        " ORDER BY e.id LIMIT ? OFFSET ?",
        [like, like, like] + cat_args + [PER_PAGE, offset]).fetchall()
    talks = get_talks(rows)
    con.close()
    return finalize(rows, total, "like", q, talks)


# ============ 知识层 KG（v2.3.0 D4） ============

@app.get("/kg.html")
def kg_page():
    return FileResponse(os.path.join(BASE, "kg.html"), media_type="text/html; charset=utf-8")


@app.get("/arbitration.html")
def arbitration_page():
    return FileResponse(os.path.join(BASE, "arbitration.html"), media_type="text/html; charset=utf-8")


@app.get("/api/kg/entities")
def kg_entities(cat: str = Query(None), q: str = Query(None)):
    con = db()
    sql = """SELECT e.eid, e.ent_code, e.name, e.official_category, e.obc_entry_id, e.type,
                    e.review_status, e.status,
                    (SELECT COUNT(*) FROM kg_aliases a WHERE a.eid=e.eid) alias_n,
                    (SELECT COUNT(*) FROM kg_claims c WHERE c.subject_id=e.eid) claim_n
             FROM kg_entities e WHERE e.status='active'"""
    args = []
    if cat:
        sql += " AND e.official_category=?"; args.append(cat)
    if q:
        sql += " AND (e.name LIKE ? OR EXISTS(SELECT 1 FROM kg_aliases a WHERE a.eid=e.eid AND a.alias LIKE ?))"
        args += [f"%{q}%", f"%{q}%"]
    rows = con.execute(sql + " ORDER BY e.ent_code", args).fetchall()
    con.close()
    return [dict(r) for r in rows]


@app.get("/api/kg/entity")
def kg_entity_detail(eid: int = Query(...)):
    """实体详情：别名强制解析 + claims（含置信过滤）——AI-first 的主查询口"""
    con = db()
    ent = con.execute("SELECT * FROM kg_entities WHERE eid=?", (eid,)).fetchone()
    if not ent:
        con.close(); return JSONResponse({"error": "not found"}, 404)
    aliases = con.execute("SELECT alias, lang, confidence, evidence FROM kg_aliases WHERE eid=?", (eid,)).fetchall()
    claims = con.execute("""SELECT cid, predicate, object_text, object_id, quote, source, confidence,
                                   narrator, review_status FROM kg_claims WHERE subject_id=?""",
                          (eid,)).fetchall()
    claims = [dict(c) for c in claims]
    for c in claims:
        c["predicate_zh"] = predicate_zh(c["predicate"])
    caveats = con.execute("SELECT cave_id, description, scope, severity FROM kg_corpus_caveats WHERE status='open'").fetchall()
    con.close()
    return {"entity": dict(ent), "aliases": [dict(a) for a in aliases],
            "claims": claims,
            "corpus_caveats": [dict(c) for c in caveats]}


@app.get("/api/kg/resolve")
def kg_resolve(name: str = Query(...)):
    """别名强制解析：任意名字 → 实体（P7 名讳混淆的运行时防线）"""
    con = db()
    rows = con.execute("""SELECT DISTINCT e.eid, e.ent_code, e.name, e.official_category, e.type, a.confidence
             FROM kg_aliases a JOIN kg_entities e ON e.eid=a.eid
             WHERE a.alias=? AND e.status='active'""", (name,)).fetchall()
    if not rows:
        rows = con.execute("""SELECT eid, ent_code, name, official_category, type, '主名' AS confidence
                 FROM kg_entities WHERE name=? AND status='active'""", (name,)).fetchall()
    con.close()
    return [dict(r) for r in rows]


@app.get("/api/kg/claims")
def kg_claims(subject: int = Query(None), confidence: str = Query(None), predicate: str = Query(None)):
    con = db()
    sql = """SELECT c.cid, e.name AS subject, c.predicate, c.object_text, c.object_id, c.quote,
                    c.source, c.confidence, c.narrator, c.review_status
             FROM kg_claims c JOIN kg_entities e ON e.eid=c.subject_id WHERE 1=1"""
    args = []
    if subject: sql += " AND c.subject_id=?"; args.append(subject)
    if confidence: sql += " AND c.confidence=?"; args.append(confidence)
    if predicate: sql += " AND c.predicate=?"; args.append(predicate)
    rows = con.execute(sql + " ORDER BY c.cid DESC LIMIT 200", args).fetchall()
    con.close()
    out = [dict(r) for r in rows]
    for r in out:
        r["predicate_zh"] = predicate_zh(r["predicate"])
    return out


@app.get("/api/kg/timeline")
def kg_timeline():
    """v2 时间轴：读 kg_ 两级表（旧 /api/timeline 读冻结表保留兼容）"""
    con = db()
    eras = con.execute("SELECT * FROM kg_eras ORDER BY ord").fetchall()
    out = []
    for e in eras:
        nodes = con.execute("""SELECT nid, title, detail, text_hash, quote, narrative_mode, ord
                               FROM kg_timeline_nodes WHERE era_id=? ORDER BY ord""", (e["era_id"],)).fetchall()
        out.append({"era": dict(e), "nodes": [dict(n) for n in nodes]})
    con.close()
    return out


@app.get("/api/arbitration/decide")
def arbitration_decide(arid: int = Query(...), status: str = Query(...)):
    """master 三态裁决（Q7 独裁权）。merged/split/uncertain/dismissed"""
    assert status in ("merged", "split", "uncertain", "dismissed")
    con = db()
    con.execute("UPDATE kg_arbitration SET status=?, decided_by='master', decided_at=datetime('now') WHERE arid=?",
                (status, arid))
    con.commit()
    con.close()
    return {"ok": True}


@app.get("/api/arbitration/list")
def arbitration_list(status: str = Query("pending")):
    con = db()
    rows = con.execute("SELECT * FROM kg_arbitration WHERE status=? ORDER BY arid", (status,)).fetchall()
    con.close()
    return [dict(r) for r in rows]


# ============ 谓词中文显示（web 只出中文，英文谓词仅内部用） ============
PRED_ZH_EXTRA = {
    "master-of": "师徒（师）", "student-of": "师徒（徒）", "has-student": "弟子",
    "absorbs": "吸收", "parsed-relation": "档案关系", "free": "自定义关系",
}

def predicate_zh(pid: str) -> str:
    if not pid:
        return ""
    if pid.startswith("free:"):
        slug = pid[5:]
        return PRED_ZH_EXTRA.get(slug, "自定义关系")
    con = db()
    row = con.execute("SELECT label_zh FROM kg_predicates WHERE pid=?", (pid,)).fetchone()
    con.close()
    if row:
        return row[0]
    return PRED_ZH_EXTRA.get(pid, "自定义关系")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=9020, log_level="warning")
