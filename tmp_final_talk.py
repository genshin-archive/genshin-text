# -*- coding: utf-8 -*-
"""按 quest + talk_id 顺序打印某章对话（doc_order 序）。
用法：python tmp_final_talk.py <chapter_id> [talk_id]
"""
import sqlite3, re, sys

DB = "genshin_text.db"
BAD = re.compile(r"<color[^>]*>|</color>|<i>|</i>")


def clean(t):
    if not t:
        return ""
    t = BAD.sub("", t)
    t = t.replace("{NICKNAME}", "旅行者")
    t = re.sub(r"\{M#([^}]*)\}\{F#([^}]*)\}", lambda m: m.group(1), t)
    t = re.sub(r"\{REALNAME\[ID\(1\)\|HOSTONLY\(true\)\]\}", "旅行者", t)
    t = re.sub(r"\{PLAYERAVATAR#[^}]*\}", "旅行者", t)
    t = re.sub(r"\{[^{}]*\}", "", t)
    return t.strip()


def main(cid, tid=None):
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    sql = ("SELECT d.quest_id q, d.talk_id t, d.doc_order o, d.file_id f, d.hash h, e.text_zh txt,"
           " s.speaker sp, s.role_type rt FROM dialogue_chapter d JOIN entries e ON e.hash=d.hash"
           " LEFT JOIN dialogue_speaker s ON s.talk_id=d.talk_id AND s.hash=d.hash"
           " WHERE d.chapter_id=? ")
    args = [cid]
    if tid:
        sql += " AND d.talk_id=? "
        args.append(tid)
    sql += " ORDER BY d.talk_id, d.doc_order, d.file_id"
    seen = set()
    lastt = None
    for r in cur.execute(sql, args):
        t = clean(r["txt"])
        if not t or (r["t"], t) in seen:
            continue
        seen.add((r["t"], t))
        if r["t"] != lastt:
            print("\n--- talk %s (quest %s) ---" % (r["t"], r["q"]))
            lastt = r["t"]
        print("[%s|%s|%s] %s" % (r["o"], r["f"], r["sp"], t))


if __name__ == "__main__":
    main(int(sys.argv[1]), sys.argv[2] if len(sys.argv) > 2 else None)
