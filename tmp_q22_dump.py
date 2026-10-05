# -*- coding: utf-8 -*-
import sys, sqlite3
db = sqlite3.connect('genshin_text.db')
kws = sys.argv[1:]
for kw in kws:
    print('\n########## KW:', kw)
    for r in db.execute('SELECT id, text_zh FROM entries WHERE text_zh LIKE ? LIMIT 2', ('%' + kw + '%',)):
        print('--- entry', r[0])
        print(r[1])
