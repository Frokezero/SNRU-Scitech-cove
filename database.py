import sqlite3
import os
import json

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database.sqlite')

def get_db_connection():
    conn = sqlite3.connect(DB_FILE, timeout=10)
    conn.row_factory = sqlite3.Row
    # Enforce foreign key constraints and WAL mode for integrity and concurrency
    conn.execute('PRAGMA foreign_keys = ON')
    try:
        conn.execute('PRAGMA journal_mode=WAL')
    except Exception:
        pass # Fallback to default journal mode if WAL is restricted on shared hosting
    conn.execute('PRAGMA synchronous=NORMAL')
    
    # Auto-register connection with Flask app context if available
    try:
        from flask import has_app_context, g
        if has_app_context():
            if not hasattr(g, '_db_connections'):
                g._db_connections = []
            g._db_connections.append(conn)
    except ImportError:
        pass
        
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
            role TEXT NOT NULL DEFAULT 'student',
            line_id TEXT
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
            status TEXT DEFAULT 'รอการดำเนินการ',
            created_at TEXT,
            registration_start TEXT,
            registration_end TEXT,
            latitude REAL DEFAULT 17.18994,
            longitude REAL DEFAULT 104.09153
        )
    ''')
    
    # Run migration in case tables were already created
    try:
        c.execute("ALTER TABLE users ADD COLUMN line_id TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("ALTER TABLE events ADD COLUMN registration_start TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("ALTER TABLE events ADD COLUMN registration_end TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("ALTER TABLE events ADD COLUMN latitude REAL DEFAULT 17.18994")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("ALTER TABLE events ADD COLUMN longitude REAL DEFAULT 104.09153")
    except sqlite3.OperationalError:
        pass
    
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

    # 5. Performance Indexes (Optimization)
    c.execute('CREATE INDEX IF NOT EXISTS idx_participations_username ON participations(username)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_participations_event_id ON participations(event_id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_registrations_username ON registrations(username)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_registrations_event_id ON registrations(event_id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_events_status ON events(status)')
    
    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    print("Database initialized successfully.")
