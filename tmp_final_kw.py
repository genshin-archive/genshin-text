# -*- coding: utf-8 -*-
import sqlite3, sys, re
db = sqlite3.connect('genshin_text.db')
kw = sys.argv[1]
lim = int(sys.argv[2]) if len(sys.argv) > 2 else 40
rows = db.execute("SELECT e.hash, e.text_zh, e.source, e.entry_id, dc.quest_id, dc.chapter_id "
                  "FROM entries e JOIN dialogue_chapter dc ON dc.hash=e.hash "
                  "WHERE e.text_zh LIKE ? LIMIT ?", ("%" + kw + "%", lim)).fetchall()
print("dialogue hits:", len(rows))
for r in rows:
    print("  q=%s ch=%s hash=%s | %s" % (r[4], r[5], r[0], (r[1] or "")[:160]))
rows = db.execute("SELECT hash, text_zh, source, entry_id FROM entries WHERE text_zh LIKE ? LIMIT ?",
                  ("%" + kw + "%", lim)).fetchall()
print("all-entry hits:", len(rows))
for r in rows:
    print("  src=%s eid=%s hash=%s | %s" % (r[2], r[3], r[0], (r[1] or "")[:160]))
