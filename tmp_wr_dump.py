# -*- coding: utf-8 -*-
"""tmp_wr_dump.py —— 按 entry_id 前缀导出武器/圣遗物故事原文（v1→v2 转换用）
用法：python tmp_wr_dump.py Weapon11515 Relic14001 ...
"""
import sys, os, sqlite3

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "genshin_text.db")

def main():
    db = sqlite3.connect(DB)
    for eid in sys.argv[1:]:
        rows = list(db.execute(
            "SELECT entry_id, field, title, text_zh FROM entries "
            "WHERE entry_id = ? OR entry_id LIKE ? ORDER BY entry_id, id",
            (eid, eid + r"_%")))
        print("=" * 20, eid, "=" * 20)
        if not rows:
            print("(no rows)")
            continue
        for entry_id, field, title, text in rows:
            print(f"--- [{entry_id}] field={field!r} title={title!r}")
            print(text)
        print()

if __name__ == "__main__":
    main()
