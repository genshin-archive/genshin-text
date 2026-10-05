# 资料库状态快照（v3.0 · 2026-10-03）

## 数据集（genshin_text.db）
| 层 | 规模 |
|---|---|
| entries（语料） | 1,231,365 行（TextMap 双池+Excel+Readable+字幕） |
| corpus_index（分类层） | 1,231,365 行（30 语义类 + 镜像标记 70%） |
| 精读档案 | archives/narr_*.md **881 份**（v3.0 全量重建，全 PASS） |
| 旧档案存档 | archives_v1/（881 份，可回滚） |
| kg_entities | **6,722**（语义实体） |
| kg_claims | **19,605**（明文 16,687 + 明文·转述 2,918） |
| kg_aliases | 1,218 |
| kg_eras / kg_timeline_nodes | 8 / 161 |

## 关键文件
- STANDARD.md（精读标准规范 v1.0——宪法）
- PROTOCOL.md（防错协议 P1-P11）
- check_claims.py（出厂闸：引文逐字+谓词+置信+结构）
- kg_reload.py（知识层重灌器）/ kg_api.py（三闸入库 API）
- CHANGELOG.md（v1.0→v3.0 全史）
- timeline.md / hypothesis.md（时间线/假说库）

## v3.0 里程碑
- 881 档案按新标准全量重写（版本锚/篇章/断言表/零遗漏）
- 三模型交叉审计（GLM/Qwen3.8/DSv4.1）+全量终验 881/881 PASS
- 知识层重建：断言主语实体化（6,722 实体）+谓词受控映射
- 时间线两级结构化（8 纪元/161 节点）

## 校验状态
- 档案：待 master 抽验（分批核对，已过三模型交叉审计）
- 知识层：机验通过（引文链+结构全过）；仲裁队列 0 积压
