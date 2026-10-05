# -*- coding: utf-8 -*-
"""导出武器故事与圣遗物故事（Readable/CHS/Weapon*.txt, Relic*.txt）
   文件名挂上武器/圣遗物名（查 Excel 表 nameTextMapHash），一套一文件"""
import json, os, sqlite3

ROOT = r"C:\AI Programs\genshin-text\AnimeGameData2"
OUT_W = r"C:\AI Programs\genshin-text\weapons_text"
OUT_R = r"C:\AI Programs\genshin-text\relics_text"

con = sqlite3.connect(r"C:\AI Programs\genshin-text\genshin_text.db")
cur = con.cursor()

# TextMap 名称查询（双池）
name_cache = {}
def get_name(h):
    if not h:
        return ""
    h = str(h)
    if h not in name_cache:
        row = cur.execute("SELECT title, text_zh FROM entries WHERE hash=? AND field='name' LIMIT 1", (h,)).fetchone()
        row2 = row or cur.execute("SELECT title, text_zh FROM entries WHERE hash=? LIMIT 1", (h,)).fetchone()
        name_cache[h] = (row2[1] if row2 else "") or (row2[0] if row2 else "")
    return name_cache[h]

# 武器名映射
wmap = {}
for x in json.load(open(os.path.join(ROOT, "ExcelBinOutput", "WeaponExcelConfigData.json"), encoding="utf-8")):
    wmap[str(x.get("id"))] = get_name(x.get("nameTextMapHash"))

# 圣遗物套装名映射（Reliquary: suitId 由 Relic 文件名前 5 位推）
rmap = {}
try:
    for x in json.load(open(os.path.join(ROOT, "ExcelBinOutput", "ReliquaryExcelConfigData.json"), encoding="utf-8")):
        sid = str(x.get("setId") or x.get("EquipAffixId") or "")
        if sid and sid not in rmap:
            rmap[sid] = get_name(x.get("setNameTextMapHash") or x.get("nameTextMapHash"))
except Exception as e:
    print("relic map err", e)

os.makedirs(OUT_W, exist_ok=True)
os.makedirs(OUT_R, exist_ok=True)

def dump(srcdir, prefix, outdir, name_map, key_len):
    n = 0
    for f in sorted(os.listdir(srcdir)):
        if not (f.startswith(prefix) and f.endswith(".txt")):
            continue
        rid = f[len(prefix):].split("_")[0].split(".")[0]
        key = rid[:key_len]
        nm = name_map.get(key, "") or name_map.get(rid, "") or ""
        txt = open(os.path.join(srcdir, f), encoding="utf-8").read().strip()
        # 一套一文件：同名追加
        out = os.path.join(outdir, (nm or rid) + ".txt")
        fn = out.replace("/", "_").replace("\\", "_").replace(":", "_").replace("?", "_").replace('"', "_").replace("*", "_")
        with open(fn, "a", encoding="utf-8") as g:
            g.write(f"===== {f} [{nm or rid}] =====\n{txt}\n\n")
        n += 1
    return n

nw = dump(os.path.join(ROOT, "Readable", "CHS"), "Weapon", OUT_W, wmap, 0)
nr = dump(os.path.join(ROOT, "Readable", "CHS"), "Relic", OUT_R, rmap, 0)
print(f"武器故事 {nw} 篇 -> {len(os.listdir(OUT_W))} 个文件")
print(f"圣遗物故事 {nr} 篇 -> {len(os.listdir(OUT_R))} 个文件")
