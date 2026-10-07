# 原神文本资料库（genshin-text）

原神全量游戏文本的**本地检索 + 精读 + 知识层**工程。三层结构：

| 层 | 内容 | 规模 |
|---|---|---|
| **语料层** | SQLite FTS5 全文索引（任务/对话/物品/武器/圣遗物/成就/角色语音/书籍信件/过场字幕） | 123 万条，中英双语 |
| **精读层** | 按 STANDARD v1.0 重写的精读档案（叙事流/关键断言表/时间锚/隐喻代指/悬案） | 881 份 |
| **知识层** | 实体-断言知识图谱 + 结构化时间线（8 纪元 161 节点） | 6,716 实体 / 19,591 断言 |

## 快速开始

```powershell
# 1. 准备游戏数据（3.3G，不入库）
git clone --depth 1 https://gitlab.com/Dimbreath/AnimeGameData2.git AnimeGameData2

# 2. 建库（约 70s → genshin_text.db 约 1GB）
python build_db.py
python build_talk_map.py        # 对话出处映射（~7min）
python build_quest_map.py       # 任务章节映射（40s）

# 3. 启动 web（浏览器打开 http://127.0.0.1:9020）
python server.py
```

## Web 页面

| 路径 | 功能 |
|---|---|
| `/` | 全文检索（中英对照、类别筛选、关键词高亮、出处标注） |
| `/browse.html` | 按章节浏览——官方演出顺序（`dialogue_chapter.sort_key`），任务分组标题 |
| `/timeline.html` | 多轴时间线（8 纪元 / 161 节点，叙述模式标注：明文/回忆/预言/改写/矛盾对） |
| `/kg.html` | 知识层——实体查询、别名解析、断言列表（含置信度与引文） |
| `/archive.html` | 精读档案库（881 份，自研 markdown 渲染） |
| `/hypothesis.html` | 假说库 |
| `/arbitration.html` | 仲裁队列 |

## 目录结构

```
archives/              # 881 份精读档案（narr_*.md）+ 章节语料（src_*.txt）
  ├── narr_16xx_*.md   #   任务章（官方演出顺序）
  ├── narr_avatar_*    #   角色档案
  ├── narr_book_*      #   书籍精读
  └── narr_weapon_*    #   武器/圣遗物
avatars_text/ books_text/ fragments_text/ weapons_text/ relics_text/ misc_text/
                       # 分类文本导出（从库再生）
STANDARD.md            # 精读标准规范（档案模板 + 置信四级 + 完整性原则）
PROTOCOL.md            # 防错协议（P1-P11：主语消解/引文回查/名讳区分…）
DESIGN.md              # 知识层设计（三道闸 + 可信度防线）
STATUS.md              # 项目状态快照
CHANGELOG.md           # 版本日志
deploy/                # Docker 部署（Dockerfile + docker-compose）
```

## 工具链

| 脚本 | 作用 |
|---|---|
| `build_db.py` | 语料建库（TextMap 双池 + Excel 展开 + Readable + Subtitle → SQLite FTS5 trigram） |
| `build_dialogue_seq.py` / `build_dialogue_chapter.py` | 对话顺序与章节归属（BinOutput/Talk 扫描 → hash→talk→quest→chapter） |
| `build_dialogue_order.py` | **官方演出序重建**：sort_key = mainQuest序×talk触发序×文件内序 |
| `build_quest_play_order.py` | 章内任务演出序表（双源互证人工录入） |
| `check_claims.py` | 精读档案出厂闸（引文逐字回查 + 谓词词表 + 置信合规 + 七节结构） |
| `kg_schema.py` / `kg_reload.py` / `kg_api.py` | 知识层表结构 / 重灌器 / 三道闸入库 API |
| `kg_import_timeline.py` | 时间线结构化（timeline.md → kg_eras + kg_timeline_nodes） |
| `export_*.py` | 分类文本导出 |
| `fetch_*.py` / `match_books.py` | 外部源抓取（B wiki / 米游社观测枢）与书名映射 |

## 数据管线要点

- **TextMap 双池**：7.x 起文本分主池与 Medium 池（物品/武器/成就描述），须合并查询
- **entries 双行**：同一 hash 可能同时来自 Dialog 与 TextMap 源——按 hash join 时须钉 `MIN(id)`
- **演出序**：Talk 表 `beginCond`（QUEST_COND_STATE_EQUAL → subId → order）为官方触发序；
  章内任务序录于 `quest_play_order`（目前仅序章第一幕双源录入，其余章回退数字序）
- **引文纪律**：所有断言引文须逐字可回查（`check_claims.py`），置信四级硬边界
  （明文 / 明文·转述 / 推演 / 存疑），转述必须标注叙述者

## 部署

`deploy/` 内含 Dockerfile 与 compose（python:3.12-slim + uvicorn，DB 以卷挂载）。
前端资源全部相对路径，根路径部署与子路径反代（如 `/genshin/`）双兼容。

## 反馈与贡献

一切以**游戏内文本为唯一事实源**（解读分歧不算错误，会进假说库并列陈列）：

- 📝 **勘误** → [Issue 模板](https://github.com/genshin-archive/genshin-text/issues/new?template=errata.md)：请附任务名/书名 + 原文片段，有出处的反馈优先核实
- 💬 **考据讨论** → [Discussions](https://github.com/genshin-archive/genshin-text/discussions)
- 📖 反馈规矩与处理流程详见 [CONTRIBUTING.md](CONTRIBUTING.md)

## 数据来源

- 游戏文本：[Dimbreath/AnimeGameData2](https://gitlab.com/Dimbreath/AnimeGameData2)（GameData 镜像）
- 书名/角色外部验证：B 站 wiki + 米游社观测枢（双源交叉）

## 版权

游戏文本版权归米哈游所有；本仓库为文本整理与研究工具，存档的均为游戏内文本及基于其的
整理产物，不作商业用途。

---

*精读档案生成与审计动用了多引擎管线（ZCode / WorkBuddy / qoder / dsh），并经过三模型交叉审计
（GLM / Qwen3.8 / DeepSeek）+ master 人工校验；详情见 `CHANGELOG.md`。*
