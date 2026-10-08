# -*- coding: utf-8 -*-
"""全量引文回查（v2 防错协议·制度1）

范围：archives/ 全部 853 份档案（arch/book/weapon/relic/avatar/frag*/misc）
     + timeline.md + hypothesis.md
规则：所有引号内文本（「」『』""）逐句回查：
  1. 优先回查 SQLite（entries FTS + dialogue_seq 关联），即"库内明文"层面
  2. 失配句再与所属叙事流导出（src_*.txt）模糊比对（跨章引用允许）
  3. 再失配 = 报警（可能是 paraphrase 补写、主语错误、或引用自库外来源）
输出：quote_check_report.md（逐文件失配清单，供人工复核分类）

失配不一定是错——档案允许引用 作者口述、跨文本联动、官方字幕文件名等
库外来源；本脚本只负责把"疑似补写"全部亮出来，分类判断交人工。
"""
import os, re, sqlite3, json, sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.abspath(__file__))
AR = os.path.join(ROOT, "archives")
DB = os.path.join(ROOT, "genshin_text.db")

# 摘录时常见的省略/连接噪声，比对前剔除
STRIP = re.compile("[…。，！？、\s「」『』“”‘’·—\-~！？。]")
# 引文切分：中英文引号内 >=6 字符
QUOTE = re.compile("[「『]([^「」『』]{6,})[」』]|[“]([^“”]{6,})[”]")

db = sqlite3.connect(DB)
db.execute("PRAGMA cache_size=-64000")

# 占位符/富文本归一化：{NICKNAME}=旅行者、{M#x}{F#y}=xy、<color> 标签剔除
RE_TAG = re.compile(r"<[^>]+>")
RE_M = re.compile(r"\{M#[^}]*\}")
RE_F = re.compile(r"\{F#[^}]*\}")
RE_NICK = re.compile(r"\{NICKNAME\}")
RE_LINK = re.compile(r"\{LINK#[^}]*\}")
RE_BRACE = re.compile(r"\{[^}]{0,30}\}")
RE_NOISE = re.compile(r"[#\n]")
# 中文引号类：norm 保留（与 FTS trigram 索引一致），比对层剔除
RE_Q = re.compile("[" + "\u300c\u300d\u300e\u300f\u201c\u201d\u2018\u2019" + "]")
def norm(s: str) -> str:
    s = RE_TAG.sub("", s)
    s = RE_M.sub("", s)          # {M#他} 整段剔除，避免性别错配
    s = RE_F.sub("", s)
    s = RE_NICK.sub("旅行者", s)
    s = RE_LINK.sub("", s)
    s = RE_BRACE.sub("", s)
    s = RE_NOISE.sub("", s)
    _PUNCTS = ''.join(chr(c) for c in [
        0x2026, 0x3002, 0xFF0C, 0xFF01, 0xFF1F, 0x3001, 0x300C, 0x300D,
        0x300E, 0x300F, 0x201C, 0x201D, 0x2018, 0x2019, 0x00B7, 0x2014,
        0xFF01, 0xFF1F, 0xFF08, 0xFF09,
    ])
    _ASCII = ''.join(chr(c) for c in [0x21, 0x3F, 0x2E, 0x2C, 0x3A, 0x3B, 0x7E, 0x23, 0x28, 0x29, 0x22, 0x27, 0x5C, 0x74])
    _RE_NOISE2 = re.compile('[' + re.escape(_ASCII + '\n\r\t ') + _PUNCTS + ']')
    s = _RE_NOISE2.sub('', s)
    return s

def loose(s: str) -> str:
    """比对层：在 norm 基础上再剔中文引号/空白，用于行内包含判断"""
    return RE_Q.sub("", norm(s))

def windows(frag: str, n=4, step=2):
    """frag 的 n 字滑窗（短探针，FTS trigram 友好：库文本引号断点不跨窗也能命中）"""
    if len(frag) <= n:
        return [frag] if frag else []
    out = [frag[i:i+n] for i in range(0, len(frag) - n + 1, step)]
    if not out:
        out = [frag]
    return out

