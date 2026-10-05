# -*- coding: utf-8 -*-
"""check_claims.py —— 断言表自检脚本（worker 交稿前必须自跑清零）
用法：python check_claims.py <档案文件路径>
检查：front-matter 存在 / 断言表格式 / 引文逐字回查（归一化+拼接段切分）
输出：PASS 或 FAIL + 失配清单（exit code 1 = 不合格）
"""
import sys, os, re, sqlite3

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "genshin_text.db")
STRIP = re.compile("[\u2026\u3002\uff0c\uff01\uff1f\u3001\s\u300c\u300d\u300e\u300f\u201c\u201d\u2018\u2019\u00b7\u2014\-~\uff01\uff1f!\?.,:;\"'()（）\n\r#■]")
ALLOWED_PRED = set("""是 从属 别称 领袖 成员 创立 统辖 敌对 同盟 背叛 对抗 血亲 先祖 创造 位格继承 继位
持有权能 授予 窃取 封印 囚禁 持用 封存于 吸收 引发 参与 见证 死于 复活 幸存 位于 活跃于 抵达
知晓 转述 预言 信任 不信任 爱 崇拜 吃掉 消灭 迫害 撤销 影响 委托 施加 奉命 前置 解除 坐实 授意 阻截 唤醒 交换 会晤 瓜分 持有 复原 引导""".split())

RE_BRACE = re.compile(r"\{[^}]{0,40}\}")
def norm(s):
    s = re.sub(r"<[^>]+>", "", s or "")
    s = RE_BRACE.sub("", s)
    s = s.replace(chr(92) + "n", "")  # 字面反斜杠n（JSON 转义残留）
    return STRIP.sub("", s)

_SRC_POOL = None
def _src_pool():
    """全部 src_*.txt 叙事流的归一化文本池（懒加载一次）"""
    global _SRC_POOL
    if _SRC_POOL is None:
        import glob as _g
        parts = []
        for sf in _g.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)), "archives", "src_*.txt")):
            parts.append(norm(open(sf, encoding="utf-8", errors="ignore").read()))
        _SRC_POOL = chr(10).join(parts)
    return _SRC_POOL

def seg_hit(db, seg):
    fn = norm(seg)
    if len(fn) < 5:
        return True
    if fn in _src_pool():
        return True  # src 叙事流层（DB 无逐字行的合法引用源）
    cand = set()
    for n_ in (4, 3):  # 多长度探针全部累加（禁提前 break）
        for i in range(0, max(len(fn) - n_ + 1, 1)):
            w = fn[i:i+n_]
            # 走 FTS5 trigram 索引（候选集与 entries 全表 LIKE 等价，已抽样 120 组验证；
            # 全表 LIKE 在 1.2M 行库上需数分钟/文件，FTS 版 <2 秒）
            for (rid,) in db.execute("SELECT rowid FROM fts WHERE text_zh LIKE ? LIMIT 300", (f"%{w}%",)):
                cand.add(rid)
    for rid in cand:
        tz = db.execute("SELECT text_zh FROM entries WHERE id=?", (rid,)).fetchone()[0]
        if fn in norm(tz or ""):
            return True
    return False

def main(path):
    errs = []
    t = open(path, encoding="utf-8").read()
    # 1) front-matter
    if not t.startswith("---") or "档案ID" not in t[:400]:
        errs.append("front-matter 缺失")
    # 2) 七节结构
    for sec in ("一、", "二、关键断言", "三、时间锚", "六、悬案", "七、"):
        if sec not in t:
            errs.append(f"缺章节：{sec}")
    # 3) 断言表逐行
    m = re.search(r"## 二、关键断言.*?\n(\|(?:[^\n]+\n)+)", t, re.S)
    if not m:
        errs.append("断言表未找到")
    else:
        db = sqlite3.connect(DB)
        for line in m.group(1).strip().split("\n"):
            cells = [c.strip() for c in line.split("|")]
            if len(cells) < 7 or cells[1] in ("主语", "") or set(cells[1]) <= {"-", " "}:
                continue
            subj, pred, obj, conf, quote = cells[1], cells[2], cells[3], cells[4], cells[5]
            if subj.startswith("（") and "无正文" in subj:
                continue  # 数据层缺失登记行，非断言
            if pred not in ALLOWED_PRED and not pred.startswith("自定义") and not pred.startswith("free:"):
                errs.append(f"谓词非词表: {pred}")
            conf_base = conf.split("（")[0].strip()
            if conf_base not in ("明文", "明文·转述", "明文·外部源", "推演", "存疑"):
                errs.append(f"置信非法: {conf}")
            if conf_base == "明文·转述" and "叙述者" not in conf:
                errs.append(f"转述缺叙述者: {subj}")
            q = quote.strip()
            if q in ("—", "-", ""):
                continue  # 外部源行无引文，放行
            if not (q.startswith("「") and q.endswith("」")):
                if not q.startswith("【摘要"):
                    errs.append(f"引文列非法（应「」或【摘要）: {subj} | {q[:30]}")
                continue
            # 拼接切分逐段验证
            segs = [x for x in re.split(r"」\s*[＋+]?\s*[「『]|』\s*[＋+]?\s*[「『]", q) if norm(x)]
            for seg in segs:
                s = seg.strip()
                s = s[1:-1] if s.startswith(("「", "『")) and s.endswith(("」", "』")) else s
                if not seg_hit(db, s):
                    errs.append(f"引文失配: {subj} | {s[:44]}")
        db.close()
    if errs:
        print("FAIL")
        for e in errs:
            print("  -", e)
        sys.exit(1)
    else:
        print("PASS")
        sys.exit(0)

if __name__ == "__main__":
    main(sys.argv[1])
