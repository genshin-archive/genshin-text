# -*- coding: utf-8 -*-
"""tmp_z5_probe.py —— 验证引文跨行（库内字面 \\n）是否被判失配"""
import re, sqlite3, importlib.util, os, sys

spec = importlib.util.spec_from_file_location(
    "cc", os.path.join(os.path.dirname(os.path.abspath(__file__)), "check_claims.py"))
cc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cc)

db = sqlite3.connect(os.path.join(os.path.dirname(os.path.abspath(__file__)), "genshin_text.db"))
t = db.execute("SELECT text_zh FROM entries WHERE source='FetterStory' AND entry_id='#558' "
               "AND field='storyContext'").fetchone()[0]
print("norm:", cc.norm(t)[-90:])
cases = {
    "cross_line": "对于一名魔术助手而言，保持低调是一种职业素养。对于「家」里的孩子而言…隐匿于影，更是一种生存之道。",
    "single_line": "喝彩并非为她而起，掌声亦非为她而鸣。",
    "seg_join_q": "保持低调是一种职业素养』＋『隐匿于影，更是一种生存之道",
}
for k, v in cases.items():
    print(k, "->", cc.seg_hit(db, v.strip("「」『』")))
