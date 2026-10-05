# -*- coding: utf-8 -*-
"""D1-1: 知识层表骨架（kg_ 前缀，同库共生存，旧 events/time_axes 冻结不删）
设计依据 DESIGN.md v1.0（14 题+官方校正层+可信度五防线）
"""
import sqlite3, os

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "genshin_text.db")

SCHEMA = """
-- ============ 实体层 ============
CREATE TABLE IF NOT EXISTS kg_entities(
    eid INTEGER PRIMARY KEY,              -- 实体ID（内部自增）
    ent_code TEXT UNIQUE,                 -- 对外编号（ent_01 等，可空=自动分配）
    name TEXT NOT NULL,                   -- 主名
    official_category TEXT,               -- 官方分类：自机角色/NPC/魔神/仙人/执行机构/无官方分类（观测枢校正层）
    obc_entry_id TEXT,                    -- 观测枢 entry_page_id（有官方条目时必填）
    type TEXT,                            -- 神/人/天使/龙/文明/种族群像/器灵/场所
    status TEXT DEFAULT 'active',         -- active/merged/hidden
    merged_into INTEGER,                  -- 被合并到的 eid（仲裁裁决后）
    review_status TEXT DEFAULT '未复核',  -- master已校验/AI交叉复核/机验通过/未复核
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS kg_aliases(
    aid INTEGER PRIMARY KEY,
    eid INTEGER NOT NULL REFERENCES kg_entities(eid),
    alias TEXT NOT NULL,                  -- 别名/称号/代称
    lang TEXT DEFAULT 'zh',               -- zh/en
    confidence TEXT NOT NULL,             -- 明文/推演/存疑（P7 验证状态）
    evidence TEXT,                        -- 出处（archive 文件名 / entry_id / talk_id）
    UNIQUE(eid, alias, lang)
);
CREATE INDEX IF NOT EXISTS idx_alias_alias ON kg_aliases(alias);

-- ============ 断言层 ============
CREATE TABLE IF NOT EXISTS kg_claims(
    cid INTEGER PRIMARY KEY,
    subject_id INTEGER NOT NULL REFERENCES kg_entities(eid),
    predicate TEXT NOT NULL,              -- 受控谓词（kg_predicates）或 fallback:free
    object_text TEXT NOT NULL,            -- 宾语（实体名或自由文本）
    object_id INTEGER REFERENCES kg_entities(eid),  -- 宾语可解析为实体时填
    text_hash TEXT,                       -- 逐字引文的 entries.hash（可多条时存首个，完整引文在 quote）
    quote TEXT,                           -- 逐字引文原文
    source TEXT NOT NULL,                 -- 出处（entry_id / talk_id / archive 文件名）
    confidence TEXT NOT NULL,             -- 明文/明文·转述/推演/存疑（P2/P5）
    narrator TEXT,                        -- 转述链叙述者（confidence=明文·转述 时必填）
    review_status TEXT DEFAULT '未复核',
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_claim_subject ON kg_claims(subject_id);
CREATE INDEX IF NOT EXISTS idx_claim_object ON kg_claims(object_id);
CREATE INDEX IF NOT EXISTS idx_claim_hash ON kg_claims(text_hash);

-- ============ 受控谓词 ============
CREATE TABLE IF NOT EXISTS kg_predicates(
    pid TEXT PRIMARY KEY,                 -- leader-of 等英文 slug
    label_zh TEXT NOT NULL,               -- 中文名
    definition TEXT,                      -- 一句定义（何时可用）
    direction TEXT DEFAULT 'directed'     -- directed/symmetric
);

-- ============ 仲裁队列（Q7：AI 提案+master 独裁） ============
CREATE TABLE IF NOT EXISTS kg_arbitration(
    arid INTEGER PRIMARY KEY,
    kind TEXT NOT NULL,                   -- alias-merge/alias-split/new-entity/claim-check/conflict
    payload TEXT NOT NULL,                -- JSON：提案详情（双方证据并列）
    status TEXT DEFAULT 'pending',        -- pending/merged/split/uncertain/dismissed
    proposal TEXT,                        -- AI 推荐三态之一
    decided_by TEXT,                      -- master/自动
    decided_at TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

-- ============ 时间轴（Q10 两级） ============
CREATE TABLE IF NOT EXISTS kg_eras(
    era_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,                   -- 一、原生纪元 等
    ord INTEGER NOT NULL,                 -- 排序
    description TEXT,
    source TEXT                           -- timeline.md 版本锚
);

CREATE TABLE IF NOT EXISTS kg_timeline_nodes(
    nid INTEGER PRIMARY KEY,
    era_id INTEGER NOT NULL REFERENCES kg_eras(era_id),
    title TEXT NOT NULL,                  -- 可讲述的事件标题
    detail TEXT,                          -- 细节（含引文）
    text_hash TEXT,                       -- 核心引文 hash
    quote TEXT,
    source TEXT NOT NULL,
    narrative_mode TEXT DEFAULT '明文',   -- 明文/回忆/预言/倒流/改写/叠加/矛盾对/应验
    axes TEXT,                            -- JSON：{地表纪年:.., 白夜国纪年:.., 月相:..} 多轴
    claim_id INTEGER REFERENCES kg_claims(cid),
    ord INTEGER                           -- 纪元内排序
);
CREATE INDEX IF NOT EXISTS idx_node_era ON kg_timeline_nodes(era_id);

-- ============ 语料缺陷登记（Q18） ============
CREATE TABLE IF NOT EXISTS kg_corpus_caveats(
    cave_id INTEGER PRIMARY KEY,
    description TEXT NOT NULL,            -- 缺陷描述
    scope TEXT,                           -- 影响范围（表/字段/条数）
    severity TEXT DEFAULT '中',           -- 高/中/低
    status TEXT DEFAULT 'open',           -- open/fixed/wontfix
    found_date TEXT,
    reference TEXT                        -- CHANGELOG 版本或 issue 链接
);

-- ============ master 口述旁证（Q19） ============
CREATE TABLE IF NOT EXISTS kg_master_witness(
    wid INTEGER PRIMARY KEY,
    content TEXT NOT NULL,                -- master 口述内容
    related_entities TEXT,                -- JSON: [ent_code...]
    stated_at TEXT DEFAULT (datetime('now')),
    verify_status TEXT DEFAULT '待验证',  -- 待验证/已证实→迁timeline/已证伪/部分证实
    verify_note TEXT,                     -- 验证说明（后续文本比对结果）
    matched_text TEXT                     -- 后续命中/证伪的库内文本
);
"""

def main():
    db = sqlite3.connect(DB)
    db.executescript(SCHEMA)
    # 旧表冻结标注
    try:
        db.execute("ALTER TABLE events RENAME TO events_deprecated_v16")
        print("events → events_deprecated_v16")
    except Exception:
        print("events 已冻结或不存在")
    try:
        db.execute("ALTER TABLE time_axes RENAME TO time_axes_deprecated_v16")
        print("time_axes → time_axes_deprecated_v16")
    except Exception:
        print("time_axes 已冻结或不存在")
    db.commit()
    # 验证
    tables = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'kg_%' ORDER BY name")]
    print("kg_ 表:", tables)
    db.close()

if __name__ == "__main__":
    main()
