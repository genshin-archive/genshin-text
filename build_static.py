# -*- coding: utf-8 -*-
"""build_static.py — 生成 GitHub Pages 静态展示站（site/）
原则：页面 JS 逻辑不动，只把 fetch("api/...") 定向替换为 data/*.json；
数据格式与 server.py API 输出逐字段一致。
"""
import json
import os
import shutil
import sqlite3

BASE = r"C:\AI Programs\genshin-text"
SITE = os.path.join(BASE, "site")
DB = os.path.join(BASE, "genshin_text.db")

PRED_ZH_EXTRA = {
    "master-of": "师徒（师）", "student-of": "师徒（徒）", "has-student": "弟子",
    "absorbs": "吸收", "parsed-relation": "档案关系", "free": "自定义关系",
}

def zh_path(*p):
    return os.path.join(BASE, *p)

def wjson(rel, obj):
    path = os.path.join(SITE, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)

def predicate_zh(con, pid):
    if not pid:
        return ""
    if pid.startswith("free:"):
        return PRED_ZH_EXTRA.get(pid[5:], "自定义关系")
    row = con.execute("SELECT label_zh FROM kg_predicates WHERE pid=?", (pid,)).fetchone()
    return (row[0] if row else PRED_ZH_EXTRA.get(pid, "自定义关系"))

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row

# ===== 1) 目录骨架（保留 site/.git —— gh-pages 分支仓库）=====
import stat, shutil as _sh

def _rm_ro(func, path, _exc):
    os.chmod(path, stat.S_IWRITE)
    func(path)

if os.path.isdir(SITE):
    gitdir = os.path.join(SITE, ".git")
    keep = SITE + "_git_keep"
    if os.path.isdir(keep):
        _sh.rmtree(keep, onerror=_rm_ro)
    moved = False
    if os.path.isdir(gitdir):
        os.rename(gitdir, keep)
        moved = True
    _sh.rmtree(SITE, onerror=_rm_ro)
    os.makedirs(os.path.join(SITE, "data"))
    if moved:
        os.rename(keep, gitdir)
else:
    os.makedirs(os.path.join(SITE, "data"))
shutil.copytree(zh_path("archives"), os.path.join(SITE, "archives"))
shutil.copy(zh_path("theme.css"), os.path.join(SITE, "theme.css"))
shutil.copy(zh_path("hypothesis.md"), os.path.join(SITE, "hypothesis.md"))

# ===== 2) 章节列表 =====
chapters = con.execute("""
    SELECT c.chapter_id, c.name, c.num, c.quest_type,
           COUNT(DISTINCT e.text_zh) AS n
    FROM chapters c JOIN dialogue_chapter dc ON c.chapter_id = dc.chapter_id
    JOIN entries e ON e.hash = dc.hash
    GROUP BY c.chapter_id HAVING n > 0 ORDER BY c.chapter_id""").fetchall()
wjson("data/browse_chapters.json", [
    {"chapter_id": r["chapter_id"], "name": r["name"], "num": r["num"],
     "type": r["quest_type"], "count": r["n"]} for r in chapters])
print(f"browse_chapters: {len(chapters)} 章")

