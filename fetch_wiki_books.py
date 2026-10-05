# -*- coding: utf-8 -*-
"""抓取 B 站原神 wiki 全部书籍页（批量 revisions 接口）→ wiki_books_full.json"""
import io
import json
import re
import time
import urllib.parse
import urllib.request

OUT = r"C:\AI Programs\genshin-text\wiki_books_full.json"
UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Referer": "https://wiki.biligame.com/ys/%E9%A6%96%E9%A1%B5",
    "Accept": "application/json",
}

titles = json.load(io.open(r"C:\AI Programs\genshin-text\wiki_bili_books.json", encoding="utf-8"))
print(f"书单 {len(titles)} 本")


def fetch_batch(batch):
    url = "https://wiki.biligame.com/ys/api.php?" + urllib.parse.urlencode({
        "action": "query", "prop": "revisions", "rvprop": "content", "rvslots": "main",
        "titles": "|".join(batch), "format": "json", "formatversion": "2"})
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.loads(r.read().decode("utf-8"))
    out = {}
    for p in d.get("query", {}).get("pages", []):
        if "missing" in p:
            out[p["title"]] = None
            continue
        rev = (p.get("revisions") or [{}])[0]
        wt = (rev.get("slots", {}).get("main", {}).get("content") or "")
        # 归一化标题键（api 可能返回规范化的标题）
        out[p["title"]] = wt
    return out


def split_template_params(wt):
    """从 '{{书籍' 开始拆顶层参数 → [(key, value)]"""
    depth, buf, parts = 0, "", []
    i = wt.index("{{书籍") + 2
    while i < len(wt):
        two = wt[i:i + 2]
        if two == "{{" or two == "[[":
            depth += 1
            buf += two
            i += 2
            continue
        if two == "}}" or two == "]]":
            if depth == 0 and two == "}}":
                parts.append(buf)
                break
            depth -= 1
            buf += two
            i += 2
            continue
        if two == "\n|" and depth == 0:
            parts.append(buf)
            buf = ""
            i += 2
            continue
        buf += wt[i]
        i += 1
    params = []
    for p in parts:
        if "=" in p:
            k, _, v = p.partition("=")
            params.append((k.strip().lstrip("|").strip(), v.strip()))
        else:
            params.append(("", p.strip()))
    return params


def clean(text):
    text = re.sub(r"<br\s*/?>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    return text.replace("&nbsp;", " ").strip()


books, failed = [], []
for off in range(0, len(titles), 20):
    batch = titles[off:off + 20]
    try:
        got = fetch_batch(batch)
    except Exception as e:
        failed.extend((t, str(e)[:80]) for t in batch)
        continue
    for t in batch:
        wt = got.get(t) or got.get(t.replace(" ", "_"))
        if not wt or "{{书籍" not in wt:
            failed.append((t, "no template" if wt is not None else "missing"))
            continue
        try:
            params = split_template_params(wt)
        except Exception as e:
            failed.append((t, f"parse: {str(e)[:60]}"))
            continue
        meta, vols = {}, []
        for k, v in params:
            if not k:
                continue
            m = re.match(r"卷(\d+)(名|内容|描述)$", k)
            if m:
                idx = int(m.group(1)) - 1
                while len(vols) <= idx:
                    vols.append({})
                vols[idx][{"名": "vol", "内容": "content", "描述": "desc"}[m.group(2)]] = clean(v)
            elif k in ("书籍名", "体裁", "实装版本", "国家", "稀有度"):
                meta[k] = clean(v)
        books.append({"page": t, "meta": meta,
                      "vols": [v for v in vols if v.get("content") or v.get("vol")]})
    print(f"  批次 {off}-{off+len(batch)} 完成, 累计 {len(books)} 本, 失败 {len(failed)}")
    time.sleep(1.5)

io.open(OUT, "w", encoding="utf-8").write(
    json.dumps({"books": books, "failed": failed}, ensure_ascii=False, indent=1))
total_vols = sum(len(b["vols"]) for b in books)
print(f"完成: {len(books)} 本 / {total_vols} 卷, 失败 {len(failed)}: {failed[:5]}")
