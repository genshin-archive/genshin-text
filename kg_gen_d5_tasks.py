# -*- coding: utf-8 -*-
"""D5 任务文件生成器：把 881 份档案分 5 批，生成 WorkBuddy 抽取任务书
抽取目标：从档案的"关系/事迹/别称"字段提取 claims JSON（不直写库）
输出格式（每个子代理产出）：
  kg_extract_batchX.json = [{"file":..., "subject":..., "alias":..., "quote":..., "source":..., "confidence":...}, ...]
灌库由 kg_load_extract.py 统一走三道闸（这是 D5 的质量关）。
"""
import os, glob, json

ROOT = os.path.dirname(os.path.abspath(__file__))
AR = os.path.join(ROOT, "archives")

def batch_files():
    files = sorted(glob.glob(os.path.join(AR, "*.md")))
    groups = {"G1": [], "G2": [], "G3": [], "G4": [], "G5": []}
    for f in files:
        b = os.path.basename(f)
        kind = b.split("_")[0]
        if kind in ("arch",):
            groups["G1"].append(b)
        elif kind == "avatar":
            groups["G2"].append(b)
        elif kind in ("book", "misc"):
            groups["G3"].append(b)
        elif kind in ("weapon", "relic"):
            groups["G4"].append(b)
        else:
            groups["G5"].append(b)  # frag/frag3/frag4/frag5/ent
    return groups

COMMON = """# 任务：从精读档案抽取知识断言（批次 {bid}）

工作目录：C:\\AI Programs\\genshin-text\\

## 任务说明
你负责的档案清单见 _batches/files_{bid}.txt（每行一个文件名，位于 archives/ 下）。
对每份档案，抽取**实体间关系断言**（不是全文复制！）：

1. 读档案的「别称映射表」「关系」「人际关系网」「事迹」等结构化字段
2. 对每条**带出处的断言行**，产出一条 JSON 记录：
   - file: 档案文件名
   - subject: 档案主实体名（# 标题里的名字，去掉括号注释）
   - alias: 【仅别称映射表行】别名文本｜出处｜置信（三段按 ｜ 拆开）
   - predicate_hint: 关系类型猜测（leader-of/enemy-of/ally-of/creates/steals/seals/possesses/descends-from/kin-of/betrays/knows-of/narrates/free）
   - object_text: 宾语（对方实体名或关系描述短语，≤40 字）
   - quote: 该行的逐字引文（「」内的原文，没有引文的行跳过）
   - source: 行内标注的出处（arch_xxx / Relic15045_3 / talk 701903 等）
   - confidence: 行内标注的置信（明文/明文·转述/推演/存疑）——没标的行按"明文"处理但要在 note 标"原文未标置信"
   - narrator: 明文·转述 时的叙述者名
3. 每份档案最多抽 12 条，优先抽**世界观级关系**（阵营/血统/权能/封印/背叛），跳过纯剧情流水
4. 产出到 kg_extract_batch{bid}.json（JSON 数组，UTF-8）

## 铁律
- quote 必须是档案里的逐字原文（会被自动回查数据库，篡改=整批作废）
- 不确定的一律标"存疑"，宁缺毋滥
- 不要发明档案里没有的关系

完成后回复：本批档案数、抽取条数、跳过数（无引文/纯流水）。
"""

def main():
    groups = batch_files()
    for bid, files in groups.items():
        with open(os.path.join(ROOT, "_batches", f"files_{bid}.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(os.path.basename(x) for x in files))
        task = COMMON.format(bid=bid)
        open(os.path.join(ROOT, "_batches", f"extract_{bid}.md"), "w", encoding="utf-8").write(task)
        print(f"{bid}: {len(files)} 份档案")

if __name__ == "__main__":
    main()
