# -*- coding: utf-8 -*-
"""试点外部源核对：观测枢 + B站wiki 拉取关键人物/章节资料"""
import json, os, time, urllib.request, urllib.parse, re

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "_batches", "external_verify.json")

NAMES = ["菲林斯", "桑多涅", "奈芙尔", "哥伦比娅", "雷利尔", "索琳蒂丝", "空月之歌", "丝柯克"]

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

def get(url, referer=None, timeout=20):
    h = dict(UA)
    if referer: h["Referer"] = referer
    req = urllib.request.Request(url, headers=h)
    return urllib.request.urlopen(req, timeout=timeout)

def obc_search(name):
    try:
        u = "https://api-takumi.mihoyo.com/hoyowiki/genshin/wapi/search?keyword=" + urllib.parse.quote(name)
        r = json.load(get(u, referer="https://baike.mihoyo.com/"))
        items = r.get("data", {}).get("list", []) or []
        out = []
        for it in items:
            clean = (it.get("name") or "").replace("<em>", "").replace("</em>", "")
            out.append({"entry_page_id": it.get("entry_page_id"), "name": clean})
        return out[:5]
    except Exception as e:
        return [{"error": str(e)}]

def bili_wiki(name):
    """B站原神wiki：MediaWiki API 解析页面"""
    try:
        u = ("https://wiki.biligame.com/ys/api.php?action=parse&page=" + urllib.parse.quote(name)
             + "&prop=wikitext&format=json&redirects=1")
        r = json.load(get(u, referer="https://wiki.biligame.com/ys/"))
        if "error" in r:
            return {"exists": False, "note": r["error"].get("info", "")[:60]}
        wt = r.get("parse", {}).get("wikitext", {}).get("*", "")
        return {"exists": True, "len": len(wt), "wikitext_head": wt[:1500]}
    except Exception as e:
        return {"error": str(e)}

def main():
    results = {}
    for name in NAMES:
        entry = {"obc": obc_search(name)}
        time.sleep(0.7)
        entry["bili"] = bili_wiki(name)
        time.sleep(0.7)
        results[name] = entry
        obc_hit = any(x.get("entry_page_id") for x in entry["obc"])
        print(f"{name}: 观测枢{'✓' if obc_hit else '✗'} B站wiki{'✓' if entry['bili'].get('exists') else '✗'}")
    json.dump(results, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("落盘:", OUT)

if __name__ == "__main__":
    main()
