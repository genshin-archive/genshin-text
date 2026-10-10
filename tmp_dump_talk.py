import sqlite3, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

con = sqlite3.connect(r'C:\AI Programs\genshin-text\genshin_text.db')
cur = con.cursor()

talk_ids = [int(x) for x in sys.argv[1:]]

for tid in talk_ids:
    print(f'\n=========== talk {tid} ===========')
    meta = cur.execute('SELECT * FROM talk_map WHERE talk_id=? LIMIT 1', (tid,)).fetchone()
    print('meta:', meta)
    rows = cur.execute('''
        SELECT ds.doc_order, e.hash, e.text_zh, s.speaker
        FROM dialogue_seq ds
        JOIN entries e ON e.hash = ds.hash
        LEFT JOIN dialogue_speaker s ON s.hash = ds.hash AND s.talk_id = ds.talk_id
        WHERE ds.talk_id = ?
        GROUP BY ds.hash
        ORDER BY ds.doc_order
    ''', (tid,)).fetchall()
    if not rows:
        # fallback via dialogue_speaker / dialogue_chapter
        rows = cur.execute('''
            SELECT dc.doc_order, e.hash, e.text_zh, s.speaker
            FROM dialogue_chapter dc
            JOIN entries e ON e.hash = dc.hash
            LEFT JOIN dialogue_speaker s ON s.hash = dc.hash AND s.talk_id = dc.talk_id
            WHERE dc.talk_id = ?
            ORDER BY dc.doc_order
        ''', (tid,)).fetchall()
    for order, h, text, spk in rows:
        t = (text or '').replace('\n', ' / ')
        print(f'[{order}] <{spk}> {t}')
    print(f'--- total {len(rows)} lines')
