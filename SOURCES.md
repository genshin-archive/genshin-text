# 数据来源与验证说明

> 本文档回答三个问题：**数据从哪来**（来源）、**凭什么可信**（验证机制）、**出了错怎么查**（可复现与已知缺口）。
> 对应学术出版的「数据可用性声明（Data Availability Statement）」——任何人可据此独立复核本项目每一条结论。

---

## 一、最高原则

**游戏内文本是唯一事实源，且每条断言必须逐字可回查。**

- 档案（`archives/*.md`）与知识层（`kg_claims`）中的每一条判断，都必须附带**引文原文 + 出处**，且引文能在全文库中逐字命中
- 社区考据、wiki 二手资料、个人解读：仅作线索参考，**不作为任何断言的依据**
- 解读分歧不算错误（转入假说库并列陈列），详见 [CONTRIBUTING.md](CONTRIBUTING.md)

---

## 二、一级来源：游戏内文本（唯一事实源）

### 数据仓库

- **来源**：[Dimbreath/AnimeGameData2](https://gitlab.com/Dimbreath/AnimeGameData2)（GameData 镜像仓库）
- **版本**：7.1.0（更新于 2026-09-21）
- **获取**：sparse checkout 拉取，本仓库不含此数据（约 3.3 GB），按 [README 快速开始](README.md) 自行 clone 后建库

### 数据构成（入库路径）

| 数据集 | 路径 | 内容 | 入库规模 |
|---|---|---|---|
| TextMap 主池 | `TextMap/TextMapCHS.json` | 任务/对话/书籍正文（约 62 万条） | 全文索引 |
| TextMap 副池 | `TextMap/TextMap_MediumCHS.json` | 物品/武器/成就描述（约 24 万条，与主池 key 不相交） | 全文索引 |
| 配置表 | `ExcelBinOutput/`（2,200+ 张） | 任务定义、对话触发条件、任务演出序等 | 展开入库 |
| 对话流 | `BinOutput/Talk/` + `BinOutput/Quest/` | 对话顺序与任务归属的原始依据 | 映射入库 |
| 书籍信件 | `Readable/CHS/` | 游戏内可阅读文本 | 入库 |
| 过场字幕 | `Subtitle/CHS/` | 过场动画字幕 | 入库 |

**入库总量**：`entries` 表 **1,231,365 行**，SQLite FTS5 trigram 全文索引（本地库约 1 GB）。

### 复现步骤

```powershell
git clone --depth 1 https://gitlab.com/Dimbreath/AnimeGameData2.git AnimeGameData2
python build_db.py          # 建库（约 70s）
python build_talk_map.py    # 对话出处映射（约 7min）
python build_quest_map.py   # 任务章节映射（约 40s）
python build_dialogue_seq.py && python build_dialogue_chapter.py && python build_dialogue_order.py
```

### 更新策略

游戏版本更新后：`cd AnimeGameData2 && git pull` → 按上述顺序重建 → 重新过 `check_claims.py` 出厂闸 → 重建知识层与展示站。

---

## 三、二级来源：外部交叉验证（仅辅助，不作断言依据）

以下来源**只用于覆盖率校验与分类校正**，与游戏文本冲突时一律以游戏文本为准：

| 来源 | 用途 | 抓取时间 | 结果 |
|---|---|---|---|
| B 站 wiki | 书名映射（书籍名/卷名） | 2026-09-25 | 105 本 / 308 卷 |
| 米游社观测枢 wiki | 书名映射 + **实体官方分类（official_category）校正层** | 2026-09-25 | 81 本 / 236 卷 |

- **书名映射**：双源交叉后 299 个书籍/信件文件挂上《书名》·卷名（218 个双源确认 / 78 个仅 B wiki / 3 个仅观测枢）
- **官方分类校正层**：2026-09「兹白误分类」事故后引入——所有入库实体强制携带 `official_category` 字段（观测枢底表），未在底表中的实体显式标记「无官方分类」，禁止猜测

---

## 四、可信度的四层验证机制

| 层 | 机制 | 实现 |
|---|---|---|
| 1·引文链 | 每条断言引文**逐字可查** | `check_claims.py` 出厂闸：FTS trigram 探针 + 四层命中（src 池 → 多长度探针 → LIKE 兜底），含占位符归一化（`{NICKNAME}` 等） |
| 2·溯源链 | 每行文本可溯源到原始条目 | 文本 hash / entry_id 双锚定 → `entries` 表 → 来源表与字段（如 `talk 600914`） |
| 3·审计链 | 全量交叉审计 | 881 份档案经三模型独立审计（GLM / Qwen3.8 / DeepSeek），抓错即修，审计结论记录于 [CHANGELOG.md](CHANGELOG.md) |
| 4·终审 | 作者逐份校验 | 每份档案 front-matter 标注校验状态；历史事故（如说话人误归）均记录并修正 |

**置信四级**（写入档案与知识层）：

| 级别 | 含义 |
|---|---|
| 明文 | 游戏文本直接陈述 |
| 明文·转述 | 文本中是角色转述，**必须标注叙述者** |
| 推演 | 推论——只允许出现在「悬案/假说」节，不得进正文断言 |
| 存疑 | 证据冲突或来源不确定，显式标注 |

---

## 五、已知数据缺口与处理约定

诚实登记，不掩盖、不编造（PROTOCOL P5「空缺留白」）：

- **套装正文缺失**：个别圣遗物套装在数据源中无正文（如 `Relic15004` 凛冬霜心）→ 档案显式登记「原文缺失」，禁编造
- **空 hash 条目**：部分可阅读文本 hash 为空串 → 使用 entry_id 双锚定
- **字面 `\n` 残留**：部分文本含 JSON 转义残留 → 验证器统一归一化处理
- **双池盲区**：主池与副池 key 不相交，任何检索必须合并两池

---

## 六、版权与使用

- **游戏文本版权归米哈游（miHoYo / COGNOSPHERE）所有**。本项目为个人非商业性的文本整理与考据工具，引用游戏文本为考据性引用
- **本项目的整理产物**（精读档案、知识层、时间线、脚本代码、文档）采用
  **[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/deed.zh)**
  （署名—非商业性使用—相同方式共享 4.0 国际）许可——转载、引用、改编请遵守：**署名**（注明本项目仓库地址）、**非商业**、**相同方式共享**
- 完整法律文本见仓库根目录 [LICENSE](LICENSE)
- 含**游戏全量剧透**——浏览前请知悉

---

## 七、如何自行验证任意一条结论

1. **站内快查**：拿到档案中任一条断言的引文 → 在展示站 / 本地检索页面搜索该引文片段 → 命中原行即核对通过
2. **全流程复现**：按第二节步骤 clone 数据源并建库 → 运行 `python check_claims.py` 全量复检 → 逐条比对
3. **发现错误**：走 [勘误 Issue 模板](https://github.com/genshin-archive/genshin-text/issues/new?template=errata.md)——附上**任务名/书名 + 原文片段**，处理流程见 [CONTRIBUTING.md](CONTRIBUTING.md)

---

*本文档随数据版本更新；最近更新：2026-10-07（v7.1.0 数据集）*
