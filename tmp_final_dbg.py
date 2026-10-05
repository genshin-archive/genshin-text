# -*- coding: utf-8 -*-
import sqlite3, re, sys
sys.path.insert(0, ".")
from tmp_final_qcheck import norm, seg_hit

db = sqlite3.connect("genshin_text.db")
for h in ("1314254618", "3308573642", "2847917842", "1712311898", "2818777930", "4224202738", "1016743914", "3586169682", "857920338"):
    rows = db.execute("SELECT id, text_zh FROM entries WHERE hash=?", (h,)).fetchall()
    print("hash", h, "rows", len(rows))
    for rid, tz in rows:
        print("   id=%s text=%r" % (rid, tz))
        print("   normeq:", norm(tz))
        # is it in fts?
        n = db.execute("SELECT rowid FROM fts WHERE rowid=?", (rid,)).fetchall()
        print("   in_fts_rows:", n)
