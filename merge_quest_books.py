# -*- coding: utf-8 -*-
"""quest_book_map 后处理：剔玩家帖、非书重分类、书挂名入库"""
import io
import json
import re
import sqlite3
import time

DB = r"C:\AI Programs\genshin-text\genshin_text.db"
SRC = r"C:\AI Programs\genshin-text\quest_book_map.json"

data = json.load(io.open(SRC, encoding="utf-8"))["results"]

JUNK_BOOK = re.compile(r"【原神丨|考据|攻略|测评|盘点")  # 玩家帖特征，一律剔除
MEANINGLESS_VOL = {"阅读", "任务奖励", "背景故事", "趣闻", "相关故事", ""}
PREFIX_CAT = {"Weapon": "武器故事", "Costume": "衣装故事", "Wings": "风之翼", "Relic": "圣遗物故事"}


def clean_book(name):
    name = (name or "").strip()
    # 玩家帖剔除
    if JUNK_BOOK.search(name):
        return None
    return name


def split_vol(book, vol):
    """书名含卷号且 vol 无意义时，把卷号拆出来"""
    if vol:
        return book, vol
    m = re.search(r"^(.*?)·(卷?[一二三四五六七八九十\d]+(?:·.*)?)$", book)
    if m and len(m.group(1)) >= 2:
        return m.group(1), m.group(2)
    return book, ""


book_updates, cat_updates, dropped = {}, {}, []
for eid, e in data.items():
    book = clean_book(e.get("book", ""))
    if not book:
        dropped.append((eid, e.get("book", ""), "junk"))
        continue
    vol = (e.get("vol") or "").strip()
    if vol in MEANINGLESS_VOL:
        vol = ""
    if eid.startswith("Book"):
        book, vol = split_vol(book, vol)
        title = (f"《{book}》" if not book.startswith("《") else book)
        if vol:
            title += f"·{vol}"
        book_updates[eid] = title
    elif eid.split("_")[0].rstrip("0123456789") in PREFIX_CAT or any(eid.startswith(p) for p in PREFIX_CAT):
        cat = next(v for p, v in PREFIX_CAT.items() if eid.startswith(p))
        cat_updates[eid] = (cat, book)
    else:
        dropped.append((eid, book, "unknown prefix"))

print(f"书挂名 {len(book_updates)}, 非书重分类 {len(cat_updates)}, 剔除 {len(dropped)}")

con = sqlite3.connect(DB)
t0 = time.time()
for eid, title in book_updates.items():
    con.execute('UPDATE entries SET title=? WHERE entry_id=? AND category="书籍信件"', (title, eid))
for eid, (cat, name) in cat_updates.items():
    # 非书文件：类别改 + title 用条目名
    con.execute('UPDATE entries SET category=?, title=? WHERE entry_id=? AND category="书籍信件"', (cat, name, eid))
con.commit()
print(f"DB 更新 {time.time()-t0:.0f}s, FTS rebuild 中...")
con.execute("INSERT INTO fts(fts) VALUES('rebuild')")
con.commit()
print(f"rebuild {time.time()-t0:.0f}s")

# 同步 book_map.json（书籍类）
bm = json.load(io.open(r"C:\AI Programs\genshin-text\book_map.json", encoding="utf-8"))
for eid, title in book_updates.items():
    m = re.match(r"^《(.+?)》(?:·(.+))?$", title)
    if m:
        bm[eid] = {"book": m.group(1), "vol": m.group(2) or "", "sources": ["obc-reverse"]}
io.open(r"C:\AI Programs\genshin-text\book_map.json", "w", encoding="utf-8").write(
    json.dumps(bm, ensure_ascii=False, indent=1))
print("book_map 同步完成, 共", len(bm))

n, = con.execute("SELECT COUNT(*) FROM entries WHERE category='书籍信件' AND title != ''").fetchone()
con.close()
print(f"书籍信件挂名总数: {n}")
