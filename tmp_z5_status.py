# -*- coding: utf-8 -*-
"""tmp_z5_status.py —— 队列 z5 的 skip/todo 精确核对"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
q = [l.strip() for l in open(os.path.join(HERE, "_batches", "queue_z5.txt"), encoding="utf-8") if l.strip()]
have, todo = [], []
for line in q:
    tag, old = line.split("|", 1)
    new = "narr_" + old
    (have if os.path.exists(os.path.join(HERE, "archives", new)) else todo).append((old, new))
print("SKIP %d:" % len(have))
for o, n in have:
    print("   ", o, "->", n)
print("TODO %d:" % len(todo))
for o, n in todo:
    print("   ", o, "->", n)
