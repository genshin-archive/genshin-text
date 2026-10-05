# -*- coding: utf-8 -*-
"""列出某段文本在库内的全部 (chapter, quest, talk, speaker) 记录。"""
import sqlite3, sys, re

BAD = re.compile(r"<color[^>]*>|</color>|<i>|</i>")


def clean(t):
    t = BAD.sub("", t or "")
    t = t.replace("{NICKNAME}", "旅行者")
    t = re.sub(r"\{M#([^}]*)\}\{F#([^}]*)\}", lambda m: m.group(1), t)
    t = re.sub(r"\{[^{}]*\}", "", t)
    return t


def norm(s):
    s = re.sub(r"<[^>]+>", "", s or "")
    s = re.sub(r"\{[^}]{0,40}\}", "", s)
    return re.sub(r"[\s\u3000]", "", s)


def run(seg):
    db = sqlite3.connect("genshin_text.db")
    db.row_factory = sqlite3.Row
    key = norm(seg)
    print("=== ", seg[:50])
    for r in db.execute("""SELECT dc.chapter_id ch, dc.quest_id q, dc.talk_id t, e.hash h,
                                  s.speaker sp, s.role_type rt, e.text_zh txt
                           FROM dialogue_chapter dc JOIN entries e ON e.hash=dc.hash
                           LEFT JOIN dialogue_speaker s ON s.talk_id=dc.talk_id AND s.hash=dc.hash"""):
        if key in norm(clean(r["txt"])):
            print("   ch=%s q=%s talk=%s hash=%s sp=%s rt=%s | %s" % (r["ch"], r["q"], r["t"], r["h"], r["sp"], r["rt"], r["txt"][:90]))


if __name__ == "__main__":
    for a in sys.argv[1:]:
        run(a)