# ===== 3) 每章对话（按页 200 行，复刻 API 结构）=====
n_dialog_files = 0
for r in chapters:
    cid = r["chapter_id"]
    rows = con.execute("""
        SELECT e.text_zh AS t, s.speaker AS sp, dc2.quest_id AS qid FROM (
            SELECT e2.hash AS h, MIN(dc.sort_key) AS ord
            FROM dialogue_chapter dc JOIN entries e2 ON e2.hash = dc.hash
            WHERE dc.chapter_id = ? GROUP BY e2.text_zh) t2
        JOIN dialogue_chapter dc2 ON dc2.hash = t2.h AND dc2.sort_key = t2.ord
        JOIN entries e ON e.hash = t2.h AND e.id = (SELECT MIN(id) FROM entries WHERE hash = t2.h)
        LEFT JOIN dialogue_speaker s ON s.talk_id = dc2.talk_id AND s.hash = t2.h
        ORDER BY t2.ord""", (cid,)).fetchall()
    lines = [(x["sp"] or "") + "|" + x["t"] + "|" + str(x["qid"] or "") for x in rows]
    total = len(lines)
    pages = max(1, (total + 199) // 200)
    for p in range(1, pages + 1):
        wjson(f"data/browse_dialogs/{cid}_p{p}.json",
              {"total": total, "page": p, "lines": lines[(p-1)*200: p*200]})
        n_dialog_files += 1
    # quest 标题
    qrows = con.execute("""
        SELECT q.quest_id, q.title FROM (
            SELECT DISTINCT quest_id FROM dialogue_chapter
            WHERE chapter_id = ? AND quest_id IS NOT NULL) d
        LEFT JOIN quest_play_order po ON po.chapter_id = ? AND po.quest_id = d.quest_id
        LEFT JOIN quest_titles q ON q.quest_id = d.quest_id
        ORDER BY COALESCE(po.seq, 9999), d.quest_id""", (cid, cid)).fetchall()
    wjson(f"data/browse_quests/{cid}.json",
          {str(x["quest_id"]): x["title"] or "" for x in qrows})
print(f"browse_dialogs: {n_dialog_files} 个分页文件")

# ===== 4) 时间线 =====
eras = con.execute("SELECT * FROM kg_eras ORDER BY ord").fetchall()
tl = []
for e in eras:
    nodes = con.execute("""SELECT nid, title, detail, text_hash, quote, narrative_mode, ord
                           FROM kg_timeline_nodes WHERE era_id=? ORDER BY ord""",
                         (e["era_id"],)).fetchall()
    tl.append({"era": dict(e), "nodes": [dict(n) for n in nodes]})
wjson("data/kg_timeline.json", tl)
print(f"kg_timeline: {len(tl)} 纪元")

# ===== 5) 知识层实体列表 + 详情 =====
ents = con.execute("""SELECT e.eid, e.ent_code, e.name, e.official_category, e.obc_entry_id, e.type,
                             e.review_status, e.status,
                             (SELECT COUNT(*) FROM kg_aliases a WHERE a.eid=e.eid) alias_n,
                             (SELECT COUNT(*) FROM kg_claims c WHERE c.subject_id=e.eid) claim_n
                      FROM kg_entities e WHERE e.status='active' ORDER BY e.ent_code""").fetchall()
wjson("data/kg_entities.json", [dict(x) for x in ents])
n_ent = 0
for e in ents:
    eid = e["eid"]
    ent = dict(con.execute("SELECT * FROM kg_entities WHERE eid=?", (eid,)).fetchone())
    aliases = [dict(a) for a in con.execute(
        "SELECT alias, lang, confidence, evidence FROM kg_aliases WHERE eid=?", (eid,)).fetchall()]
    claims = []
    for c in con.execute("""SELECT cid, predicate, object_text, object_id, quote, source, confidence,
                                   narrator, review_status FROM kg_claims WHERE subject_id=?""",
                          (eid,)).fetchall():
        d = dict(c)
        d["predicate_zh"] = predicate_zh(con, d["predicate"])
        claims.append(d)
    caveats = [dict(c) for c in con.execute(
        "SELECT cave_id, description, scope, severity FROM kg_corpus_caveats WHERE status='open'").fetchall()]
    wjson(f"data/kg_entity/{eid}.json",
          {"entity": ent, "aliases": aliases, "claims": claims, "corpus_caveats": caveats})
    n_ent += 1
print(f"kg_entities: {len(ents)} 行列表 + {n_ent} 个详情文件")

# ===== 6) 档案库 / 假说库 列表（与 server.py 共用 archive_index 归组）=====
from archive_index import build_archive_index
wjson("data/archive_list.json", build_archive_index(zh_path("archives")))
wjson("data/hypothesis_list.json", {"items": [{"file": "hypothesis.md", "title": "假说库（全部）"}]})
print(f"archive_list: 分组结构（{len(build_archive_index(zh_path('archives'))['groups'])} 组）")
con.close()

# ===== 7) 页面变体（定向替换 fetch 路径）=====
def make_page(src, dst, repl):
    with open(zh_path(src), encoding="utf-8") as f:
        s = f.read()
    for old, new in repl:
        if old not in s:
            raise SystemExit(f"替换锚点未命中 [{src}]: {old[:60]}")
        s = s.replace(old, new)
    with open(os.path.join(SITE, dst), "w", encoding="utf-8") as f:
        f.write(s)

# 导航去仲裁（静态站无写接口；行尾 CRLF/LF 兼容——只匹配单行片段）
NAV_ARB = '<a href="arbitration.html" data-p="arb">仲裁</a>'

make_page("browse.html", "browse.html", [
    ('fetch("api/browse/chapters")', 'fetch("data/browse_chapters.json")'),
    ('fetch(`api/browse/quests?chapter_id=${id}`)', 'fetch(`data/browse_quests/${id}.json`)'),
    ('fetch(`api/browse/dialogs?chapter_id=${curCh}&page=${curPage}`)',
     'fetch(`data/browse_dialogs/${curCh}_p${curPage}.json`)'),
    (NAV_ARB, ""),
])
make_page("timeline.html", "timeline.html", [
    ('fetch("api/kg/timeline")', 'fetch("data/kg_timeline.json")'),
    (NAV_ARB, ""),
])
make_page("archive.html", "archive.html", [
    ('fetch("api/archive/list")', 'fetch("data/archive_list.json")'),
    ('fetch("api/archive/get?file="+encodeURIComponent(item.dataset.f))',
     'fetch("archives/"+encodeURIComponent(item.dataset.f))'),
    (""".then(r=>r.json()).then(d=>{
        document.getElementById("content").innerHTML =
          d.content ? '<div class="md">'+renderMd(d.content)+"</div>"
                    : '<div class="md empty">'+esc(d.error||"读取失败")+"</div>";
      });""",
     """.then(r=>r.text()).then(t=>{
        document.getElementById("content").innerHTML =
          t ? '<div class="md">'+renderMd(t)+"</div>"
            : '<div class="md empty">读取失败</div>';
      });"""),
    (NAV_ARB, ""),
])
make_page("hypothesis.html", "hypothesis.html", [
    ('fetch("api/hypothesis/list")', 'fetch("data/hypothesis_list.json")'),
    ('fetch("api/hypothesis/get?file="+encodeURIComponent(item.dataset.f))',
     'fetch(encodeURIComponent(item.dataset.f))'),
    (""".then(r=>r.json()).then(d=>{
        document.getElementById("content").innerHTML =
          d.content ? '<div class="md">'+renderMd(d.content)+"</div>"
                    : '<div class="md empty">'+esc(d.error||"读取失败")+"</div>";
      });""",
     """.then(r=>r.text()).then(t=>{
        document.getElementById("content").innerHTML =
          t ? '<div class="md">'+renderMd(t)+"</div>"
            : '<div class="md empty">读取失败</div>';
      });"""),
    (NAV_ARB, ""),
])
make_page("kg.html", "kg.html", [
    ("""  const r = await fetch(`api/kg/entities?${curCat?`cat=${curCat}&`:""}${document.getElementById("q").value?`q=${encodeURIComponent(document.getElementById("q").value)}`:""}`);
  const list = await r.json();""",
     """  if (!window._allEnts) { window._allEnts = await (await fetch("data/kg_entities.json")).json(); }
  const kw = document.getElementById("q").value;
  const list = window._allEnts.filter(e => (!curCat || e.official_category === curCat)
    && (!kw || e.name.includes(kw) || (e.official_category||"").includes(kw)));"""),
    ('fetch(`api/kg/entity?eid=${eid}`)', 'fetch(`data/kg_entity/${eid}.json`)'),
    (NAV_ARB, ""),
])
# kg 页面"无匹配"文案用的 p 标签保留即可

# ===== 8) 门户首页 =====
INDEX = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>原神文本资料库 · 展示站</title>
<link rel="stylesheet" href="theme.css">
<style>
  .hero { text-align:center; padding:34px 0 8px; }
  h1 { font-size:28px; letter-spacing:8px; font-weight:600; color:#4a5168; }
  h1::before, h1::after { content:"✦"; color:var(--gold); font-size:14px; vertical-align:middle; margin:0 14px; }
  .lede { margin-top:12px; color:var(--ink-light); font-size:13px; letter-spacing:2px; }
  .grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(300px,1fr)); gap:14px; margin-top:34px; }
  .nav-card { display:block; text-decoration:none; color:inherit; background:var(--card);
    border:1px solid var(--line); border-radius:12px; padding:20px 22px; transition:all .15s; }
  .nav-card:hover { border-color:var(--gold); box-shadow:0 3px 14px rgba(168,135,63,.10); transform:translateY(-2px); }
  .nav-card .ic { font-size:24px; }
  .nav-card .t { font-size:16px; margin:8px 0 6px; color:#4a5168; letter-spacing:1px; }
  .nav-card .d { font-size:12.5px; color:var(--ink-light); line-height:1.8; }
  .stats { display:flex; justify-content:center; gap:34px; margin-top:26px; flex-wrap:wrap; }
  .stat { text-align:center; }
  .stat b { display:block; font-size:22px; color:var(--gold-deep); font-weight:600; }
  .stat span { font-size:12px; color:var(--ink-light); letter-spacing:1px; }
  .note { margin-top:34px; text-align:center; font-size:12px; color:var(--ink-light); line-height:2; }
</style>
</head>
<body>
<nav id="zg-nav">
  <span class="brand">原神资料库 v3</span>
  <a href="index.html" class="cur">展示站</a>
  <a href="browse.html">章节浏览</a>
  <a href="timeline.html">时间线</a>
  <a href="kg.html">知识层</a>
  <a href="archive.html">档案库</a>
  <a href="hypothesis.html">假说库</a>
</nav>
<div class="wrap">
  <div class="hero">
    <h1>原神文本资料库</h1>
    <div class="lede">全量游戏文本 · 精读档案 · 知识图谱 · 多轴时间线</div>
    <div class="stats">
      <div class="stat"><b>1,231,365</b><span>语料条目</span></div>
      <div class="stat"><b>881</b><span>精读档案</span></div>
      <div class="stat"><b>6,716</b><span>知识实体</span></div>
      <div class="stat"><b>19,591</b><span>断言（带引文）</span></div>
      <div class="stat"><b>161</b><span>时间线节点</span></div>
    </div>
  </div>
  <div class="grid">
    <a class="nav-card" href="archive.html">
      <div class="ic">📜</div><div class="t">精读档案库</div>
      <div class="d">881 份按 STANDARD v1.0 重建的章节/角色/书籍/武器档案——叙事流、关键断言表（逐字引文）、时间锚、隐喻代指、悬案。</div>
    </a>
    <a class="nav-card" href="browse.html">
      <div class="ic">💬</div><div class="t">章节浏览</div>
      <div class="d">142 章主线/传说/世界任务对话，官方演出顺序（Talk beginCond 触发序），按任务分组显示。</div>
    </a>
    <a class="nav-card" href="timeline.html">
      <div class="ic">⏳</div><div class="t">多轴时间线</div>
      <div class="d">8 纪元 161 节点，非线性时间结构化：叙述模式逐条标注（明文/回忆/预言/改写/倒流/矛盾对/应验）。</div>
    </a>
    <a class="nav-card" href="kg.html">
      <div class="ic">🕸️</div><div class="t">知识层</div>
      <div class="d">6,716 实体 / 19,591 断言，置信四级（明文·转述必带叙述者），别名强制解析，每条断言可回查引文。</div>
    </a>
    <a class="nav-card" href="hypothesis.html">
      <div class="ic">💡</div><div class="t">假说库</div>
      <div class="d">推演与悬案的集中收纳——推论只进假说，不入正文。</div>
    </a>
  </div>
  <div class="note">
    本站为静态展示版（GitHub Pages）。123 万条全文毫秒检索、仲裁工作流等动态功能见本地版 / 服务器版。<br>
    发现错误或遗漏？欢迎 <a href="https://github.com/genshin-archive/genshin-text/issues/new?template=errata.md" style="color:var(--gold-deep)">提交勘误</a>——一切以游戏内文本为准，有原文出处的反馈会被优先核实。<br>
    游戏文本版权归米哈游所有 · 数据源 Dimbreath/AnimeGameData2 · 重建与审计记录见仓库 CHANGELOG
  </div>
</div>
</body>
</html>
"""
with open(os.path.join(SITE, "index.html"), "w", encoding="utf-8") as f:
    f.write(INDEX)
with open(os.path.join(SITE, ".nojekyll"), "w") as f:
    f.write("")

# ===== 9) 体积报告 =====
total = 0
for root, _, files in os.walk(SITE):
    for f in files:
        total += os.path.getsize(os.path.join(root, f))
n_files = sum(len(files) for _, _, files in os.walk(SITE))
print(f"\n=== site/ 完成：{n_files} 个文件, {total/1024/1024:.1f} MB ===")
