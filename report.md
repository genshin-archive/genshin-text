# 书名映射三方验证报告（2026-09-25）

## 数据源

| 来源 | 规模 | 说明 |
|---|---|---|
| 本地解包 Readable/CHS | 1897 条 | 权威正文（游戏原文），以内部文件名存储 |
| B 站 wiki（Category:书籍） | 105 本 / 308 卷 | 民间 wiki，书页含各卷全文，批量 revisions 接口抓取 |
| 米游社观测枢 wiki（hoyowiki API） | 81 本 / 236 卷 | 官方 wiki，`/hoyowiki/genshin/wapi/search` + `entry_page` 逆向获得 |

## 交叉验证结果

- 匹配成功的 wiki 卷：**520 卷** → 库内 **299 个文件**挂上书名/卷名（title 列）。
- 书名双源共同确认：**77/105 本**；映射文件按来源：双源一致 218、仅 B wiki 78、仅观测枢 3。
  - 双源正文与库内游戏原文一致性高（前缀归一化匹配通过），有少量 wiki 抄录错字/繁体（"任然""飄荡"），由 fuzzy 匹配兜住。
- 观测枢未召回 24 本（多为新版本书籍观测枢无独立条目或搜索召回差异）。
- wiki 有内容但未匹配的卷：24 卷，其中 8 卷 wiki 未抄录正文（空卷）；16 卷中大部分为观测枢页面混入的
  卡牌故事/任务 module（非书籍正文，已排除），真正的文本差异遗留：
  《提瓦特游览指南·璃月篇》《嘟嘟可轰轰奇遇记》（wiki 为图片格式）等个案。
- 库内其余 1598 条"书籍信件"为任务信件、便签、单页文本——wiki 不系统性收录，无书名可挂，属正常。

## 观测枢 API 逆向记录（供后续更新复用）

- 搜索：`GET https://api-takumi.mihoyo.com/hoyowiki/genshin/wapi/search?keyword=&menu_id=&page_num=&page_size=`
- 条目详情：`GET .../wapi/entry_page?entry_page_id=N`（modules[].name=卷名，components[].data JSON 里 rich_text=正文）
- 书籍分类 menu_id=68；`entry_pages` 接口 menu_id=68 返回空（未解），书目以 B wiki 为底、观测枢按书名搜索配对。
- Nuxt bundle 逆向链：页面 → `/ys/obc/_nuxt/*.js` → `blackboardApiBase = apiHost + "/common/blackboard/" + APP_SIGN + "/v1"`、`wikiApiBase = apiHost + "/hoyowiki/genshin"`。

## 遗留事项

- 观测枢 `entry_pages`（menu_id=68）返回空，未拿到官方完整书单；如需补全可按书名逐本搜索探测。
- B wiki 抓取脚本 `fetch_wiki_books.py`（批量模式）、观测枢 `fetch_obc_books.py`、匹配 `match_books.py` 均保留，游戏更新后可重跑刷新映射。
