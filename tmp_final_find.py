# -*- coding: utf-8 -*-
"""临时工具：引文→库内条目+说话人 反查。
用法：python tmp_final_find.py "引文片段" [更多片段...]
或：  python tmp_final_find.py -f 片段文件.txt
输出：hash / talk_id / quest / speaker / role_type / text_zh
"""
import sqlite3, sys, re

DB = "genshin_text.db"


def norm(s):
    s = re.sub(r"<[^>]+>", "", s or "")
    return re.sub(r"[\s\u3000]", "", s)


def find(seg):
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    key = norm(seg)
    if len(key) < 4:
        print("!! 片段过短:", seg)
        return
    cand = set()
    for n in (4, 3):
        for i in range(0, max(len(key) - n + 1, 1)):
            w = key[i:i + n]
            for (rid,) in cur.execute("SELECT rowid FROM fts WHERE text_zh LIKE ? LIMIT 300", ("%" + w + "%",)):
                cand.add(rid)
    hits = []
    for rid in cand:
        r = cur.execute("SELECT hash,text_zh,source,entry_id,category,field FROM entries WHERE id=?", (rid,)).fetchone()
        if key in norm(r["text_zh"] or ""):
            hits.append(r)
    if not hits:
        print("== 无命中:", seg)
        return
    print("== 命中 %d 条: %s" % (len(hits), seg))
    for r in hits[:6]:
        sps = cur.execute(
            "SELECT DISTINCT s.speaker, s.role_type, s.talk_id, dc.quest_id FROM dialogue_speaker s "
            "LEFT JOIN dialogue_chapter dc ON dc.hash=s.hash AND dc.talk_id=s.talk_id WHERE s.hash=?",
            (r["hash"],)).fetchall()
        spinfo = "; ".join("%s/%s/talk=%s/q=%s" % (s[0], s[1], s[2], s[3]) for s in sps) or "-"
        print("  hash=%s src=%s eid=%s cat=%s field=%s" % (r["hash"], r["source"], r["entry_id"], r["category"], r["field"]))
        print("     speaker: %s" % spinfo)
        print("     text: %s" % (r["text_zh"] or "")[:200])
    con.close()


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "-f":
        for line in open(args[1], encoding="utf-8"):
            line = line.strip()
            if line:
                find(line)
    else:
        for a in args:
            find(a)
