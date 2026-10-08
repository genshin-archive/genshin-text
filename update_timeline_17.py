# -*- coding: utf-8 -*-
"""v1.7 增量：至冬 1702/1703 精读成果补入时间线表"""
import sqlite3

DB = "genshin_text.db"
con = sqlite3.connect(DB)
cur = con.cursor()

# 修正既有事件（白沙皇时代全链）
cur.execute("UPDATE events SET detail=? WHERE title='白沙皇时代'", (
    "白沙皇唆使宫廷传令使与第三降临者打开深渊之门（千年深渊灾祸之源）→天理抹消传令使存在、白沙皇遁影域→"
    "第三登天空岛谈判以命换复活+承诺不害坎瑞亚人→尸身拆解七块巩固统治体系（=七颗神之心）→"
    "第三对天理许下最深诅咒，天理反制抹去世间关于他的一切→坎瑞亚灾变触发诅咒→天理沉睡",))

# 新增事件
NEW = [
    ("神之心=第三降临者遗骨", "「神之心是第三降临者的遗骨，不可能长期与地脉共存」（1702）与「尸身被拆解成七块，用来巩固天理所构建的统治体系」（1703）互证；女皇持六颗神之心可小范围改写世界规则（时间流速变慢）", "明文", "【明文·1702/1703】", "7.1 至冬主线", [(6, "白沙皇时代"), (8, "游戏7.1")]),
    ("三月持有生死时空权能", "「很久以前，世间『生』『死』『时』『空』的权能都属于『三月』，虹月分到了最多的『死』之权能」——三月早于四影持有四权能", "明文", "【明文·1703】", "7.1 至冬主线", [(2, "三月时代")]),
    ("虹月=赤月", "「『死』之权柄仍以另一种形式存在于提瓦特，存在于赤月以及赤月子民的血脉之中，『两界之火』便是佐证」；阿蕾奇诺=赤月遗民；深秘院五百年前起研究赤月", "明文", "【明文·1703】", "7.1 至冬主线", [(4, "三月尽逝后"), (8, "游戏7.1")]),
    ("若娜瓦败退·死之权能被回收", "至冬之战后天理回收其死之权能（越界惩戒：未经天理授意对至冬施加死之诅咒）", "明文", "【明文·1703】", "7.1 至冬主线", [(8, "游戏7.1")]),
    ("荧五百年前在天空岛", "海洛塔帝「召唤」的金发「王储」即荧；皮耶罗自述「正如我当年从天空岛『召唤』了派蒙，而同一时间海洛塔帝所『召唤』的…正是你的妹妹」——派蒙出自天空岛实锤", "明文", "【明文·1703】", "7.1 至冬主线", [(7, "约500年前")]),
    ("女皇名讳=安娜丝塔夏", "1702/1703 两处直接称呼「安娜丝塔夏女皇」；她被天理抹去「第三降临者」相关记忆后不信任自己的记忆；白沙皇曾为她讲述往事", "明文", "【明文·1702/1703】", "7.1 至冬主线", [(6, "白沙皇时代后"), (8, "游戏7.1")]),
]
title2id = {r[0]: r[1] for r in cur.execute("SELECT title, event_id FROM events").fetchall()}
nmax = cur.execute("SELECT MAX(event_id) FROM events").fetchone()[0]
for i, (t, d, m, e, s, ax) in enumerate(NEW, 1):
    if t in title2id:
        continue
    eid = nmax + i
    cur.execute("INSERT INTO events VALUES (?,?,?,?,?,?)", (eid, t, d, m, e, s))
    for axis, pos in ax:
        cur.execute("INSERT OR IGNORE INTO event_axis_map VALUES (?,?,?)", (eid, axis, pos))
    title2id[t] = eid

# 新增链接
LINKS = [
    ("白沙皇时代", "神之心=第三降临者遗骨", "因果", "尸身七块=神之心"),
    ("神之心=第三降临者遗骨", "女皇名讳=安娜丝塔夏", "同期", "女皇以遗骨增幅改写规则"),
    ("三月尽逝", "虹月=赤月", "因果", "虹月破碎赤影入渊海→赤月子民"),
    ("坎瑞亚灾变", "荧五百年前在天空岛", "同期", "灾变前后兄妹抵达/召唤线"),
]
for a, b, rel, note in LINKS:
    if a in title2id and b in title2id:
        cur.execute("INSERT INTO event_links (from_event,to_event,relation,note) VALUES (?,?,?,?)",
                    (title2id[a], title2id[b], rel, note))

# 新增隐喻
MET = [
    ("不死诅咒（双记载）", "a)海洛塔帝深秘院研究产物 b)若娜瓦奉天理判罚施加的永久诅咒", "明文·矛盾对", "1703 两处并存，待 作者裁断"),
    ("「黑王的审美」", "黑王（尼伯龙根特征解读继续成立）", "特征解读", "1703 莱茵多特语境"),
    ("「星之楔」/誊录棱晶/溯见之镜", "第三降临者力量的衍生器物，可规避部分提瓦特法则", "明文", "1702/1703"),
]
for m, t, lv, st in MET:
    cur.execute("INSERT INTO metaphors (metaphor,target,evidence_level,status) VALUES (?,?,?,?)", (m, t, lv, st))

con.commit()
print("events:", cur.execute("SELECT COUNT(*) FROM events").fetchone()[0])
print("axis_map:", cur.execute("SELECT COUNT(*) FROM event_axis_map").fetchone()[0])
print("links:", cur.execute("SELECT COUNT(*) FROM event_links").fetchone()[0])
print("metaphors:", cur.execute("SELECT COUNT(*) FROM metaphors").fetchone()[0])
