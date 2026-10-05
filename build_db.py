# -*- coding: utf-8 -*-
"""原神全量文本建库：TextMap + ExcelBinOutput hash 展开 + Readable + Subtitle → SQLite FTS5"""
import json
import os
import re
import sqlite3
import sys
import time

ROOT = r"C:\AI Programs\genshin-text\AnimeGameData2"
DB = r"C:\AI Programs\genshin-text\genshin_text.db"

# 来源表前缀 → 中文类别
CATEGORY_RULES = [
    ("MainQuest", "任务"), ("Quest", "任务"), ("Talk", "对话"),
    ("Material", "物品"), ("Weapon", "武器"), ("Reliquary", "圣遗物"),
    ("Achievement", "成就"), ("Avatar", "角色"), ("Fetter", "角色"),
    ("Dungeon", "秘境"), ("Monster", "怪物"), ("Npc", "NPC"),
    ("Book", "书籍"), ("ManualTextMap", "图鉴说明"),
    ("GCG", "七圣召唤"), ("Homeworld", "尘歌壶"), ("HomeWorld", "尘歌壶"),
    ("Activity", "活动"), ("Scene", "场景"), ("Gadget", "装置"),
    ("City", "城市"), ("Area", "区域"), ("Bargain", "交易"),
    ("Cook", "烹饪"), ("Food", "食物"), ("Compound", "合成"),
    ("EyeOfStorm", "其他"), ("Weather", "天气"), ("Shop", "商店"),
]
DEFAULT_CATEGORY = "玩法配置"
HASH_RE = re.compile(r"^(.+?)TextMapHash$")


def category_of(table):
    for prefix, cat in CATEGORY_RULES:
        if table.startswith(prefix):
            return cat
    return DEFAULT_CATEGORY


def clean_table(table):
    """表名美化：去 ExcelConfigData 等后缀"""
    for suffix in ("ExcelConfigData.json", "ConfigData.json", "ExcelConfigData", "ConfigData"):
        if table.endswith(suffix):
            return table[: -len(suffix)]
    return table[:-5] if table.endswith(".json") else table


def entry_id_of(item, index):
    if isinstance(item, dict):
        for k in ("id", "Id", "ID", "configId", "talkId", "mainId"):
            if k in item:
                return str(item[k])
    return f"#{index}"


def walk_hashes(obj, out):
    """递归收集所有 <field>TextMapHash: value（值统一转 str，与 TextMap key 对齐）"""
    if isinstance(obj, dict):
        for k, v in obj.items():
            m = HASH_RE.match(k)
            if m and isinstance(v, (int, str)) and str(v).lstrip("-").isdigit():
                out.append((m.group(1), str(v)))
            else:
                walk_hashes(v, out)
    elif isinstance(obj, list):
        for v in obj:
            walk_hashes(v, out)


def iter_rows(cur):
    return cur


