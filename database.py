import sqlite3
import os
import json

# Use /data/ persistent disk on Render, fallback to local for development
_DATA_DIR = '/data' if os.path.isdir('/data') else '.'
DB_FILE = os.path.join(_DATA_DIR, 'database.sqlite')

def get_db_connection():
    conn = sqlite3.connect(DB_FILE, timeout=10)
    conn.row_factory = sqlite3.Row
    # Enforce WAL mode for better concurrency
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA synchronous=NORMAL')
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    
    # 1. Users Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            name TEXT NOT NULL,
            email TEXT,
            major TEXT,
            role TEXT NOT NULL DEFAULT 'student'
        )
    ''')
    
    # 2. Events Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            date TEXT,
            category TEXT,
            location TEXT,
            owner TEXT,
            description TEXT,
            registration_open INTEGER DEFAULT 0,
            max_participants INTEGER DEFAULT 0,
            score INTEGER DEFAULT 0,
            hidden INTEGER DEFAULT 0,
            created_at TEXT
        )
    ''')
    
    # 3. Participations Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS participations (
            id TEXT PRIMARY KEY,
            username TEXT NOT NULL,
            student_name TEXT,
            major TEXT,
            event_id TEXT,
            event_title TEXT,
            event_date TEXT,
            score INTEGER DEFAULT 0,
            timestamp TEXT,
            image_url TEXT,
            status TEXT DEFAULT 'pending',
            FOREIGN KEY(username) REFERENCES users(username),
            FOREIGN KEY(event_id) REFERENCES events(id)
        )
    ''')
    
    # 4. Registrations Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS registrations (
            id TEXT PRIMARY KEY,
            event_id TEXT NOT NULL,
            event_title TEXT,
            event_date TEXT,
            username TEXT NOT NULL,
            name TEXT,
            major TEXT,
            email TEXT,
            timestamp TEXT,
            status TEXT DEFAULT 'pending',
            FOREIGN KEY(event_id) REFERENCES events(id),
            FOREIGN KEY(username) REFERENCES users(username)
        )
    ''')

    # 5. Notifications Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            title TEXT NOT NULL,
            message TEXT,
            type TEXT DEFAULT 'info',
            is_read INTEGER DEFAULT 0,
            created_at TEXT,
            FOREIGN KEY(username) REFERENCES users(username)
        )
    ''')
    
    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    print("Database initialized successfully.")
