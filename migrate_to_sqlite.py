import os
import json
import sqlite3
from database import init_db, get_db_connection
from werkzeug.security import generate_password_hash

def migrate_users():
    conn = get_db_connection()
    c = conn.cursor()
    if not os.path.exists('users.json'):
        return
        
    with open('users.json', 'r', encoding='utf-8') as f:
        users = json.load(f)
        
    # Scan participations.json for missing users
    if os.path.exists('participations.json'):
        with open('participations.json', 'r', encoding='utf-8') as f:
            try:
                parts = json.load(f)
                for p in parts:
                    u = p.get('username')
                    if u and u not in users:
                        users[u] = {
                            "password": generate_password_hash('password'),
                            "name": p.get('student_name') or f"นักศึกษา {u}",
                            "major": p.get('major') or "คณะวิทยาศาสตร์และเทคโนโลยี",
                            "email": p.get('email') or f"{u}@snru.ac.th",
                            "role": "student"
                        }
            except Exception as e:
                print(f"Error scanning participations.json for users: {e}")

    # Scan registrations.json for missing users
    if os.path.exists('registrations.json'):
        with open('registrations.json', 'r', encoding='utf-8') as f:
            try:
                regs = json.load(f)
                for r in regs:
                    u = r.get('username')
                    if u and u not in users:
                        users[u] = {
                            "password": generate_password_hash('password'),
                            "name": r.get('name') or f"นักศึกษา {u}",
                            "major": r.get('major') or "คณะวิทยาศาสตร์และเทคโนโลยี",
                            "email": r.get('email') or f"{u}@snru.ac.th",
                            "role": "student"
                        }
            except Exception as e:
                print(f"Error scanning registrations.json for users: {e}")

    for username, data in users.items():
        c.execute('''
            INSERT OR REPLACE INTO users (username, password, name, email, major, role)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            username,
            data.get('password', ''),
            data.get('name', ''),
            data.get('email', ''),
            data.get('major', ''),
            data.get('role', 'student')
        ))
    conn.commit()
    conn.close()
    print(f"Migrated {len(users)} users.")

def migrate_events():
    conn = get_db_connection()
    c = conn.cursor()
    if not os.path.exists('events.json'):
        return
        
    with open('events.json', 'r', encoding='utf-8') as f:
        events = json.load(f)
        
    for e in events:
        c.execute('''
            INSERT OR REPLACE INTO events (
                id, title, date, category, location, owner, description,
                registration_open, max_participants, score, hidden, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            e.get('id', ''),
            e.get('title', ''),
            e.get('date', ''),
            e.get('category', ''),
            e.get('location', ''),
            e.get('owner', 'สโมสรนักศึกษา'),
            e.get('description', ''),
            1 if e.get('registration_open') else 0,
            int(e.get('max_participants', 0)),
            int(e.get('score', 0)),
            1 if e.get('hidden') else 0,
            e.get('created_at', '')
        ))
    conn.commit()
    conn.close()
    print(f"Migrated {len(events)} events.")

def migrate_participations():
    conn = get_db_connection()
    c = conn.cursor()
    if not os.path.exists('participations.json'):
        return
        
    with open('participations.json', 'r', encoding='utf-8') as f:
        parts = json.load(f)
        
    for p in parts:
        c.execute('''
            INSERT OR REPLACE INTO participations (
                id, username, student_name, major, event_id, event_title,
                event_date, score, timestamp, image_url, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            p.get('id', ''),
            p.get('username', ''),
            p.get('student_name', ''),
            p.get('major', ''),
            p.get('event_id', ''),
            p.get('event_title', ''),
            p.get('event_date', ''),
            int(p.get('score', 0)),
            p.get('timestamp', ''),
            p.get('image_url', ''),
            p.get('status', 'pending')
        ))
    conn.commit()
    conn.close()
    print(f"Migrated {len(parts)} participations.")

def migrate_registrations():
    conn = get_db_connection()
    c = conn.cursor()
    if not os.path.exists('registrations.json'):
        return
        
    with open('registrations.json', 'r', encoding='utf-8') as f:
        regs = json.load(f)
        
    for r in regs:
        c.execute('''
            INSERT OR REPLACE INTO registrations (
                id, event_id, event_title, event_date, username, name,
                major, email, timestamp, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            r.get('id', ''),
            r.get('event_id', ''),
            r.get('event_title', ''),
            r.get('event_date', ''),
            r.get('username', ''),
            r.get('name', ''),
            r.get('major', ''),
            r.get('email', ''),
            r.get('timestamp', ''),
            r.get('status', 'pending')
        ))
    conn.commit()
    conn.close()
    print(f"Migrated {len(regs)} registrations.")

if __name__ == '__main__':
    print("Starting migration to SQLite...")
    init_db()
    migrate_users()
    migrate_events()
    migrate_participations()
    migrate_registrations()
    print("Migration complete!")