def db_lookup(frag: str):
    """回查库内。返回 'full' | 'partial' | False
    full = 整段 loose 包含于某行；partial = 候选行上有 >=6 字连续重叠
    FTS 探针 OR 合并；4 字探针 0 命中时降级 3 字重试（3 字窗可跨全角标点断点，
    如「退海潮，立天衡」的 4 字窗"退海潮立"必 0 命中，3 字窗"退海潮"可中）。"""
    fn = loose(frag)
    if len(fn) < 6:
        return "full"  # 过短不判
    rows = None
    for n, step, limit in ((4, 2, 12), (3, 2, 12)):
        probes = windows(fn, n, step)[:limit]
        if not probes:
            continue
        query = " OR ".join('"%s"' % p for p in probes)
        try:
            rows = db.execute("SELECT rowid FROM fts WHERE fts MATCH ? LIMIT 400", (query,)).fetchall()
        except Exception:
            rows = db.execute("SELECT id FROM entries WHERE text_zh LIKE ? LIMIT 400", ("%"+probes[0]+"%",)).fetchall()
        if rows:
            break
    if not rows:
        return False
    ids = ",".join(str(r[0]) for r in rows)
    hit_count = 0
    for (tz,) in db.execute("SELECT text_zh FROM entries WHERE id IN (%s)" % ids):
        tn = loose(tz or "")
        if fn in tn:
            return "full"
        # partial 要求"长重叠"：候选行中连续命中 >=8 字（约 2 个相邻探针），
        # 避免编造句靠"天空岛上"这类常见词蹭出 partial
        best_run = 0
        run = 0
        for i in range(0, len(fn) - 3):
            if fn[i:i+4] in tn:
                run += 1
                best_run = max(best_run, run)
            else:
                run = 0
        if best_run >= 3:  # 连续 3 个 4 字窗 ≈ 6 字连续命中（措辞微差级）
            hit_count += 1
    if hit_count >= 2:
        return "partial"
    return False

# 叙事流导出缓存（跨章引用第二道比对）
_src_cache = {}
def src_text(cid):
    if cid not in _src_cache:
        p = os.path.join(AR, f"src_{cid}_" )
        hit = None
        for fn in os.listdir(AR):
            if fn.startswith(p) and fn.endswith(".txt"):
                hit = os.path.join(AR, fn); break
        _src_cache[cid] = open(hit, encoding="utf-8").read() if hit else ""
    return _src_cache[cid]

SRC_NORM = {}  # 141 章叙事流归一化全文拼接，跨章兜底比对
def src_all_norm():
    if not SRC_NORM:
        parts = []
        for fn in os.listdir(AR):
            if fn.startswith("src_") and fn.endswith(".txt"):
                parts.append(loose(open(os.path.join(AR, fn), encoding="utf-8").read()))
        SRC_NORM["all"] = "\n".join(parts)
    return SRC_NORM["all"]

def check_text(text, source_label, report, src_norm=""):
    quotes = QUOTE.findall(text)
    total = miss = partial = 0
    misses = []
    for a, b in quotes:
        q = (a or b).strip()
        frag = q
        if len(frag) < 6:
            continue
        total += 1
        hit = db_lookup(frag)
        if hit == "full":
            continue
        fn = loose(frag)
        # 第二道：本章叙事流
        if src_norm and (fn in src_norm or any(w in src_norm for w in windows(fn, 8))):
            continue
        # 第三道：全部叙事流（跨章引用）
        sa = src_all_norm()
        if fn in sa or any(w in sa for w in windows(fn, 8)):
            continue
        if hit == "partial":
            partial += 1
            continue
        miss += 1
        misses.append(q)
    report.append((source_label, total, miss, partial, misses))
    return total, miss

def main():
    report = []
    files = sorted(f for f in os.listdir(AR) if f.endswith(".md"))
    grand_t = grand_m = 0
    for fn in files:
        text = open(os.path.join(AR, fn), encoding="utf-8").read()
        src_norm = ""
        m = re.match(r"(arch|src)_(\d+)_", fn)
        if fn.startswith("arch_"):
            cid = fn.split("_")[1]
            p = os.path.join(AR, f"src_{cid}_")
            for f2 in os.listdir(AR):
                if f2.startswith(p) and f2.endswith(".txt"):
                    src_norm = loose(open(os.path.join(AR, f2), encoding="utf-8").read())
                    break
        check_text(text, fn, report, src_norm)
    # timeline / hypothesis
    for top in ("timeline.md", "hypothesis.md"):
        p = os.path.join(ROOT, top)
        if os.path.exists(p):
            check_text(open(p, encoding="utf-8").read(), top, report)

    # 输出报告
    lines = ["# 全量引文回查报告\n", "生成时间见文件 mtime；失配=四道比对全未命中。\n"]
    n_files_with_miss = 0
    for label, total, miss, partial, misses in report:
        grand_t += total; grand_m += miss
        if miss:
            n_files_with_miss += 1
            lines.append(f"\n## {label}（引文 {total}，失配 {miss}，{miss*100//max(total,1)}%）\n")
            for q in misses[:15]:
                lines.append(f"- 失配：{q[:60]}")
            if len(misses) > 15:
                lines.append(f"- …另有 {len(misses)-15} 条")
    lines.insert(2, "\n**总计：引文 %d 条，失配 %d 条（%d%%），涉及 %d 个文件**\n" % (grand_t, grand_m, grand_m * 100 // max(grand_t, 1), n_files_with_miss))
    out = os.path.join(ROOT, "quote_check_report.md")
    open(out, "w", encoding="utf-8").write("\n".join(lines))
    print(f"总计引文 {grand_t} 条，失配 {grand_m} 条（{grand_m*100//max(grand_t,1)}%），涉及 {n_files_with_miss} 个文件")
    print(f"报告：{out}")

if __name__ == "__main__":
    main()
