# -*- coding: utf-8 -*-
"""按章节导出叙事流文本 v2（对话流 + 说话人标注，quest 分隔），供精读档案使用。"""
import sqlite3, os, re, sys

DB = "genshin_text.db"
OUT = "archives"

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

def export(chapters=None, outdir=OUT):
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    if chapters is None:
        chapters = [r[0] for r in cur.execute(
            """SELECT c.chapter_id FROM chapters c
               JOIN dialogue_chapter d ON d.chapter_id=c.chapter_id
               GROUP BY c.chapter_id ORDER BY c.chapter_id""").fetchall()]
    os.makedirs(outdir, exist_ok=True)
    for cid in chapters:
        row = cur.execute("SELECT name FROM chapters WHERE chapter_id=?", (cid,)).fetchone()
        name = row[0] if row else str(cid)
        rows = cur.execute(
            """SELECT d.quest_id AS q, e.text_zh AS txt, d.doc_order AS o, d.file_id AS fid,
                      s.speaker AS sp
               FROM dialogue_chapter d JOIN entries e ON e.hash=d.hash
               LEFT JOIN dialogue_speaker s ON s.talk_id=d.talk_id AND s.hash=d.hash
               WHERE d.chapter_id=?
               ORDER BY d.quest_id, d.doc_order, d.file_id""", (cid,)).fetchall()
        # 同 hash 跨章重复引用导致同文同序重复：保留首现
        seen, lines, last_q = set(), [], None
        for r in rows:
            q, txt, sp = r["q"], r["txt"], r["sp"]
            t = clean(txt)
            if not t or (q, t) in seen:
                continue
            seen.add((q, t))
            if q != last_q:
                lines.append(f"\n===== quest {q} =====")
                last_q = q
            # 说话人标注：NPC/角色台词加【名字】前缀；系统文本/玩家文本不加
            if sp and sp != "旅行者" and not t.startswith("#") and not t.startswith("("):
                lines.append(f"【{sp}】{t}")
            else:
                lines.append(t)
        fn = os.path.join(outdir, f"src_{cid}_{name}.txt")
        with open(fn, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        print(f"{cid} {name}: {len(lines)} lines -> {fn}")

if __name__ == "__main__":
    export([int(x) for x in sys.argv[1:]] if len(sys.argv) > 1 else None)
