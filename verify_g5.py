# -*- coding: utf-8 -*-
"""批次 G5 抽取结果独立回查：合并 9 个 part，逐条校验 quote 是否为档案逐字原文。"""
import json, os, glob, sys, collections

ROOT = os.path.dirname(os.path.abspath(__file__))
ARCH = os.path.join(ROOT, "archives")
PREDS = {"leader-of","enemy-of","ally-of","creates","steals","seals","possesses",
         "descends-from","kin-of","betrays","knows-of","narrates","free"}
CONFS = {"明文","明文·转述","推演","存疑"}

parts = sorted(glob.glob(os.path.join(ROOT, "kg_extract_batchG5_part*.json")))
records = []
for p in parts:
    with open(p, encoding="utf-8") as f:
        d = json.load(f)
    print(f"{os.path.basename(p)}: {len(d)}")
    records.extend(d)
print("TOTAL:", len(records))

# 缓存档案文本
cache = {}
def arch_text(fn):
    if fn not in cache:
        path = os.path.join(ARCH, fn)
        if not os.path.exists(path):
            cache[fn] = None
        else:
            with open(path, encoding="utf-8") as f:
                cache[fn] = f.read()
    return cache[fn]

bad_file, bad_quote, bad_pred, bad_conf, too_many = [], [], [], [], []
per_file = collections.Counter()
files_seen = set()
for i, r in enumerate(records):
    fn = r.get("file")
    files_seen.add(fn)
    per_file[fn] += 1
    t = arch_text(fn)
    if t is None:
        bad_file.append((i, fn)); continue
    q = r.get("quote")
    if not q or q not in t:
        bad_quote.append((i, fn, q))
    if r.get("predicate_hint") not in PREDS:
        bad_pred.append((i, fn, r.get("predicate_hint")))
    if r.get("confidence") not in CONFS:
        bad_conf.append((i, fn, r.get("confidence")))

for fn, c in per_file.items():
    if c > 12:
        too_many.append((fn, c))

print("\n-- 校验结果 --")
print("缺失档案记录:", len(bad_file))
for x in bad_file[:20]: print("   ", x)
print("引文失配:", len(bad_quote))
for x in bad_quote[:40]: print("   ", x[0], x[1], repr(x[2])[:120])
print("predicate 非法:", len(bad_pred))
for x in bad_pred[:20]: print("   ", x)
print("confidence 非法:", len(bad_conf))
for x in bad_conf[:20]: print("   ", x)
print("单档超 12 条:", len(too_many))
for x in too_many[:20]: print("   ", x)
print("\n覆盖档案数:", len(files_seen))

# 清单覆盖情况
with open(os.path.join(ROOT, "_batches", "files_G5.txt"), encoding="utf-8") as f:
    listed = [l.strip() for l in f if l.strip()]
missing = [x for x in listed if x not in files_seen]
print("清单未产出记录的档案数:", len(missing))
for x in missing: print("   ", x)

if not (bad_file or bad_quote or bad_pred or bad_conf or too_many):
    with open(os.path.join(ROOT, "kg_extract_batchG5.json"), "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=1)
    print("\n已写出 kg_extract_batchG5.json")
else:
    print("\n存在失配，未写出最终文件")
