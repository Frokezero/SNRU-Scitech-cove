import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add import for database
if 'from database import get_db_connection' not in content:
    content = content.replace('import json', 'import json\nfrom database import get_db_connection')

# 2. Replace load_users and save_users
user_repl = '''def load_users():
    with data_lock:
        conn = get_db_connection()
        rows = conn.execute('SELECT * FROM users').fetchall()
        conn.close()
        return {r['username']: dict(r) for r in rows}

def save_users(users):
    with data_lock:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('BEGIN TRANSACTION')
        c.execute('DELETE FROM users')
        for username, data in users.items():
            c.execute(\'\'\'
                INSERT INTO users (username, password, name, email, major, role)
                VALUES (?, ?, ?, ?, ?, ?)
            \'\'\', (username, data.get('password',''), data.get('name',''), data.get('email',''), data.get('major',''), data.get('role','student')))
        conn.commit()
        conn.close()'''
content = re.sub(r'def load_users\(\):.*?def save_users\(users\):[^\n]*\n(?:    [^\n]*\n)*', user_repl + '\n\n', content, flags=re.DOTALL)

# 3. Replace load_events and save_events
event_repl = '''def load_events():
    with data_lock:
        conn = get_db_connection()
        rows = conn.execute('SELECT * FROM events').fetchall()
        conn.close()
        events = []
        for r in rows:
            d = dict(r)
            d['registration_open'] = bool(d['registration_open'])
            d['hidden'] = bool(d['hidden'])
            events.append(d)
        return events

def save_events(events):
    with data_lock:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('BEGIN TRANSACTION')
        c.execute('DELETE FROM events')
        for e in events:
            c.execute(\'\'\'
                INSERT INTO events (
                    id, title, date, category, location, owner, description,
                    registration_open, max_participants, score, hidden, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            \'\'\', (
                e.get('id', ''), e.get('title', ''), e.get('date', ''),
                e.get('category', ''), e.get('location', ''), e.get('owner', 'สโมสรนักศึกษา'),
                e.get('description', ''), 1 if e.get('registration_open') else 0,
                int(e.get('max_participants', 0) or 0), int(e.get('score', 0) or 0),
                1 if e.get('hidden') else 0, e.get('created_at', '')
            ))
        conn.commit()
        conn.close()'''
content = re.sub(r'def load_events\(\):.*?def save_events\(data\):[^\n]*\n(?:    [^\n]*\n)*', event_repl + '\n\n', content, flags=re.DOTALL)

# 4. Replace load_participations and save_participations
part_repl = '''def load_participations():
    with data_lock:
        conn = get_db_connection()
        rows = conn.execute('SELECT * FROM participations').fetchall()
        conn.close()
        return [dict(r) for r in rows]

def save_participations(data):
    with data_lock:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('BEGIN TRANSACTION')
        c.execute('DELETE FROM participations')
        for p in data:
            c.execute(\'\'\'
                INSERT INTO participations (
                    id, username, student_name, major, event_id, event_title,
                    event_date, score, timestamp, image_url, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            \'\'\', (
                p.get('id', ''), p.get('username', ''), p.get('student_name', ''),
                p.get('major', ''), p.get('event_id', ''), p.get('event_title', ''),
                p.get('event_date', ''), int(p.get('score', 0) or 0), p.get('timestamp', ''),
                p.get('image_url', ''), p.get('status', 'pending')
            ))
        conn.commit()
        conn.close()'''
content = re.sub(r'def load_participations\(\):.*?def save_participations\(data\):[^\n]*\n(?:    [^\n]*\n)*', part_repl + '\n\n', content, flags=re.DOTALL)

# 5. Replace load_registrations and save_registrations
reg_repl = '''def load_registrations():
    with data_lock:
        conn = get_db_connection()
        rows = conn.execute('SELECT * FROM registrations').fetchall()
        conn.close()
        return [dict(r) for r in rows]

def save_registrations(data):
    with data_lock:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('BEGIN TRANSACTION')
        c.execute('DELETE FROM registrations')
        for r in data:
            c.execute(\'\'\'
                INSERT INTO registrations (
                    id, event_id, event_title, event_date, username, name,
                    major, email, timestamp, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            \'\'\', (
                r.get('id', ''), r.get('event_id', ''), r.get('event_title', ''),
                r.get('event_date', ''), r.get('username', ''), r.get('name', ''),
                r.get('major', ''), r.get('email', ''), r.get('timestamp', ''),
                r.get('status', 'pending')
            ))
        conn.commit()
        conn.close()'''
content = re.sub(r'def load_registrations\(\):.*?def save_registrations\(data\):[^\n]*\n(?:    [^\n]*\n)*', reg_repl + '\n\n', content, flags=re.DOTALL)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("app.py has been refactored.")
