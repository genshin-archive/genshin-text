# -*- coding: utf-8 -*-
"""未挂名书籍文件 → 观测枢反查书名（wiki 仅作索引，正文必须双向匹配验证）"""
import io
import json
import re
import sqlite3
import time
import urllib.parse
import urllib.request

DB = r"C:\AI Programs\genshin-text\genshin_text.db"
OUT = r"C:\AI Programs\genshin-text\quest_book_map.json"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0",
      "Referer": "https://baike.mihoyo.com/"}
BASE = "https://api-takumi.mihoyo.com/hoyowiki/genshin/wapi"


def api_get(ep, **params):
    url = BASE + ep + ("?" + urllib.parse.urlencode(params) if params else "")
    req = urllib.request.Request(url, headers=UA)
    for i in range(3):
        try:
            return json.loads(urllib.request.urlopen(req, timeout=25).read().decode())
        except Exception as e:
            if i == 2:
                raise
            time.sleep(2)


def norm(s):
    s = re.sub(r"\s+", "", s or "")
    return re.sub(r"[「」『』《》()（）'\"…·~—\-！？，。：:；;【】\[\]<>＝=]", "", s)


def clean_rich(rt):
    t = re.sub(r"<br\s*/?>", "\n", rt or "")
    t = re.sub(r"<[^>]+>", "", t)
    return t.strip()


def make_query(text):
    """取正文中段特异句作搜索词"""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    # 过滤标记行
    cand = [ln for ln in lines
            if len(ln) >= 12
            and not ln.startswith(("<", "【", "——", "－", "=="))
            and "<" not in ln[:6]]
    if not cand:
        cand = [ln for ln in lines if len(ln) >= 12]
    if not cand:
        return None
    # 取中间位置的行（开头常见抬头格式）
    ln = cand[len(cand) // 3]
    ln = re.sub(r"[「」『』——…·]", "", ln).strip()
    return ln[:16] if len(ln) >= 10 else None


def entry_text(page):
    """entry_page → {module_name: text}"""
    out = {}
    for m in page.get("modules") or []:
        nm = (m.get("name") or "").strip()
        for c in m.get("components") or []:
            try:
                cj = json.loads(c.get("data") or "{}")
            except Exception:
                continue
            rt = cj.get("rich_text")
            if rt:
                out[nm] = clean_rich(rt)
                break
    return out


con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row
files = con.execute(
    """SELECT entry_id, text_zh, LENGTH(text_zh) AS n FROM entries
       WHERE category='书籍信件' AND (title IS NULL OR title='') AND LENGTH(text_zh) >= 300
       ORDER BY n DESC""").fetchall()
print(f"待识别文件（≥300字）: {len(files)}")

results, misses, errors = {}, {}, []
t0 = time.time()
for i, r in enumerate(files):
    eid, text = r["entry_id"], r["text_zh"]
    q = make_query(text)
    if not q:
        misses[eid] = "no query"
        continue
    try:
        d = api_get("/search", keyword=q, menu_id="0", page_num=1, page_size=8)
    except Exception as e:
        errors.append((eid, str(e)[:50]))
        time.sleep(1.5)
        continue
    objs = (d.get("data") or {}).get("list") or []
    matched = None
    for o in objs[:4]:
        try:
            ed = api_get("/entry_page", entry_page_id=o["entry_page_id"])
        except Exception:
            continue
        page = (ed.get("data") or {}).get("page") or {}
        mods = entry_text(page)
        ntext = norm(text)
        if len(ntext) < 30:
            break
        # 验证：库内文本前 60 字出现在条目正文里，或条目正文前 60 字出现在库内文本
        for nm, body in mods.items():
            nb = norm(body)
            if not nb:
                continue
            if ntext[:60] in nb or nb[:60] in ntext:
                matched = {"obc_id": o["entry_page_id"], "book": page.get("name", ""),
                           "vol": nm, "obc_name": o.get("name", "")}
                break
        if matched:
            break
        time.sleep(0.1)
    if matched:
        results[eid] = matched
        print(f"  HIT {eid} -> 《{matched['book']}》{matched['vol']}")
    else:
        misses[eid] = "no match"
    if (i + 1) % 50 == 0:
        print(f"  进度 {i+1}/{len(files)}, 命中 {len(results)}, 未中 {len(misses)}, {time.time()-t0:.0f}s")
    time.sleep(0.18)

io.open(OUT, "w", encoding="utf-8").write(
    json.dumps({"results": results, "misses": list(misses.keys()), "errors": errors},
               ensure_ascii=False, indent=1))
print(f"完成: 识别 {len(results)} / {len(files)}, 未中 {len(misses)}, 错误 {len(errors)}, 耗时 {time.time()-t0:.0f}s")
