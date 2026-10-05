# -*- coding: utf-8 -*-
"""导出角色资料：角色故事（FetterStory）+ 好感度语音（Fetters）+ 基础信息（FetterInfo）
   一角色一文件，正文用 TextMap 双池反查"""
import json, os, sqlite3
from collections import OrderedDict

ROOT = r"C:\AI Programs\genshin-text\AnimeGameData2"
DB = r"C:\AI Programs\genshin-text\genshin_text.db"
OUT = r"C:\AI Programs\genshin-text\avatars_text"

con = sqlite3.connect(DB)
cur = con.cursor()

# TextMap 双池直查（比 entries 表快且全）
pool = {}
for fn in ("TextMapCHS.json", "TextMap_MediumCHS.json"):
    pool.update(json.load(open(os.path.join(ROOT, "TextMap", fn), encoding="utf-8")))
print(f"TextMap 池: {len(pool)}")

def T(h):
    if not h:
        return ""
    return pool.get(str(h), "")

# 角色名
avatars = json.load(open(os.path.join(ROOT, "ExcelBinOutput", "AvatarExcelConfigData.json"), encoding="utf-8"))
id2name = {str(a["id"]): T(a.get("nameTextMapHash")) for a in avatars}
id2name = {k: v for k, v in id2name.items() if v}

os.makedirs(OUT, exist_ok=True)
data = OrderedDict()  # avatarId -> {"name":…, "info":…, "stories":[], "voices":[]}

# 1. 基础信息（FetterInfo 124 条）
for x in json.load(open(os.path.join(ROOT, "ExcelBinOutput", "FetterInfoExcelConfigData.json"), encoding="utf-8")):
    aid = str(x.get("avatarId"))
    nm = id2name.get(aid)
    if not nm:
        continue
    d = data.setdefault(aid, {"name": nm, "info": [], "stories": [], "voices": []})
    title = T(x.get("avatarTitleTextMapHash"))
    detail = T(x.get("avatarDetailTextMapHash"))
    native = T(x.get("avatarNativeTextMapHash"))
    const = T(x.get("avatarConstellationBeforTextMapHash"))
    vision = T(x.get("avatarVisionBeforTextMapHash"))
    d["info"].append(f"称号：{title}（{detail}）｜所属：{native}｜命之座：{const}｜神之眼：{vision}")

# 2. 角色故事（FetterStory 974 条）
for x in json.load(open(os.path.join(ROOT, "ExcelBinOutput", "FetterStoryExcelConfigData.json"), encoding="utf-8")):
    aid = str(x.get("avatarId"))
    nm = id2name.get(aid)
    if not nm:
        continue
    d = data.setdefault(aid, {"name": nm, "info": [], "stories": [], "voices": []})
    title = T(x.get("storyTitleTextMapHash"))
    ctx = T(x.get("storyContextTextMapHash"))
    if title or ctx:
        d["stories"].append((title, ctx))
    t2 = T(x.get("storyTitle2TextMapHash"))
    c2 = T(x.get("storyContext2TextMapHash"))
    if t2 or c2:
        d["stories"].append((t2 + "（二段）", c2))

# 3. 语音（Fetters 9183 条）
for x in json.load(open(os.path.join(ROOT, "ExcelBinOutput", "FettersExcelConfigData.json"), encoding="utf-8")):
    aid = str(x.get("avatarId"))
    nm = id2name.get(aid)
    if not nm:
        continue
    d = data.setdefault(aid, {"name": nm, "info": [], "stories": [], "voices": []})
    vt = T(x.get("voiceTitleTextMapHash"))
    vc = T(x.get("voiceFileTextTextMapHash"))
    if vt or vc:
        d["voices"].append((vt, vc))

n = 0
for aid, d in data.items():
    fn = os.path.join(OUT, "".join(c for c in d["name"] if c not in '/\\:*?"<>|') + ".txt")
    with open(fn, "w", encoding="utf-8") as f:
        f.write(f"# {d['name']}（avatarId {aid}）\n\n")
        for info in d["info"]:
            f.write(info + "\n")
        if d["stories"]:
            f.write(f"\n===== 角色故事（{len(d['stories'])} 篇）=====\n")
            for t, c in d["stories"]:
                f.write(f"\n--- {t} ---\n{c}\n")
        if d["voices"]:
            f.write(f"\n===== 语音（{len(d['voices'])} 条）=====\n")
            for t, c in d["voices"]:
                f.write(f"\n[{t}]\n{c}\n")
    n += 1
total = sum(len(open(os.path.join(OUT, f), encoding="utf-8").read()) for f in os.listdir(OUT))
print(f"导出 {n} 个角色文件, 总字数 {total}")
print("样例:", sorted(os.listdir(OUT))[:8])
