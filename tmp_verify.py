# -*- coding: utf-8 -*-
"""tmp_verify.py —— 预检候选引文是否逐字命中库内（复用 check_claims 逻辑）
用法：python tmp_verify.py "引文1" "引文2" ...
每条以去掉「」后的裸串传入；打印 HIT/MISS。
"""
import sys, os, sqlite3, importlib.util
spec = importlib.util.spec_from_file_location("cc", os.path.join(os.path.dirname(os.path.abspath(__file__)), "check_claims.py"))
cc = importlib.util.module_from_spec(spec); spec.loader.exec_module(cc)
db = sqlite3.connect(cc.DB)
for q in sys.argv[1:]:
    print(("HIT " if cc.seg_hit(db, q) else "MISS"), q[:60])
db.close()
