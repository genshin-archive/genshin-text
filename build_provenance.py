# -*- coding: utf-8 -*-
"""D1-4: 溯源指纹链生成器（Q15）
每次 build_db 后运行：python build_provenance.py
产出 _provenance/manifest.json —— 数据从哪来永远可答。
"""
import os, json, hashlib, sqlite3, subprocess, datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "AnimeGameData2")

def sha256_file(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()

def git_info(path):
    try:
        head = subprocess.run(["git", "-C", path, "log", "-1", "--format=%H|%ci|%s"],
                              capture_output=True, text=True, timeout=30).stdout.strip()
        dirty = subprocess.run(["git", "-C", path, "status", "--porcelain"],
                               capture_output=True, text=True, timeout=30).stdout.strip()
        return {"head": head.split("|")[0] if head else None,
                "date": head.split("|")[1] if head else None,
                "subject": head.split("|", 2)[2] if head else None,
                "dirty_files": len(dirty.splitlines()) if dirty else 0}
    except Exception as e:
        return {"error": str(e)}

def source_counts():
    """关键源目录文件计数（抽查级，不逐文件 hash——800MB 全量太慢，目录计数+关键文件指纹够定位）"""
    counts = {}
    for sub in ("TextMap/CHS", "TextMap/EN", "TextMap/MediumCHS", "ExcelBinOutput", "BinOutput/Talk"):
        p = os.path.join(SRC, sub)
        if os.path.isdir(p):
            counts[sub] = sum(len(fs) for _, _, fs in os.walk(p))
    return counts

def main():
    db = sqlite3.connect(os.path.join(ROOT, "genshin_text.db"))
    tables = {}
    for t in ("entries", "dialogue_seq", "dialogue_chapter", "dialogue_speaker", "talk_map",
              "kg_entities", "kg_aliases", "kg_claims", "kg_predicates",
              "kg_eras", "kg_timeline_nodes", "kg_arbitration",
              "kg_corpus_caveats", "kg_author_witness"):
        try:
            tables[t] = db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        except Exception:
            tables[t] = None
    db.close()

    manifest = {
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "source_git": git_info(SRC),
        "source_counts": source_counts(),
        "db_sha256": sha256_file(os.path.join(ROOT, "genshin_text.db")),
        "table_counts": tables,
        "builder": "build_db.py @ commit " + str(git_info(ROOT).get("head") or "?"),
    }
    # 历史链：manifests 逐次追加（带时间戳文件名），latest 固定指针
    outdir = os.path.join(ROOT, "_provenance")
    os.makedirs(outdir, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    with open(os.path.join(outdir, f"manifest_{stamp}.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
    with open(os.path.join(outdir, "manifest_latest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
    print("manifest 写入:", f"manifest_{stamp}.json")
    print(json.dumps({k: v for k, v in manifest.items() if k != "source_counts"}, ensure_ascii=False, indent=1)[:600])

if __name__ == "__main__":
    main()
