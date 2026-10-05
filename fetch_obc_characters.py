# -*- coding: utf-8 -*-
"""D2-1: 观测枢官方分类校正层
拉取全部自机角色条目 → official_category/称号/所属/神之眼 入 kg_entities 校正池。
管线复用 v1.1 match_books.py 的观测枢 API 逆向（MEMORY.md 登记）。
速率控制：0.8s/请求（v1.1 实测单页快请求会撞反爬）。
"""
import json, os, time, urllib.request, urllib.parse

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "_obc_characters.json")

def _get(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Referer": "https://baike.mihoyo.com/"})
    return json.load(urllib.request.urlopen(req, timeout=20))

def search_all():
    """观测枢角色菜单 id=25（兹白样例实测）。按字母/拼音逐页枚举成本高，
    改用本地库角色名清单逐个搜索——123 名单已知，逆向枚举省掉。"""
    import glob
    names = [os.path.basename(f)[len("avatar_"):-3] for f in glob.glob(os.path.join(ROOT, "archives", "avatar_*.md"))]
    return sorted(set(names))

def fetch_one(name):
    try:
        r = _get("https://api-takumi.mihoyo.com/hoyowiki/genshin/wapi/search?keyword=" + urllib.parse.quote(name))
        items = r.get("data", {}).get("list", []) or []
        for it in items:
            clean = (it.get("name") or "").replace("<em>", "").replace("</em>", "")
            if clean == name:
                return {"name": name, "entry_page_id": it.get("entry_page_id"),
                        "menu_ids": [m.get("id") for m in (it.get("menus") or [])]}
        return {"name": name, "entry_page_id": None, "note": "未命中同名条目"}
    except Exception as e:
        return {"name": name, "error": str(e)}

def main():
    names = search_all()
    print(f"本地自机角色全集: {len(names)} 人")
    results = []
    for i, n in enumerate(names, 1):
        results.append(fetch_one(n))
        if i % 20 == 0:
            print(f"  {i}/{len(names)}")
        time.sleep(0.8)
    json.dump(results, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    hit = sum(1 for r in results if r.get("entry_page_id"))
    print(f"完成: 命中 {hit}/{len(results)}，落盘 {OUT}")

if __name__ == "__main__":
    main()
