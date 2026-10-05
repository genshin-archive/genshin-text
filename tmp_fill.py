# -*- coding: utf-8 -*-
"""tmp_fill.py —— QUOTE 占位逐字回填（中文搬运走文件 IO，杜绝手抄丢字）。
用法：python tmp_fill.py <v1源文件> <narr目标文件>
把 narr 文件里的 QUOTE<n> 替换为 v1 第 n 个「…」原文（含「」，n 从 1 计）。
"""
import sys, re

v1 = open(sys.argv[1], encoding="utf-8").read()
quotes = re.findall(r"(「[^」]*」)", v1)
path = sys.argv[2]
t = open(path, encoding="utf-8").read()

def rep(m):
    n = int(m.group(1))
    if 1 <= n <= len(quotes):
        return quotes[n - 1]
    return m.group(0)

t2 = re.sub(r"QUOTE(\d+)", rep, t)
open(path, "w", encoding="utf-8").write(t2)
print("filled v1_quotes=%d" % len(quotes))
