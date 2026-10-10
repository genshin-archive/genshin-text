# -*- coding: utf-8 -*-
"""Temporary audit helper v3 for e3_c006 batch: 3-gram evidence retrieval."""
import json, re, sqlite3, difflib
from collections import defaultdict

BASE = r"C:\AI Programs\genshin-text"
con = sqlite3.connect(BASE + r"\genshin_text.db")
cur = con.cursor()

items = []
with open(BASE + r"\_batches\e3_c006.jsonl", encoding="utf-8-sig") as f:
    for line in f:
        line = line.strip()
        if line:
            items.append(json.loads(line))

qtitles = {}
cur.execute("SELECT quest_id, title FROM quest_titles")
for qid, t in cur.fetchall():
    qtitles[qid] = t

all_qids = set()
for it in items:
    all_qids |= set(int(x) for x in re.findall(r'quest\s*(\d+)', it.get('source', '')))

# quest -> list of (hash, text, speaker_set)
qrows = defaultdict(list)
for qid in all_qids:
    cur.execute("""SELECT DISTINCT e.text_zh, s.speaker
                   FROM talk_map t JOIN entries e ON e.hash=t.hash
                   LEFT JOIN dialogue_speaker s ON s.hash=t.hash
                   WHERE t.kind='Quest' AND t.quest_id=? AND e.text_zh IS NOT NULL AND e.text_zh!=''""", (qid,))
    qrows[qid] = [r for r in cur.fetchall()]
print("# quests:", len(qrows), "total rows:", sum(len(v) for v in qrows.values()))

def ngrams(s, n=3):
    # only over chinese/alnum runs
    out = set()
    for run in re.findall(r'[\u4e00-\u9fffA-Za-z0-9]+', s):
        for i in range(len(run) - n + 1):
            out.add(run[i:i+n])
    return out

def src_speakers(src):
    tail = src.split('·')[-1]
    if 'quest' in tail or 'quest' in src.split('·')[-1]:
        return []
    return [s.strip() for s in re.split(r'[/、]', tail) if s.strip()]

def evidence_for(qids, text, topn=14, limit_speaker=14):
    grams = ngrams(text)
    scored = []
    for qid in qids:
        for t, sp in qrows.get(qid, ()):
            if not t:
                continue
            tg = ngrams(t)
            inter = len(grams & tg)
            if inter >= 3:
                scored.append((inter, qid, sp, t))
    scored.sort(key=lambda x: -x[0])
    out = []
    seen = set()
    for inter, qid, sp, t in scored:
        k = t[:24]
        if k in seen:
            continue
        seen.add(k)
        out.append((inter, qid, sp, t))
        if len(out) >= topn:
            break
    return out

report = []
for it in items:
    cid = it['cid']
    src = it.get('source', '')
    quote = (it.get('quote') or '').strip()
    obj = it.get('object', '')
    subj = it.get('subject', '')
    qids = sorted(set(int(x) for x in re.findall(r'quest\s*(\d+)', src)))
    report.append(f"\n===== cid {cid} | {subj} | {src} | {it.get('confidence')}")
    report.append(f"OBJ: {obj}")
    if quote:
        ov = difflib.SequenceMatcher(None, obj, quote).ratio()
        report.append(f"QOVERLAP={ov:.2f} QUOTE: {quote}")
        # locate
        found = False
        pieces = [quote]
        for p in re.split(r'…+', quote):
            if len(p.strip()) >= 8:
                pieces.append(p.strip())
        for p in pieces:
            p2 = p.strip().strip('「」')
            if len(p2) < 8:
                continue
            cur.execute("SELECT hash, text_zh FROM entries WHERE text_zh LIKE ? LIMIT 2", ('%' + p2 + '%',))
            rows = cur.fetchall()
            for h, t in rows:
                cur.execute("SELECT DISTINCT quest_id FROM talk_map WHERE hash=?", (h,))
                tq = [r[0] for r in cur.fetchall()]
                sp = '/'.join(sorted(set(x[0] for x in cur.execute('SELECT speaker FROM dialogue_speaker WHERE hash=?', (h,)).fetchall() if x[0])))
                report.append(f"  HIT sp={sp} quests={tq}: {t}")
                found = True
            if rows:
                break
        if not found:
            report.append("  !! quote NOT FOUND")
    # speaker-filtered lines
    sps = src_speakers(src)
    if not quote:
        ev = evidence_for(qids, obj)
        for inter, qid, sp, t in ev:
            report.append(f"  EV{inter}[q{qid}][{sp}]: {t[:150]}")
        if sps:
            for sp in sps:
                lines = [(qid, s, t) for qid in qids for t, s in qrows.get(qid, ()) if s and (sp in s or s in sp)]
                if lines:
                    report.append(f"  -- speaker {sp} lines ({len(lines)}):")
                    seen = set()
                    for qid, s, t in lines[:14]:
                        if t[:20] in seen:
                            continue
                        seen.add(t[:20])
                        report.append(f"    [{qid}] {t[:120]}")

with open(BASE + r"\tmp_c006_audit.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(report))
print("written")
