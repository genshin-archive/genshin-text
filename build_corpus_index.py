# -*- coding: utf-8 -*-
"""
build_corpus_index.py — Phase 0.5 语料分类层
对 genshin_text.db 的 entries（原始表，只读）建物化分类层 corpus_index。
可重复执行：每次 DROP 重建。

分类规则（master 2026-10-01 拍板 + 两处补充见注释）:
  1. category='TextMap原文' → is_mirror=1, semantic_type='镜像'
     （镜像行 entry_id 全为空，与下述前缀规则天然无冲突）
  2. entry_id 前缀（Readable 类）: Book%→书籍 Relic%→圣遗物故事
     Weapon%→武器故事 Costume%→衣装 Wings%→风之翼
  3. category='角色' AND source IN (FetterStory,Fetters,FetterInfo) → 角色资料
  4. source='Dialog' → 对话
     【补充规则】semantic_type 枚举含"对话"，但 Dialog 源全部挂在
     category='玩法配置' 下，若不单列则该枚举位永远为空。master 可否决。
  5. 过场字幕→字幕; 任务/MainQuest→任务文本; NPC→NPC文本
  6. 其余 semantic_type = category 原值
  entity_hints 本轮留空（NULL），后续 KG 实体归属填充。
"""
import sqlite3
import sys
import time

DB = "genshin_text.db"
BATCH = 200_000

CASE_EXPR = """
CASE
    WHEN category = 'TextMap原文' THEN '镜像'
    WHEN entry_id LIKE 'Book%'    THEN '书籍'
    WHEN entry_id LIKE 'Relic%'   THEN '圣遗物故事'
    WHEN entry_id LIKE 'Weapon%'  THEN '武器故事'
    WHEN entry_id LIKE 'Costume%' THEN '衣装'
    WHEN entry_id LIKE 'Wings%'   THEN '风之翼'
    WHEN category = '角色' AND source IN ('FetterStory','Fetters','FetterInfo')
                                  THEN '角色资料'
    WHEN source = 'Dialog'        THEN '对话'
    WHEN category = '过场字幕'     THEN '字幕'
    WHEN category IN ('任务','MainQuest') THEN '任务文本'
    WHEN category = 'NPC'         THEN 'NPC文本'
    ELSE category
END
"""


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    t0 = time.time()

    n_entries = cur.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
    print(f"[entries] 只读核数: {n_entries}")

    # 建表（若已存在则 DROP 重建）
    cur.execute("DROP TABLE IF EXISTS corpus_index")
    cur.execute(
        """
        CREATE TABLE corpus_index(
            entry_id INTEGER PRIMARY KEY,      -- entries.id
            hash TEXT,
            category TEXT,                      -- 原始 category
            semantic_type TEXT,                 -- 语义类型
            is_mirror INTEGER DEFAULT 0,        -- 是否 TextMap 原文镜像行
            entity_hints TEXT                   -- JSON 实体名提示，本轮留空
        )
        """
    )

    # 分批填充（按 entries.id 区间扫，单事务）
    inserted = 0
    cur.execute("BEGIN")
    lo = 0
    while lo < n_entries:
        hi = lo + BATCH
        cur.execute(
            f"""
            INSERT INTO corpus_index(entry_id, hash, category, semantic_type, is_mirror)
            SELECT id, hash, category,
                   {CASE_EXPR},
                   CASE WHEN category = 'TextMap原文' THEN 1 ELSE 0 END
            FROM entries
            WHERE id > ? AND id <= ?
            """,
            (lo, hi),
        )
        inserted += cur.rowcount
        lo = hi
        print(f"  batch .. {inserted} rows", flush=True)
    con.commit()

    # 索引
    cur.execute("CREATE INDEX idx_corpus_index_semantic ON corpus_index(semantic_type)")
    cur.execute("CREATE INDEX idx_corpus_index_mirror ON corpus_index(is_mirror)")
    con.commit()

    print(f"[done] corpus_index {inserted} rows, {time.time()-t0:.1f}s")

    # ---- 验证 ----
    total = cur.execute("SELECT COUNT(*) FROM corpus_index").fetchone()[0]
    print(f"\n=== corpus_index 总行数: {total} (entries: {n_entries}, 差: {total - n_entries}) ===")

    print("\n=== semantic_type 分布 ===")
    for st, c in cur.execute(
        "SELECT semantic_type, COUNT(*) AS n FROM corpus_index GROUP BY semantic_type ORDER BY n DESC"
    ).fetchall():
        print(f"{c:>9}  {st}")

    print("\n=== is_mirror 统计 ===")
    for m, c in cur.execute("SELECT is_mirror, COUNT(*) FROM corpus_index GROUP BY is_mirror"):
        print(f"is_mirror={m}: {c}")

    # 交叉自检：镜像标记与语义类型应当自洽
    bad = cur.execute(
        "SELECT COUNT(*) FROM corpus_index WHERE is_mirror=1 AND semantic_type!='镜像'"
    ).fetchone()[0]
    print(f"\n镜像自洽检查 (is_mirror=1 但 semantic_type!='镜像'): {bad} 行")
    bad2 = cur.execute(
        "SELECT COUNT(*) FROM corpus_index WHERE is_mirror=0 AND semantic_type='镜像'"
    ).fetchone()[0]
    print(f"镜像自洽检查 (is_mirror=0 但 semantic_type='镜像'): {bad2} 行")
    null_st = cur.execute(
        "SELECT COUNT(*) FROM corpus_index WHERE semantic_type IS NULL OR semantic_type=''"
    ).fetchone()[0]
    print(f"semantic_type 空值检查: {null_st} 行")

    # 抽查：镜像/书籍/武器故事各 3 + 角色资料/圣遗物故事/对话 各 1
    print("\n=== 抽查样本 ===")
    samples = []
    samples += cur.execute(
        "SELECT entry_id, category, semantic_type, is_mirror, substr(hash,1,12) FROM corpus_index "
        "WHERE is_mirror=1 AND hash IS NOT NULL AND hash!='' LIMIT 3"
    ).fetchall()
    for st in ("书籍", "武器故事", "圣遗物故事", "角色资料", "对话", "任务文本"):
        samples += cur.execute(
            "SELECT entry_id, category, semantic_type, is_mirror, substr(hash,1,12) "
            "FROM corpus_index WHERE semantic_type=? LIMIT 3",
            (st,),
        ).fetchall()
    for eid, cat, st, m, h in samples:
        print(f"  id={eid:<22} category={cat:<8} semantic={st:<8} mirror={m} hash={h}")

    # 抽查正文核对（取书/武器/镜像原文各 1 行的实际文本）
    print("\n=== 抽查正文 ===")
    for st in ("书籍", "武器故事", "镜像"):
        r = cur.execute(
            """
            SELECT c.entry_id, c.semantic_type, e.title, substr(e.text_zh,1,60)
            FROM corpus_index c JOIN entries e ON e.id=c.entry_id
            WHERE c.semantic_type=? AND e.text_zh IS NOT NULL AND e.text_zh!=''
            ORDER BY LENGTH(e.text_zh) DESC LIMIT 1
            """,
            (st,),
        ).fetchone()
        print(f"  [{st}] id={r[0]} title={r[2]!r}")
        print(f"        text: {r[3]}...")

    con.close()
    print("\n[OK] corpus_index 就绪")


if __name__ == "__main__":
    sys.exit(main())
