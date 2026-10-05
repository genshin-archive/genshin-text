# -*- coding: utf-8 -*-
"""候选引文 → 库内 speaker / talk_id / quest 反查（按章过滤）。
用法：python tmp_final_spk.py <chapter_id> <候选文件.txt>
每行一条候选原文（不含外层「」）。
"""
import sys, re, sqlite3

BAD = re.compile(r"<color[^>]*>|</color>|<i>|</i>")


def clean(t):
    t = BAD.sub("", t or "")
    t = t.replace("{NICKNAME}", "旅行者")
    t = re.sub(r"\{M#([^}]*)\}\{F#([^}]*)\}", lambda m: m.group(1), t)
    t = re.sub(r"\{[^{}]*\}", "", t)
    return t.strip()


def norm(s):
    s = re.sub(r"<[^>]+>", "", s or "")
    s = re.sub(r"\{[^}]{0,40}\}", "", s)
    return re.sub(r"[\s\u3000]", "", s)


def main(cid, path):
    db = sqlite3.connect("genshin_text.db")
    db.row_factory = sqlite3.Row
    rows = db.execute(
        """SELECT dc.quest_id q, dc.talk_id t, dc.hash h, e.text_zh txt, s.speaker sp, s.role_type rt
           FROM dialogue_chapter dc JOIN entries e ON e.hash=dc.hash
           LEFT JOIN dialogue_speaker s ON s.talk_id=dc.talk_id AND s.hash=dc.hash
           WHERE dc.chapter_id=?""", (cid,)).fetchall()
    idx = []
    for r in rows:
        idx.append((norm(clean(r["txt"])), r))
    for line in open(path, encoding="utf-8"):
        s = line.strip()
        if not s or s.startswith("##"):
            continue
        key = norm(s)
        hit = None
        for k, r in idx:
            if key in k:
                hit = r
                break
        if hit:
            print("OK   [%s|talk %s|%s] %s" % (hit["q"], hit["t"], hit["sp"], s[:44]))
        else:
            print("MISS                                 %s" % s[:60])


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
