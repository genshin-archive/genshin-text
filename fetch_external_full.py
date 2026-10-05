# -*- coding: utf-8 -*-
"""外部源正文抓取与事实对照"""
import json, os, time, urllib.request, urllib.parse, re

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "_batches", "external_verify_full.json")
ev = json.load(open(os.path.join(ROOT, "_batches", "external_verify.json"), encoding="utf-8"))

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

def get(url, referer=None, timeout=25):
    h = dict(UA)
    if referer: h["Referer"] = referer
    req = urllib.request.Request(url, headers=h)
    return urllib.request.urlopen(req, timeout=timeout)

def obc_page(pid):
    try:
        u = "https://api-takumi.mihoyo.com/hoyowiki/genshin/wapi/entry_page?entry_page_id=" + str(pid)
        r = json.load(get(u, referer="https://baike.mihoyo.com/"))
        page = r.get("data", {}).get("page", {})
        out = {"name": page.get("name"), "modules": [m.get("name") for m in page.get("modules", [])]}
        # 抓"基础信息"与"角色详细/人物简介"的文本
        texts = []
        for m in page.get("modules", []):
            for c in m.get("components", []):
                data = c.get("data")
                if isinstance(data, str) and len(data) > 30:
                    try:
                        j = json.loads(data)
                        for k, v in j.items():
                            if isinstance(v, list):
                                for item in v:
                                    if isinstance(item, dict):
                                        for kk, vv in item.items():
                                            if isinstance(vv, str) and len(vv) > 20:
                                                texts.append(re.sub(r"<[^>]+>", "", vv)[:300])
                            elif isinstance(v, str) and len(v) > 20 and k not in ("layout_",):
                                texts.append(re.sub(r"<[^>]+>", "", v)[:300])
                    except Exception:
                        pass
        out["texts"] = texts[:6]
        return out
    except Exception as e:
        return {"error": str(e)}

def bili_full(name):
    try:
        u = ("https://wiki.biligame.com/ys/api.php?action=parse&page=" + urllib.parse.quote(name)
             + "&prop=wikitext&format=json&redirects=1")
        r = json.load(get(u, referer="https://wiki.biligame.com/ys/"))
        wt = r.get("parse", {}).get("wikitext", {}).get("*", "")
        # 抽信息框关键行与正文前段
        info = {}
        for m in re.finditer(r"\|\s*([^=|]{1,12})\s*=\s*([^\n|]{1,80})", wt[:3000]):
            k, v = m.group(1).strip(), m.group(2).strip()
            if any(t in k for t in ("称号", "身份", "种族", "所属", "席位", "名字", "全名", "职位", "种别")):
                info[k] = v
        return {"len": len(wt), "info": info, "head": wt[:800]}
    except Exception as e:
        return {"error": str(e)}

def main():
    out = {}
    for name, entry in ev.items():
        rec = {}
        # 观测枢：取第一个命中的 entry_page_id
        pid = None
        for x in entry.get("obc", []):
            if x.get("entry_page_id"):
                pid = x["entry_page_id"]; break
        if pid:
            rec["obc_pid"] = pid
            rec["obc"] = obc_page(pid)
            time.sleep(0.8)
        # B站全文
        rec["bili"] = bili_full(name)
        time.sleep(0.8)
        out[name] = rec
        print(name, "done")
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("落盘:", OUT)

if __name__ == "__main__":
    main()
