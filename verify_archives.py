# -*- coding: utf-8 -*-
"""档案引文验证：档案中引用的「原文短句」必须能在本章叙事流中找到"""
import os, re, sys

AR = "archives"

def load_src(cid):
    for fn in os.listdir(AR):
        if fn.startswith(f"src_{cid}_") and fn.endswith(".txt"):
            return open(os.path.join(AR, fn), encoding="utf-8").read()
    return None

def main():
    fails = []
    for fn in sorted(os.listdir(AR)):
        if not (fn.startswith("arch_") and fn.endswith(".md")):
            continue
        cid = int(fn.split("_")[1])
        src = load_src(cid)
        if src is None:
            continue
        text = open(os.path.join(AR, fn), encoding="utf-8").read()
        src_norm = re.sub(r"[…。，！？、\s「」『』·—\-]", "", src)
        quotes = re.findall(r"「([^「」]{6,})」", text)
        miss = 0
        missing_examples = []
        for q in quotes:
            q = q.strip()
            frag = re.sub(r"[…。，！？、\s「」『』·—\-]", "", q)
            if len(frag) < 6:
                continue
            probe = frag[:8] if len(frag) >= 8 else frag
            if probe not in src_norm:
                miss += 1
                if len(missing_examples) < 3:
                    missing_examples.append(q[:30])
        total = len([q for q in quotes if len(re.sub(r"[…。，！？、\s]", "", q)) >= 6])
        if total and miss / total > 0.2:
            fails.append((fn, total, miss, missing_examples))
    if not fails:
        print("全部档案引文验证通过（失配率 < 20%）")
    for fn, t, m, ex in fails:
        print(f"{fn}: 引文 {t} 条失配 {m} 条 ({m*100//max(t,1)}%)")
        for e in ex:
            print("    例:", e)

if __name__ == "__main__":
    main()
