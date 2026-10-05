# -*- coding: utf-8 -*-
"""导出全部挂名书籍为一本一文件（多卷合并），供书籍精读档案使用"""
import sqlite3, os
from collections import OrderedDict

con = sqlite3.connect("genshin_text.db")
cur = con.cursor()
os.makedirs("books_text", exist_ok=True)

rows = cur.execute("""SELECT title, entry_id, text_zh FROM entries
WHERE category='书籍信件' AND title != '' ORDER BY title, entry_id""").fetchall()

books = OrderedDict()
for t, eid, txt in rows:
    bk = t.split("·")[0]
    books.setdefault(bk, []).append((t, eid, txt))

BAD = set('/\\:*?"<>|*《》')

def safe(b):
    return "".join(c for c in b if c not in BAD)

for bk, vols in books.items():
    fn = os.path.join("books_text", safe(bk) + ".txt")
    with open(fn, "w", encoding="utf-8") as f:
        for t, eid, txt in vols:
            f.write(f"===== {t} [{eid}] =====\n")
            f.write(txt.strip() + "\n\n")

n = len(os.listdir("books_text"))
total = sum(len(open(os.path.join("books_text", f), encoding="utf-8").read()) for f in os.listdir("books_text"))
print(f"导出 {len(books)} 本 -> {n} 个文件, 总字数 {total}")
