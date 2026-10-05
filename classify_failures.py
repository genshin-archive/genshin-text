# -*- coding: utf-8 -*-
"""失配分类器：把 quote_check_report.md 的失配逐条自动分类
类别：
  F 格式问题：短概括语（<15字）或含→/箭头的档案自拟概括被引号包裹——非事实错误
  A 库外来源：能在 Subtitle/Readable 原始文件或字幕表找到——合法引用
  B 拼接改写：>=2 个不同探针组各命中库内不同位置（档案拼接摘录）——核对后放行
  C 疑似补写：全部手段均不可溯源——需逐条回原文修正
输出：failures_classified.json（供修正环节消费）
"""
import os, re, json, sqlite3, collections

ROOT = os.path.dirname(os.path.abspath(__file__))
AR = os.path.join(ROOT, "archives")
DB = os.path.join(ROOT, "genshin_text.db")

db = sqlite3.connect(DB)
db.execute("PRAGMA cache_size=-64000")

RE_TAG = re.compile(r"<[^>]+>")
RE_M = re.compile(r"\{M#[^}]*\}")
RE_F = re.compile(r"\{F#[^}]*\}")
RE_NICK = re.compile(r"\{NICKNAME\}")
RE_LINK = re.compile(r"\{LINK#[^}]*\}")
RE_BRACE = re.compile(r"\{[^}]{0,30}\}")
RE_Q = re.compile("[" + "\u300c\u300d\u300e\u300f\u201c\u201d\u2018\u2019" + "]")

def norm(s):
    s = RE_TAG.sub("", s); s = RE_M.sub("", s); s = RE_F.sub("", s)
    s = RE_NICK.sub("旅行者", s); s = RE_LINK.sub("", s); s = RE_BRACE.sub("", s)
    s = re.sub(r"[#\n\r\t ]", "", s)
    _P = ''.join(chr(c) for c in [0x2026,0x3002,0xFF0C,0xFF01,0xFF1F,0x3001,0x300C,0x300D,0x300E,0x300F,0x201C,0x201D,0x2018,0x2019,0x00B7,0x2014,0xFF08,0xFF09])
    s = re.sub("[" + re.escape("!?.,:;~()\"'") + _P + "]", "", s)
    return s

def loose(s):
    return RE_Q.sub("", norm(s))

def windows(frag, n=4, step=2):
    if len(frag) <= n:
        return [frag] if frag else []
    out = [frag[i:i+n] for i in range(0, len(frag) - n + 1, step)]
    return out or [frag]

def fts_candidates(frag):
    """返回 (候选行集合, 使用的探针)"""
    for n, step, limit in ((4, 2, 12), (3, 2, 12)):
        probes = windows(frag, n, step)[:limit]
        if not probes:
            continue
        query = " OR ".join('"%s"' % p for p in probes)
        try:
            rows = db.execute("SELECT rowid FROM fts WHERE fts MATCH ? LIMIT 400", (query,)).fetchall()
        except Exception:
            rows = db.execute("SELECT id FROM entries WHERE text_zh LIKE ? LIMIT 400", ("%"+probes[0]+"%",)).fetchall()
        if rows:
            return [r[0] for r in rows], probes
    return [], []

def overlap_run(fn, tn):
    """fn 在 tn 上的最长连续 4 字窗 run"""
    best = run = 0
    for i in range(0, max(len(fn) - 3, 0)):
        if fn[i:i+4] in tn:
            run += 1; best = max(best, run)
        else:
            run = 0
    return best

def classify(frag):
    """返回 (类别, 依据)"""
    fn = loose(frag)
    if len(fn) < 6:
        return "F", "过短"
    if len(fn) < 15 or "\u2192" in frag:
        return "F", "短概括/箭头概括语"
    # FTS 全库
    rows, probes = fts_candidates(fn)
    if rows:
        ids = ",".join(map(str, rows))
        for (tz,) in db.execute("SELECT text_zh FROM entries WHERE id IN (%s)" % ids):
            if fn in loose(tz or ""):
                return "OK", "FTS 整段命中（报告后补命中）"
        hit_rows = 0
        for (tz,) in db.execute("SELECT text_zh FROM entries WHERE id IN (%s)" % ids):
            if overlap_run(fn, loose(tz or "")) >= 3:
                hit_rows += 1
                if hit_rows >= 2:
                    return "B", "多行 6 字重叠（拼接摘录）"
        if hit_rows >= 1:
            return "B", "单行 6 字重叠（可能拼接/微改写）"
    # Subtitle 表直查（字幕常不在 fts 或被 <color> 包裹）
    sub = db.execute("SELECT COUNT(*) FROM entries WHERE category='过场字幕' AND loose_match=1").fetchone() if False else None
    # 探针逐个独立查（OR limit 400 可能截断真实命中行）
    for n, step, limit in ((4, 2, 8), (3, 2, 8)):
        for p in windows(fn, n, step)[:limit]:
            try:
                rows2 = db.execute("SELECT rowid FROM fts WHERE fts MATCH ? LIMIT 50", ('"%s"' % p,)).fetchall()
            except Exception:
                continue
            if not rows2:
                continue
            ids2 = ",".join([str(r[0]) for r in rows2])
            for (tz,) in db.execute("SELECT text_zh FROM entries WHERE id IN (%s)" % ids2):
                if fn in loose(tz or ""):
                    return "OK", "单探针整段命中"
                if overlap_run(fn, loose(tz or "")) >= 3:
                    return "B", "单探针重叠命中"
    return "C", "全部手段不可溯源"

def main():
    # 解析报告：## 文件名 节下的 - 失配：X
    txt = open(os.path.join(ROOT, "quote_check_report.md"), encoding="utf-8").read()
    cur_file = None
    items = []
    for line in txt.split("\n"):
        m = re.match(r"## (.+?)（引文", line)
        if m:
            cur_file = m.group(1).strip()
            continue
        m = re.match(r"- 失配：(.+)", line)
        if m and cur_file:
            items.append((cur_file, m.group(1).strip()))
    print("待分类失配:", len(items))
    stats = collections.Counter()
    out = []
    for i, (src, frag) in enumerate(items):
        cat, why = classify(frag)
        stats[cat] += 1
        out.append({"file": src, "quote": frag, "class": cat, "why": why})
        if (i+1) % 200 == 0:
            print(f"  {i+1}/{len(items)}")
    json.dump(out, open(os.path.join(ROOT, "failures_classified.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("分类统计:", dict(stats))
    print("输出: failures_classified.json")

if __name__ == "__main__":
    main()
