# -*- coding: utf-8 -*-
"""E3 进度追踪：列出哪些块已完成（有 verdicts 文件）、哪些待跑"""
import os
import glob

B = r"C:\AI Programs\genshin-text\_batches"
batches = sorted(glob.glob(os.path.join(B, "e3_c*.jsonl")))
batches = [b for b in batches if "_verdicts" not in b]
done, todo = [], []
for b in batches:
    tag = os.path.basename(b).replace(".jsonl", "")
    v = os.path.join(B, f"{tag}_verdicts.jsonl")
    if os.path.exists(v):
        n = sum(1 for _ in open(v, encoding="utf-8"))
        done.append((tag, n))
    else:
        todo.append(tag)

print(f"总批次: {len(batches)} | 完成: {len(done)} | 待跑: {len(todo)}")
print(f"\n待跑清单（{len(todo)}）:")
for t in todo:
    print(f"  {t}", end="")
print()
