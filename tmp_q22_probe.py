# -*- coding: utf-8 -*-
import sqlite3
db = sqlite3.connect('genshin_text.db')
cols = [r[1] for r in db.execute('PRAGMA table_info(entries)')]
print('entries cols:', cols)
for kw in ['金钱流通的轨迹', '应当是金钱之主', '取而代之', '囤积者的私法']:
    print('===', kw)
    for r in db.execute('SELECT id, text_zh FROM entries WHERE text_zh LIKE ?', ('%' + kw + '%',)):
        print(r[0], repr(r[1][:160]))
