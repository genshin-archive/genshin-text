# -*- coding: utf-8 -*-
"""archive_index — 精读档案归组排序（server.py 与 build_static.py 共用）
一级组：类型（任务章→传说章→世界任务→角色→书籍→碎片→武器→圣遗物→衣装→风之翼→实体→主题）
二级子组：任务章按篇章；碎片按篇章地域前缀；其余平铺
排序：任务类按章号数字；其余按章名
"""
import os
import re

# 类型显示顺序（key = front-matter 类型原值）
TYPE_ORDER = ["任务章", "传说章", "世界任务", "角色", "书籍", "碎片",
              "武器", "圣遗物", "衣装", "风之翼", "实体", "主题"]

def _front_matter(path):
    with open(path, encoding="utf-8") as f:
        s = f.read(800)
    m = re.match(r"^---\r?\n(.*?)\r?\n---", s, re.S)
    if not m:
        return {}
    d = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            d[k.strip()] = v.strip()
    return d

def _sort_num(item):
    n = item.get("num") or ""
    m = re.search(r"\d+", str(n))
    return int(m.group()) if m else 10**9

def _frag_group(chapter):
    m = re.match(r"碎片·([^（(]+)", chapter or "")
    return m.group(1).strip() if m else "其他"

def build_archive_index(archives_dir):
    buckets = {}  # type -> list of item
    for fn in sorted(os.listdir(archives_dir)):
        if not fn.endswith(".md"):
            continue
        d = _front_matter(os.path.join(archives_dir, fn))
        t = d.get("类型") or "其他"
        buckets.setdefault(t, []).append({
            "file": fn,
            "title": d.get("章名") or fn[:-3],
            "num": d.get("章号") or "",
            "chapter": d.get("篇章") or "",
        })

    groups = []
    known = [t for t in TYPE_ORDER if t in buckets]
    rest = sorted(t for t in buckets if t not in TYPE_ORDER)
    for t in known + rest:
        items = buckets[t]
        if t in ("任务章", "传说章", "世界任务"):
            items.sort(key=_sort_num)
        else:
            items.sort(key=lambda x: x["title"])
        subgroups = []
        if t == "任务章":
            seen = {}
            for it in items:
                seen.setdefault(it["chapter"] or "其他", []).append(it)
            # 子组按组内最小章号排
            order = sorted(seen, key=lambda ch: _sort_num(seen[ch][0]))
            subgroups = [{"title": ch, "items": seen[ch]} for ch in order]
        elif t == "碎片":
            seen = {}
            for it in items:
                seen.setdefault(_frag_group(it["chapter"]), []).append(it)
            subgroups = [{"title": ch, "items": sorted(seen[ch], key=lambda x: x["title"])}
                         for ch in sorted(seen)]
        else:
            subgroups = [{"title": "", "items": items}]
        groups.append({"key": t, "title": t, "count": len(items), "subgroups": subgroups})
    return {"groups": groups, "total": sum(g["count"] for g in groups)}

if __name__ == "__main__":
    import json
    base = os.path.dirname(os.path.abspath(__file__))
    idx = build_archive_index(os.path.join(base, "archives"))
    print(f"总档案 {idx['total']} 份，{len(idx['groups'])} 组")
    for g in idx["groups"]:
        subs = " / ".join(f"{s['title'] or '—'}({len(s['items'])})" for s in g["subgroups"][:4])
        more = "" if len(g["subgroups"]) <= 4 else f" …共{len(g['subgroups'])}子组"
        print(f"  {g['title']} {g['count']}: {subs}{more}")
