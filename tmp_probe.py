# -*- coding: utf-8 -*-
"""tmp_probe.py —— 引文探针：check 校验逐字命中；find 列出含关键词的库内原文
用法：python tmp_probe.py check "「…」"
     python tmp_probe.py find 关键词 [limit]
"""
import sys, os, re, sqlite3, json

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "genshin_text.db")
STRIP = re.compile(r"[\u2026\u3002\uff0c\uff01\uff1f\u3001\s\u300c\u300d\u300e\u300f\u201c\u201d\u2018\u2019\u00b7\u2014\-~\uff01\uff1f!\?.,:;\"'()（）\n\r#■]")
RE_BRACE = re.compile(r"\{[^}]{0,40}\}")


def norm(s):
    s = re.sub(r"<[^>]+>", "", s or "")
    s = RE_BRACE.sub("", s)
    return STRIP.sub("", s)


def cand_ids(db, fn):
    cand = set()
    for n_ in (4, 3):
        for i in range(0, max(len(fn) - n_ + 1, 1)):
            w = fn[i:i + n_]
            for (rid,) in db.execute("SELECT rowid FROM fts WHERE text_zh LIKE ? LIMIT 300", (f"%{w}%",)):
                cand.add(rid)
    return cand


def main():
    mode = sys.argv[1]
    arg = sys.argv[2]
    db = sqlite3.connect(DB)
    fn = norm(arg)
    if mode == "check":
        hit = 0
        for rid in cand_ids(db, fn):
            tz = db.execute("SELECT text_zh FROM entries WHERE id=?", (rid,)).fetchone()[0]
            if fn in norm(tz or ""):
                hit += 1
        print("HIT" if hit else "MISS", hit)
    else:
        lim = int(sys.argv[3]) if len(sys.argv) > 3 else 12
        shown = 0
        for rid in sorted(cand_ids(db, fn)):
            row = db.execute("SELECT category, source, entry_id, title, text_zh FROM entries WHERE id=?", (rid,)).fetchone()
            if not row or fn not in norm(row[4] or ""):
                continue
            print("||".join(str(x) for x in row[:4]))
            print(row[4])
            shown += 1
            if shown >= lim:
                break
        if not shown:
            print("(no hit)")
    db.close()


if __name__ == "__main__":
    main()
