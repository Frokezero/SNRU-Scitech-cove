import sys
sys.path.insert(0, '.')
from database import get_db_connection
import json

conn = get_db_connection()
rows = conn.execute('''
    SELECT * FROM notifications 
    WHERE username = ? 
    ORDER BY created_at DESC 
    LIMIT 2
''', ('67102122111',)).fetchall()
conn.close()

result = [dict(r) for r in rows]
print(json.dumps(result, indent=2, ensure_ascii=False))
