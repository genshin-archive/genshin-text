# -*- coding: utf-8 -*-
"""tmp_lookup.py — 拉取角色逐字原文+hash，辅助 v1→v2 转换
用法:
  python tmp_lookup.py block <角色名>   # 定位 FetterStory 连续块（角色详细..神之眼）并全量打印
  python tmp_lookup.py voice <角色名>   # 打印该角色 FetterStory 块 + 语音块（初次见面..全部）
  python tmp_lookup.py find <子串>       # 全库 LIKE 搜索，返回 id/source/entry_id/field/hash/前120字
"""
import sys, sqlite3, os, re
DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "genshin_text.db")
db = sqlite3.connect(DB)

def clean(s):
    s = s or ""
    s = re.sub(r"<[^>]+>", "", s)
    s = s.replace("\\n", "\n    ")
    return s

def block(name):
    # find contiguous FetterStory storyContext rows containing name; get their entry_id
    ids = [r[0] for r in db.execute(
        "SELECT DISTINCT entry_id FROM FetterStories" if False else
        "SELECT DISTINCT entry_id FROM entries WHERE source='FetterStory' AND field='storyContext' AND text_zh LIKE ?",
        (f"%{name}%",))]
    rows = list(db.execute("SELECT entry_id, storyorder FROM (SELECT entry_id, MIN(id) AS storyorder FROM entries WHERE source='FetterStory' GROUP BY entry_id) ORDER BY storyorder"))
    # map entry_id -> min id
    order = list(db.execute("SELECT entry_id, MIN(id) FROM entries WHERE source='FetterStory' GROUP BY entry_id ORDER BY MIN(id)"))
    eids = set(ids)
    for i,(eid,_) in enumerate(order):
        if eid in eids:
            # print all rows in this block
            for r in db.execute("SELECT field, storyTitle, storyContext, hash, id FROM (SELECT field, text_zh AS storyTitle, '' AS storyContext, hash, id FROM entries WHERE source='FetterStory' AND entry_id=? AND field='storyTitle') ORDER BY id", (eid,)):
                pass
            print(f"\n##### BLOCK entry_id={eid} #####")
            titles = list(db.execute("SELECT id, text_zh, hash FROM entries WHERE source='FetterStory' AND entry_id=? AND field='storyTitle' ORDER BY id", (eid,)))
            ctxs = list(db.execute("SELECT id, text_zh, hash FROM entries WHERE source='FetterStory' AND entry_id=? AND field='storyContext' ORDER BY id", (eid,)))
            # pair by order
            for j in range(max(len(titles), len(ctxs))):
                t = titles[j] if j < len(titles) else ("?","(无标题)","?")
                c = ctxs[j] if j < len(ctxs) else ("?","(无正文)","?")
                print(f"\n== {t[1]}  [hash {t[2]} / ctx_hash {c[2]}] ==")
                print("   ", clean(c[1]))

def find(sub):
    for r in db.execute("SELECT id, source, entry_id, field, hash, text_zh FROM entries WHERE text_zh LIKE ? ORDER BY id LIMIT 30", (f"%{sub}%",)):
        print(f"id={r[0]} src={r[1]} eid={r[2]} field={r[3]} hash={r[4]}")
        print("   ", clean(r[5])[:200])

if __name__ == "__main__":
    mode = sys.argv[1]
    arg = sys.argv[2]
    if mode == "block":
        block(arg)
    elif mode == "find":
        find(arg)
    db.close()
