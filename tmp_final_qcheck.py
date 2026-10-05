# -*- coding: utf-8 -*-
"""逐条测试候选引文是否能通过 check_claims 的 seg_hit 逻辑。
用法：python tmp_final_qcheck.py 候选文件.txt   （每行一条「」内的候选原文，不含外层引号）
"""
import sys, os, re, sqlite3

DB = "genshin_text.db"
STRIP = re.compile("[\u2026\u3002\uff0c\uff01\uff1f\u3001\s\u300c\u300d\u300e\u300f\u201c\u201d\u2018\u2019\u00b7\u2014\-~\uff01\uff1f!\?.,:;\"'()（）\n\r#■]")


def norm(s):
    s = re.sub(r"<[^>]+>", "", s or "")
    s = re.sub(r"\{[^}]{0,40}\}", "", s)
    return STRIP.sub("", s)


def seg_hit(db, seg, trace=False):
    fn = norm(seg)
    if len(fn) < 5:
        return True
    cand = set()
    for n_ in (4, 3):
        for i in range(0, max(len(fn) - n_ + 1, 1)):
            w = fn[i:i + n_]
            rows = db.execute("SELECT rowid FROM fts WHERE text_zh LIKE ? LIMIT 300", ("%" + w + "%",)).fetchall()
            if trace:
                print("    probe %-6s -> %d" % (w, len(rows)))
            for (rid,) in rows:
                cand.add(rid)
    for rid in cand:
        tz = db.execute("SELECT text_zh FROM entries WHERE id=?", (rid,)).fetchone()[0]
        if fn in norm(tz or ""):
            return True
    return False


def main(path):
    db = sqlite3.connect(DB)
    for line in open(path, encoding="utf-8"):
        s = line.rstrip("\n")
        if not s.strip() or s.startswith("##"):
            continue
        ok = seg_hit(db, s)
        print(("PASS " if ok else "FAIL ") + s[:70])


if __name__ == "__main__":
    main(sys.argv[1])
