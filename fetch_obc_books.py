# -*- coding: utf-8 -*-
"""米游社观测枢书籍抓取：B wiki 书名 → 搜索配对 → entry_page 详情 → obc_books_full.json"""
import io
import json
import re
import time
import urllib.parse
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0",
      "Referer": "https://baike.mihoyo.com/"}
BASE = "https://api-takumi.mihoyo.com/hoyowiki/genshin/wapi"


def get(ep, **params):
    url = BASE + ep + ("?" + urllib.parse.urlencode(params) if params else "")
    req = urllib.request.Request(url, headers=UA)
    return json.loads(urllib.request.urlopen(req, timeout=25).read().decode())


def norm(s):
    return re.sub(r"[《》\s「」·']", "", s or "")


def strip_em(s):
    return (s or "").replace("<em>", "").replace("</em>", "").strip()


def fetch_entry(pid):
    d = get("/entry_page", entry_page_id=pid)
    page = (d.get("data") or {}).get("page") or {}
    vols = []
    for m in page.get("modules") or []:
        name = (m.get("name") or "").strip()
        if not name:
            continue
        body = ""
        for c in m.get("components") or []:
            raw = c.get("data") or ""
            try:
                cj = json.loads(raw)
            except Exception:
                continue
            rt = cj.get("rich_text")
            if rt:
                t = re.sub(r"<br\s*/?>", "\n", rt)
                t = re.sub(r"<[^>]+>", "", t)
                body = t.strip()
                break
        if body:
            vols.append({"vol": name, "content": body})
    return {"name": page.get("name", ""), "desc": page.get("desc", ""), "vols": vols}


wiki = json.load(io.open(r"C:\AI Programs\genshin-text\wiki_books_full.json", encoding="utf-8"))
titles = [b["page"] for b in wiki["books"]]
print(f"B wiki 书名 {len(titles)} 个，开始观测枢配对…")

out, failed = [], []
for i, t in enumerate(titles):
    key = norm(t)
    hit = None
    try:
        d = get("/search", keyword=t, menu_id="0", page_num=1, page_size=20)
        for o in (d.get("data") or {}).get("list") or []:
            nm = strip_em(o.get("name"))
            if norm(nm) == key:
                hit = o
                break
    except Exception as e:
        failed.append((t, "search: " + str(e)[:60]))
        time.sleep(1)
        continue
    if not hit:
        failed.append((t, "no match"))
        continue
    try:
        entry = fetch_entry(hit["entry_page_id"])
        out.append({"wiki_title": t, "obc_id": hit["entry_page_id"], "obc_name": entry["name"],
                    "obc_desc": entry["desc"], "vols": entry["vols"]})
    except Exception as e:
        failed.append((t, f"entry: {str(e)[:60]}"))
        time.sleep(1)
        continue
    if (i + 1) % 20 == 0:
        print(f"  {i+1}/{len(titles)}, 成功 {len(out)}, 失败 {len(failed)}")
    time.sleep(0.2)

io.open(r"C:\AI Programs\genshin-text\obc_books_full.json", "w", encoding="utf-8").write(
    json.dumps({"books": out, "failed": failed}, ensure_ascii=False, indent=1))
tv = sum(len(b["vols"]) for b in out)
print(f"完成: {len(out)} 本 / {tv} 卷, 失败 {len(failed)}: {failed[:6]}")
