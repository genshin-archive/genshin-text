# -*- coding: utf-8 -*-
"""统一导航栏注入：给所有页面装同一套 nav（高亮当前页）
用法: python unify_nav.py
"""
import os, re

ROOT = os.path.dirname(os.path.abspath(__file__))

NAV_CSS = """
/* ===== 统一导航栏（v3.0 整合） ===== */
#zg-nav{position:sticky;top:0;z-index:99;background:#1c1f26;border-bottom:1px solid #2b2f3a;
  padding:10px 20px;display:flex;gap:4px;align-items:center;font-family:"Microsoft YaHei",sans-serif;
  font-size:13.5px;flex-wrap:wrap;}
#zg-nav a{color:#8b93a7;text-decoration:none;padding:5px 12px;border-radius:6px;transition:all .15s;}
#zg-nav a:hover{color:#d8d2c4;background:#232838;}
#zg-nav a.cur{color:#e8dcc8;background:#2a3040;border:1px solid #3a4258;}
#zg-nav .brand{color:#e8dcc8;font-weight:600;margin-right:12px;font-size:14px;}
#zg-nav .brand::before{content:"✦ ";color:#c8a860;}
"""

NAV_HTML = """<nav id="zg-nav">
  <span class="brand">原神资料库 v3</span>
  <a href="/" data-p="home">检索</a>
  <a href="/browse.html" data-p="browse">章节浏览</a>
  <a href="/timeline.html" data-p="timeline">时间线</a>
  <a href="/kg.html" data-p="kg">知识层</a>
  <a href="/archive.html" data-p="archive">档案库</a>
  <a href="/hypothesis.html" data-p="hypo">假说库</a>
  <a href="/arbitration.html" data-p="arb">仲裁</a>
</nav>
<script>
(function(){
  var path = location.pathname;
  var cur = path === "/" || path === "/index.html" ? "home"
          : path.includes("browse") ? "browse"
          : path.includes("timeline") ? "timeline"
          : path.includes("kg") ? "kg"
          : path.includes("archive") ? "archive"
          : path.includes("hypothesis") ? "hypo"
          : path.includes("arbitration") ? "arb" : "";
  var a = document.querySelector('#zg-nav a[data-p="'+cur+'"]');
  if (a) a.classList.add("cur");
})();
</script>
"""

PAGES = {
    "index.html": "home",
    "browse.html": "browse",
    "timeline.html": "timeline",
    "kg.html": "kg",
    "archive.html": "archive",
    "hypothesis.html": "hypo",
    "arbitration.html": "arb",
}

def inject(fn):
    p = os.path.join(ROOT, fn)
    if not os.path.exists(p):
        print(f"  跳过 {fn}（不存在）")
        return
    s = open(p, encoding="utf-8").read()
    # 已有统一导航则先移除（幂等）
    s = re.sub(r"<nav id=\"zg-nav\">.*?</script>\n?", "", s, flags=re.S)
    s = s.replace(NAV_CSS, "")  # 清旧 css
    # 注入 CSS（</style> 前）与 HTML（<body> 后）
    if "</style>" in s:
        s = s.replace("</style>", NAV_CSS + "</style>", 1)
    else:
        s = s.replace("</head>", f"<style>{NAV_CSS}</style></head>", 1)
    if "<body>" in s:
        s = s.replace("<body>", "<body>\n" + NAV_HTML, 1)
    elif re.search(r"<body[^>]*>", s):
        s = re.sub(r"(<body[^>]*>)", r"\1\n" + NAV_HTML, s, count=1)
    open(p, "w", encoding="utf-8").write(s)
    print(f"  ✓ {fn}")

def main():
    print("注入统一导航:")
    for fn in PAGES:
        inject(fn)

if __name__ == "__main__":
    main()
