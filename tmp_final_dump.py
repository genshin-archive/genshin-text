# -*- coding: utf-8 -*-
"""临时工具：按章号导出完整说话人版叙事流（含 talk_id / hash / role_type），供精读归属核对。
用法：python tmp_final_dump.py <chapter_id>
"""
import sqlite3, os, re, sys

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


def main(cid):
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    name = cur.execute("SELECT name FROM chapters WHERE chapter_id=?", (cid,)).fetchone()
    name = name[0] if name else str(cid)
    rows = cur.execute(
        """SELECT d.quest_id AS q, e.text_zh AS txt, d.doc_order AS o, d.file_id AS fid,
                  d.talk_id AS tid, d.hash AS h, s.speaker AS sp, s.role_type AS rt, s.npc_id AS npc
           FROM dialogue_chapter d JOIN entries e ON e.hash=d.hash
           LEFT JOIN dialogue_speaker s ON s.talk_id=d.talk_id AND s.hash=d.hash
           WHERE d.chapter_id=?
           ORDER BY d.quest_id, d.doc_order, d.file_id""", (cid,)).fetchall()
    seen, last_q = set(), None
    out = []
    for r in rows:
        t = clean(r["txt"])
        if not t or (r["q"], t) in seen:
            continue
        seen.add((r["q"], t))
        if r["q"] != last_q:
            out.append("\n===== quest %s =====" % r["q"])
            last_q = r["q"]
        out.append("[%s|%s|%s|%s] {%s} %s" % (r["q"], r["tid"], r["h"], r["sp"], r["rt"], t))
    fn = os.path.join("_batches", "tmp_final_full_%s.txt" % cid)
    with open(fn, "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    print(name, len(out), "->", fn)


if __name__ == "__main__":
    main(sys.argv[1])
