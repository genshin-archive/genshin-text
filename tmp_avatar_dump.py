# -*- coding: utf-8 -*-
"""tmp_avatar_dump.py <角色名> —— 导出该角色 FetterStory(角色详细/故事1-5/特殊/神之眼) + Fetters(语音) 全文
用法：python tmp_avatar_dump.py 八重神子   （加 --only-story 只导故事）
"""
import sys, os, json, io, sqlite3

ROOT = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(ROOT, "genshin_text.db")
EX = os.path.join(ROOT, "AnimeGameData2/ExcelBinOutput")

def load(fn):
    return json.load(io.open(os.path.join(EX, fn), encoding="utf-8"))

def pretty(s):
    if not s:
        return s
    return s.replace("\\r\\n", "\n").replace("\\n", "\n").replace("\\r", "\n")

def main():
    name = sys.argv[1]
    db = sqlite3.connect(DB)
    H = {}  # hash -> text_zh
    def txt(h):
        if h not in H:
            r = db.execute("SELECT text_zh FROM entries WHERE hash=?", (str(h),)).fetchone()
            H[h] = pretty(r[0]) if r and r[0] else None
        return H[h]

    avatars = load("AvatarExcelConfigData.json")
    row = db.execute(
        "SELECT entry_id, text_zh FROM entries WHERE source='Avatar' AND field='name' AND text_zh=?",
        (name,)).fetchone()
    if row is None:
        row = db.execute(
            "SELECT entry_id, text_zh FROM entries WHERE source='Avatar' AND field='name' AND text_zh LIKE ? LIMIT 1",
            ('%' + name + '%',)).fetchone()
    aid = int(row[0]) if row else None
    if aid is None:
        print("NOT_FOUND", name); return 1
    print("#MATCH name=%s avatarId=%s" % (row[1], aid), file=sys.stderr)

    print("=" * 20, "FetterStory avatarId=%s" % aid, "=" * 20)
    for i, fs in enumerate(load("FetterStoryExcelConfigData.json")):
        if fs.get("avatarId") != aid:
            continue
        st = txt(fs.get("storyTitleTextMapHash", 0))
        sc = txt(fs.get("storyContextTextMapHash", 0))
        sc2 = txt(fs.get("storyContext2TextMapHash", 0))
        print("\n### [story #%d] %s" % (i, st or ""))
        print(sc or "(无)")
        if sc2:
            print("---- storyContext2 ----")
            print(sc2)

    if "--only-story" in sys.argv:
        return 0
    print("\n" + "=" * 20, "Fetters avatarId=%s" % aid, "=" * 20)
    for i, f in enumerate(load("FettersExcelConfigData.json")):
        if f.get("avatarId") != aid:
            continue
        vt = txt(f.get("voiceTitleTextMapHash", 0))
        vf = txt(f.get("voiceFileTextTextMapHash", 0))
        print("\n### [voice #%d] %s" % (i, vt or ""))
        print(vf or "(无)")
    return 0

sys.exit(main())
