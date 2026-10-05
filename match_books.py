# -*- coding: utf-8 -*-
"""三方匹配：库内 Readable 正文 ↔ B wiki 卷 ↔ 观测枢卷 → book_map.json"""
import io
import json
import re
import sqlite3

DB = r"C:\AI Programs\genshin-text\genshin_text.db"


# 繁体→简体 常用字映射（wiki 抄录混入繁体字）
T2S = str.maketrans({t: s for t, s in {
    "飄": "飘", "塵": "尘", "甦": "苏", "缐": "线", "頑": "顽", "衝": "冲",
    "復": "复", "盡": "尽", "嘗": "尝", "讀": "读", "歷": "历", "鐘": "钟",
    "聲": "声", "幾": "几", "對": "对", "開": "开", "門": "门", "見": "见",
    "東": "东", "車": "车", "馬": "马", "畫": "画", "龍": "龙", "國": "国",
    "兒": "儿", "內": "内", "為": "为", "長": "长", "雲": "云", "絲": "丝",
    "來": "来", "萬": "万", "鳥": "鸟", "獸": "兽", "氣": "气", "風": "风",
    "飛": "飞", "與": "与", "於": "于", "嘯": "啸", "聽": "听", "遠": "远",
    "還": "还", "這": "这", "們": "们", "無": "无", "燈": "灯", "獵": "猎",
    "聞": "闻", "歲": "岁", "劍": "剑", "壓": "压", "銀": "银", "燦": "灿",
}.items()})


def norm(s):
    if not s:
        return ""
    s = re.sub(r"\s+", "", s)
    s = s.translate(T2S)
    s = s.replace("。", "").replace("、", "").replace("，", "").replace("．", "")
    s = re.sub(r"[「」『』《》()（）'\"…·~－—-]", "", s)
    s = s.replace("！", "").replace("？", "").replace(":", "").replace("：", "")
    return s


con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row
rows = con.execute(
    "SELECT id, entry_id, text_zh FROM entries WHERE category='书籍信件'").fetchall()
con.close()
lib = []
for r in rows:
    lib.append({"id": r["id"], "file": r["entry_id"], "text": r["text_zh"],
                "n": norm(r["text_zh"])})
print(f"库内书籍信件: {len(lib)} 条")

bili = json.load(io.open(r"C:\AI Programs\genshin-text\wiki_books_full.json", encoding="utf-8"))["books"]
obc = json.load(io.open(r"C:\AI Programs\genshin-text\obc_books_full.json", encoding="utf-8"))["books"]

# entry_id（文件名）→ {book, vol, src}
mapping = {}
matched_vols = 0
unmatched = []   # wiki 有、库内没匹配到
BOOK_ALIASES = {}  # 文件名(非BookN) 可能自带书名线索, 暂不处理


def match_lib(content):
    n = norm(content)
    if len(n) < 20:
        return None
    head = n[:60]
    for item in lib:
        if head and head in item["n"]:
            return item["file"]
    # 兜底1：库内正文前 60 字出现在 wiki 卷里
    for item in lib:
        h = item["n"][:60]
        if h and h in n:
            return item["file"]
    # 兜底2：fuzzy（wiki 抄录有错字/漏字时）
    from difflib import SequenceMatcher
    whead = n[:50]
    best, best_r = None, 0.0
    for item in lib:
        lhead = item["n"][:50]
        if len(lhead) < 20:
            continue
        sm = SequenceMatcher(None, whead, lhead)
        if sm.quick_ratio() < 0.7:
            continue
        r = sm.ratio()
        if r > best_r:
            best, best_r = item["file"], r
    if best is not None and best_r >= 0.75:
        return best
    return None


def clean_book(name):
    return re.sub(r"^《|》$", "", (name or "").strip())


def clean_vol(vol, book, idx):
    vol = (vol or "").strip()
    vol = re.sub(r"^《[^》]+》", "", vol)
    if "·" in vol:
        vol = vol.split("·", 1)[1].strip()
    if not vol or vol == book or vol in ("阅读", "正文", "内容", "书籍内容", "物品描述", "卡牌故事", "效果描述", "任务过程", "任务奖励"):
        vol = f"卷{idx + 1}" if idx else ""
    return vol


for source, books in (("bili", bili), ("obc", obc)):
    for b in books:
        book_name = clean_book(b.get("meta", {}).get("书籍名") or b.get("obc_name")
                               or b.get("wiki_title") or b.get("page"))
        for vi, v in enumerate(b.get("vols", [])):
            f = match_lib(v.get("content", ""))
            if f is None:
                unmatched.append({"src": source, "book": book_name, "vol": v.get("vol", ""), "head": norm(v.get("content", ""))[:40]})
                continue
            matched_vols += 1
            e = mapping.setdefault(f, {"book": book_name, "vols": {}, "sources": set()})
            vol = clean_vol(v.get("vol", ""), book_name, vi)
            if vol:
                e["vols"][f] = vol
            e["sources"].add(source)

print(f"wiki 卷匹配成功: {matched_vols}, 未匹配: {len(unmatched)}")
print(f"库内被命中的文件: {len(mapping)} / {len(lib)}")

out = {}
for f, e in mapping.items():
    # 卷名格式：《书名》·卷名
    vol = next(iter(e["vols"].values()), "")
    out[f] = {"book": e["book"], "vol": vol, "sources": sorted(e["sources"])}

io.open(r"C:\AI Programs\genshin-text\book_map.json", "w", encoding="utf-8").write(
    json.dumps(out, ensure_ascii=False, indent=1))
io.open(r"C:\AI Programs\genshin-text\book_unmatched.json", "w", encoding="utf-8").write(
    json.dumps(unmatched, ensure_ascii=False, indent=1))

# 样例
import itertools
for f, e in itertools.islice(out.items(), 6):
    print(f"  {f} -> 《{e['book']}》 {e['vol']} [{','.join(e['sources'])}]")
print("已写 book_map.json / book_unmatched.json")
