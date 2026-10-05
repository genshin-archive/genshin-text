# -*- coding: utf-8 -*-
"""tmp_eval.py —— 逐句回查：读一个文件，抽出所有「…」段，走 check_claims.seg_hit 判命中。
用法：python tmp_eval.py <文件路径>
输出：ASCII 位串（1=命中 0=失配），每段长度 + unicode 转义前 60 字符。
"""
import sys, re
import check_claims as C

db = C.sqlite3.connect(C.DB)
t = open(sys.argv[1], encoding="utf-8").read()
segs = re.findall(r"「([^」]*)」", t)
bits = []
for i, s in enumerate(segs, 1):
    hit = C.seg_hit(db, s)
    bits.append("1" if hit else "0")
    esc = s.encode("unicode_escape").decode()[:60]
    print(f"Q{i} len={len(C.norm(s))} H={int(hit)} {esc}")
print("BITS=" + "".join(bits))
db.close()