def main():
    t0 = time.time()
    print("加载 TextMap ...")
    def load(*parts):
        return json.load(open(os.path.join(ROOT, "TextMap", *parts), encoding="utf-8"))
    chs = load("TextMapCHS.json")
    med = load("TextMap_MediumCHS.json")
    en = {**load("TextMap_MediumEN.json"), **load("TextMapEN.json")}
    lookup_zh = {**med, **chs}   # 两套 hash 池合并，CHS 优先
    lookup_en = en
    print(f"  CHS {len(chs)} + Medium {len(med)} 条, EN 合并 {len(en)} 条, {time.time()-t0:.0f}s")

    if os.path.exists(DB):
        os.remove(DB)
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute("PRAGMA journal_mode=WAL")
    cur.execute("""
        CREATE TABLE entries(
            id INTEGER PRIMARY KEY,
            category TEXT, source TEXT, entry_id TEXT, field TEXT,
            hash TEXT, text_zh TEXT, text_en TEXT, title TEXT
        )""")
    cur.execute("""
        CREATE VIRTUAL TABLE fts USING fts5(
            text_zh, text_en, title,
            content='entries', content_rowid='id', tokenize='trigram'
        )""")

    def insert(rows):
        cur.executemany(
            "INSERT INTO entries(category, source, entry_id, field, hash, text_zh, text_en, title) "
            "VALUES(?,?,?,?,?,?,?,?)", rows)
        max_id = cur.execute("SELECT MAX(id) FROM entries").fetchone()[0]
        min_id = max_id - len(rows) + 1
        cur.execute(
            "INSERT INTO fts(rowid, text_zh, text_en, title) "
            "SELECT id, text_zh, text_en, title FROM entries WHERE id >= ?", (min_id,))
        con.commit()

    # ── 1. ExcelBinOutput 全表 hash 展开 ──
    batch, total = [], 0
    files = sorted(os.listdir(os.path.join(ROOT, "ExcelBinOutput")))
    for i, fn in enumerate(files):
        if not fn.endswith(".json"):
            continue
        p = os.path.join(ROOT, "ExcelBinOutput", fn)
        if os.path.getsize(p) > 150 * 1024 * 1024:
            print(f"  [跳过大文件] {fn}")
            continue
        try:
            with open(p, encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"  [解析失败] {fn}: {e}")
            continue
        if not isinstance(data, list):
            data = [data]
        table = clean_table(fn)
        cat = category_of(fn)
        for idx, item in enumerate(data):
            hs = []
            walk_hashes(item, hs)
            eid = entry_id_of(item, idx)
            for field, h in hs:
                zh = lookup_zh.get(h)
                if zh is None:
                    continue
                batch.append((cat, table, eid, field, str(h), zh, lookup_en.get(h, ""), ""))
        if len(batch) >= 20000:
            total += len(batch)
            insert(batch)
            print(f"  Excel 展开 {total} 行 ({i+1}/{len(files)} 张表) {time.time()-t0:.0f}s")
            batch = []
    if batch:
        total += len(batch)
        insert(batch)
    print(f"Excel 展开完成: {total} 行, {time.time()-t0:.0f}s")

    # ── 2. TextMap 全量原文（CHS + Medium 两池）──
    batch = []
    for pool, srcname in ((chs, "TextMap"), (med, "TextMapMedium")):
        for h, zh in pool.items():
            batch.append(("TextMap原文", srcname, "", "", str(h), zh, lookup_en.get(h, ""), ""))
            if len(batch) >= 20000:
                total += len(batch)
                insert(batch)
                batch = []
    if batch:
        total += len(batch)
        insert(batch)
    print(f"TextMap 全量完成, {time.time()-t0:.0f}s")

    # ── 3. Readable（书籍/信件，CHS）──
    book_map = {}
    bmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "book_map.json")
    if os.path.exists(bmp):
        book_map = json.load(open(bmp, encoding="utf-8"))
        print(f"  书名映射: {len(book_map)} 条")
    rdir = os.path.join(ROOT, "Readable", "CHS")
    batch = []
    for fn in sorted(os.listdir(rdir)):
        if not fn.endswith(".txt"):
            continue
        with open(os.path.join(rdir, fn), encoding="utf-8", errors="replace") as f:
            body = f.read()
        if not body.strip():
            continue
        key = fn[:-4]
        bm = book_map.get(key) or {}
        title = f"《{bm['book']}》" + (f"·{bm['vol']}" if bm.get("vol") else "") if bm else ""
        batch.append(("书籍信件", "Readable", key, "", "", body, "", title))
        if len(batch) >= 500:
            total += len(batch)
            insert(batch)
            batch = []
    if batch:
        total += len(batch)
        insert(batch)
    print(f"Readable 完成, {time.time()-t0:.0f}s")

    # ── 4. Subtitle（过场字幕 srt → 纯文本）──
    sdir = os.path.join(ROOT, "Subtitle", "CHS")
    srt_tag = re.compile(r"\{[^}]*\}|<[^>]*>")
    batch = []
    for fn in sorted(os.listdir(sdir)):
        if not fn.endswith(".srt"):
            continue
        with open(os.path.join(sdir, fn), encoding="utf-8", errors="replace") as f:
            raw = f.read()
        lines = [srt_tag.sub("", ln).strip()
                 for ln in raw.splitlines()
                 if ln.strip() and not ln.strip().isdigit() and "-->" not in ln]
        # 去连续重复行
        body = "\n".join(dict.fromkeys(lines))
        if not body:
            continue
        batch.append(("过场字幕", "Subtitle", fn[:-4], "", "", body, "", ""))
        if len(batch) >= 500:
            total += len(batch)
            insert(batch)
            batch = []
    if batch:
        total += len(batch)
        insert(batch)
    print(f"Subtitle 完成, {time.time()-t0:.0f}s")

    n = cur.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
    con.execute("ANALYZE")
    con.close()
    print(f"完成！共 {n} 行, 耗时 {time.time()-t0:.0f}s, 库大小 {os.path.getsize(DB)/1e6:.0f}MB")


if __name__ == "__main__":
    main()
