# -*- coding: utf-8 -*-
import sqlite3, sys
db=sqlite3.connect('genshin_text.db')
lo,hi=int(sys.argv[1]),int(sys.argv[2])
for i in range(lo,hi+1):
    rows=db.execute("SELECT field,hash,text_zh FROM entries WHERE source='Fetters' AND entry_id=?",(f"#{i}",)).fetchall()
    if not rows: continue
    title=txt=th=ch=None
    for f,h,t in rows:
        if f=='voiceTitle': title,th=t,h
        elif f=='voiceFileText': txt,ch=t,h
        elif f=='voiceTitleLocked': title=title or t
    print(f"##{i} [{title}] voice_hash={ch}")
    print("   ",(txt or '').replace('\n',' '))
