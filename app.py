from flask import Flask, jsonify, request, send_from_directory, session, redirect
from werkzeug.security import generate_password_hash, check_password_hash
import json
from database import get_db_connection
import os
import uuid
import re
import smtplib
import threading
import time
import shutil
from datetime import datetime, timedelta
from functools import wraps
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formatdate, make_msgid
from werkzeug.utils import secure_filename

# Simple Cache for Performance
_cache = {
    "users": {"data": None, "time": 0},
    "events": {"data": None, "time": 0},
    "participations": {"data": None, "time": 0},
    "registrations": {"data": None, "time": 0}
}
CACHE_TTL = 2 # 2 seconds cache to reduce Disk I/O under high load

def require_role(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            username = session.get('username')
            if not username:
                return jsonify({"success": False, "message": "กรุณาเข้าสู่ระบบ"}), 401
            users = load_users()
            user = users.get(username)
            if not user:
                return jsonify({"success": False, "message": "ไม่พบผู้ใช้งาน"}), 401
            if user.get('role') not in roles:
                return jsonify({"success": False, "message": "คุณไม่มีสิทธิ์เข้าถึงส่วนนี้"}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def send_email_async(to_email, subject, body):
    def send_email_task():
        if not os.path.exists('email_config.json'):
            return
        try:
            with open('email_config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            sender_email = config.get("sender_email")
            sender_password = config.get("sender_password")
            smtp_server = config.get("smtp_server", "smtp.gmail.com")
            smtp_port = config.get("smtp_port", 587)
            
            if not sender_email or not sender_password or sender_email == "your-email@gmail.com":
                return # Not configured
                
            # Use 'alternative' so we can attach both plain text and HTML
            msg = MIMEMultipart('alternative')
            msg['From'] = f"University Activity Calendar <{sender_email}>"
            msg['To'] = to_email
            msg['Subject'] = subject
            msg['Date'] = formatdate(localtime=True)
            msg['Message-ID'] = make_msgid()
            
            # Create a more readable plain text version
            # Replace common block tags with newlines
            text = re.sub(r'<(p|br|li|div|h[1-6])[^>]*>', '\n', body)
            # Remove all other tags
            text = re.sub(r'<[^>]+>', '', text)
            # Clean up whitespace
            plain_text = text.replace('&nbsp;', ' ').replace('\n\n\n', '\n\n').strip()
            
            # Attach plain text first, then HTML (standard practice)
            msg.attach(MIMEText(plain_text, 'plain', 'utf-8'))
            msg.attach(MIMEText(body, 'html', 'utf-8'))
            
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
            server.quit()
        except Exception as e:
            print(f"Failed to send email to {to_email}: {e}")
            
    thread = threading.Thread(target=send_email_task)
    thread.start()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'super-secret-sakon-nakhon-key')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB upload limit

DATA_FILE = 'events.json'

USER_FILE = 'users.json'

data_lock = threading.RLock()

def load_users():
    with data_lock:
        conn = get_db_connection()
        rows = conn.execute('SELECT * FROM users').fetchall()
        conn.close()
        return {r['username']: dict(r) for r in rows}

def db_save_user(username, data):
    with data_lock:
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO users (username, password, name, email, major, role)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(username) DO UPDATE SET
                password=excluded.password,
                name=excluded.name,
                email=excluded.email,
                major=excluded.major,
                role=excluded.role
        ''', (username, data.get('password',''), data.get('name',''), data.get('email',''), data.get('major',''), data.get('role','student')))
        conn.commit()
        conn.close()

def db_delete_user(username):
    with data_lock:
        conn = get_db_connection()
        conn.execute('DELETE FROM users WHERE username=?', (username,))
        conn.commit()
        conn.close()


def get_student_year(username):
    """Calculates student year based on ID prefix (e.g., 69 = Year 1 in 2569)"""
    if not username: return None
    try:
        # Student ID usually starts with the year prefix, e.g., 6911020641...
        prefix = str(username)[:2]
        if prefix.isdigit():
            start_year = int(prefix) + 2500
            # Dynamic calculation based on current Buddhist year
            current_year = datetime.now().year + 543
            year = current_year - start_year + 1
            if 1 <= year <= 8:
                return year
    except:
        pass
    return None

UPLOAD_FOLDER = 'uploads'
# Global Session Tracking (for activity timeout only, not concurrency restriction)
session_lock = threading.RLock()
ACTIVE_SESSIONS = {} # {username: last_activity_timestamp}
SESSION_TIMEOUT = 3600 # 1 hour idle timeout

def cleanup_sessions():
    now = time.time()
    with session_lock:
        expired = [u for u, t in ACTIVE_SESSIONS.items() if now - t > SESSION_TIMEOUT]
        for u in expired:
            ACTIVE_SESSIONS.pop(u, None)

ACTIVITIES_UPLOAD_FOLDER = os.path.join(UPLOAD_FOLDER, 'activities')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
if not os.path.exists(ACTIVITIES_UPLOAD_FOLDER):
    os.makedirs(ACTIVITIES_UPLOAD_FOLDER)

PARTICIPATIONS_FILE = 'participations.json'

def load_participations():
    with data_lock:
        conn = get_db_connection()
        rows = conn.execute('SELECT * FROM participations').fetchall()
        conn.close()
        return [dict(r) for r in rows]

def db_save_participation(p):
    with data_lock:
        conn = get_db_connection()
        conn.execute('''
            INSERT OR REPLACE INTO participations (
                id, username, student_name, major, event_id, event_title,
                event_date, score, timestamp, image_url, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            p.get('id', ''), p.get('username', ''), p.get('student_name', ''),
            p.get('major', ''), p.get('event_id', ''), p.get('event_title', ''),
            p.get('event_date', ''), int(p.get('score', 0) or 0), p.get('timestamp', ''),
            p.get('image_url', ''), p.get('status', 'pending')
        ))
        conn.commit()
        conn.close()
        _cache["participations"]["data"] = None # Invalidate cache

def db_delete_participation(part_id):
    with data_lock:
        conn = get_db_connection()
        conn.execute('DELETE FROM participations WHERE id=?', (part_id,))
        conn.commit()
        conn.close()
        _cache["participations"]["data"] = None # Invalidate cache

def db_delete_user_participations(username):
    with data_lock:
        conn = get_db_connection()
        conn.execute('DELETE FROM participations WHERE username=?', (username,))
        conn.commit()
        conn.close()
        _cache["participations"]["data"] = None # Invalidate cache

def db_update_participation_status(part_id, status, score=None):
    with data_lock:
        conn = get_db_connection()
        if score is not None:
            conn.execute('UPDATE participations SET status=?, score=? WHERE id=?', (status, score, part_id))
        else:
            conn.execute('UPDATE participations SET status=? WHERE id=?', (status, part_id))
        conn.commit()
        conn.close()
        _cache["participations"]["data"] = None # Invalidate cache


ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

REGISTRATIONS_FILE = 'registrations.json'

def load_registrations():
    with data_lock:
        conn = get_db_connection()
        rows = conn.execute('SELECT * FROM registrations').fetchall()
        conn.close()
        return [dict(r) for r in rows]

def db_add_registration(r):
    with data_lock:
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO registrations (
                id, event_id, event_title, event_date, username, name,
                major, email, timestamp, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            r.get('id', ''), r.get('event_id', ''), r.get('event_title', ''),
            r.get('event_date', ''), r.get('username', ''), r.get('name', ''),
            r.get('major', ''), r.get('email', ''), r.get('timestamp', ''),
            r.get('status', 'pending')
        ))
        conn.commit()
        conn.close()
        _cache["registrations"]["data"] = None # Invalidate cache

def db_update_registration_status(reg_id, status):
    with data_lock:
        conn = get_db_connection()
        conn.execute('UPDATE registrations SET status=? WHERE id=?', (status, reg_id))
        conn.commit()
        conn.close()
        _cache["registrations"]["data"] = None # Invalidate cache


def load_carousel():
    with data_lock:
        if not os.path.exists('carousel.json'):
            return []
        with open('carousel.json', 'r', encoding='utf-8') as f:
            return json.load(f)

def save_carousel(images):
    with data_lock:
        with open('carousel.json', 'w', encoding='utf-8') as f:
            json.dump(images, f, ensure_ascii=False, indent=4)

def save_json(filepath, data):
    with data_lock:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

# Helper to parse Thai date string for comparison
def parse_thai_date_to_comparable(date_str):
    if not date_str or not isinstance(date_str, str):
        return None
    
    # Standardize Thai month abbreviations
    months_map = {
        'ม.ค': 1, 'ก.พ': 2, 'มี.ค': 3, 'เม.ย': 4, 'พ.ค': 5, 'มิ.ย': 6,
        'ก.ค': 7, 'ส.ค': 8, 'ก.ย': 9, 'ต.ค': 10, 'พ.ย': 11, 'ธ.ค': 12,
        'มกราคม': 1, 'กุมภาพันธ์': 2, 'มีนาคม': 3, 'เมษายน': 4, 'พฤษภาคม': 5, 'มิถุนายน': 6,
        'กรกฎาคม': 7, 'สิงหาคม': 8, 'กันยายน': 9, 'ตุลาคม': 10, 'พฤศจิกายน': 11, 'ธันวาคม': 12
    }
    
    try:
        clean_date = date_str.strip()
        
        # Extract Day (first number)
        day_match = re.search(r'^\d+', clean_date)
        if not day_match:
            day_match = re.search(r'\d+', clean_date)
        day = int(day_match.group()) if day_match else 1
        
        # Find Month (flexible matching)
        month = 1
        for m_name, m_idx in months_map.items():
            # Match month with or without trailing dot
            if m_name in clean_date or m_name.replace('.', '') in clean_date:
                month = m_idx
                break
        
        # Extract Year (looking for 2 or 4 digits)
        # Better regex for year: 25xx or 20xx or 6x
        year_match = re.search(r'(25\d{2}|20\d{2}|[5-7]\d)', clean_date)
        year = int(year_match.group()) if year_match else 2569
        
        if year < 100: 
            year += 2500
        elif year < 2100: # AD year
            year += 543
            
        # Return as standard Date comparison
        return datetime(year - 543, month, day).date()
    except Exception as e:
        with open('auto_open.log', 'a', encoding='utf-8') as f:
            f.write(f"[{datetime.now().isoformat()}] ERROR parsing date '{date_str}': {str(e)}\n")
        return None

def process_auto_open(events):
    today = datetime.now().date()
    modified = False
    log_entries = []
    
    for e in events:
        if not e.get('registration_open', False):
            event_date = parse_thai_date_to_comparable(e.get('date'))
            if event_date:
                if event_date <= today:
                    e['registration_open'] = True
                    modified = True
                    log_entries.append(f"SUCCESS: Opened '{e.get('title')}' (Event Date: {event_date}, Today: {today})")
            else:
                # Log only if date is not empty
                if e.get('date'):
                    log_entries.append(f"SKIP: Could not parse date for '{e.get('title')}' - Value: '{e.get('date')}'")
    
    if log_entries:
        try:
            with open('auto_open.log', 'a', encoding='utf-8') as f:
                for entry in log_entries:
                    f.write(f"[{datetime.now().isoformat()}] {entry}\n")
        except: pass
        
    return modified

def add_notification(username, title, message, type='info'):
    try:
        with data_lock:
            conn = get_db_connection()
            conn.execute('''
                INSERT INTO notifications (username, title, message, type, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (username, title, message, type, datetime.now().isoformat()))
            conn.commit()
            conn.close()
        return True
    except Exception as e:
        print(f"Error adding notification: {e}")
        return False

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/certificate')
def view_certificate():
    return send_from_directory('.', 'certificate.html')

@app.route('/api/certificate/<participation_id>')
def get_certificate_data(participation_id):
    username = session.get('username')
    if not username:
        return jsonify({"success": False, "message": "กรุณาเข้าสู่ระบบ"}), 401
    
    conn = get_db_connection()
    # Check if this participation belongs to the user and is approved
    part = conn.execute('''
        SELECT p.*, e.location as event_location 
        FROM participations p
        JOIN events e ON p.event_id = e.id
        WHERE p.id = ? AND p.username = ? AND p.status = 'approved'
    ''', (participation_id, username)).fetchone()
    conn.close()
    
    if not part:
        # Also check if user is admin (admin can see all certs)
        conn = get_db_connection()
        user_row = conn.execute('SELECT role FROM users WHERE username = ?', (username,)).fetchone()
        if user_row and user_row['role'] == 'admin':
            part = conn.execute('''
                SELECT p.*, e.location as event_location 
                FROM participations p
                JOIN events e ON p.event_id = e.id
                WHERE p.id = ? AND p.status = 'approved'
            ''', (participation_id,)).fetchone()
        conn.close()
        
    if not part:
        return jsonify({"success": False, "message": "ไม่พบข้อมูลเกียรติบัตรหรือยังไม่ได้รับการอนุมัติ"}), 404
        
    return jsonify({
        "id": part['id'],
        "student_name": part['student_name'],
        "event_title": part['event_title'],
        "event_date": part['event_date'],
        "event_location": part['event_location']
    })

def load_events():
    with data_lock:
        now = time.time()
        if _cache["events"]["data"] is not None and (now - _cache["events"]["time"] < CACHE_TTL):
            return _cache["events"]["data"]
            
        conn = get_db_connection()
        rows = conn.execute('SELECT * FROM events').fetchall()
        conn.close()
        data = [dict(r) for r in rows]
        
        # Ensure correct boolean types and defaults
        for e in data:
            e['hidden'] = bool(e.get('hidden'))
            e['registration_open'] = bool(e.get('registration_open'))
            if 'owner' not in e: e['owner'] = "สโมสรนักศึกษา"
            
        _cache["events"] = {"data": data, "time": now}
        return data

def db_add_event(e):
    with data_lock:
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO events (
                id, title, date, category, location, owner, description,
                registration_open, max_participants, score, hidden, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            e.get('id'), e.get('title', ''), e.get('date', ''),
            e.get('category', ''), e.get('location', ''), e.get('owner', ''),
            e.get('description', ''), 1 if e.get('registration_open') else 0,
            int(e.get('max_participants', 0)), int(e.get('score', 0)),
            1 if e.get('hidden') else 0, e.get('created_at', '')
        ))
        conn.commit()
        conn.close()
        _cache["events"]["data"] = None # Invalidate cache

def db_update_event(e):
    with data_lock:
        conn = get_db_connection()
        conn.execute('''
            UPDATE events SET
                title=?, date=?, category=?, location=?, owner=?, description=?,
                registration_open=?, max_participants=?, score=?, hidden=?
            WHERE id=?
        ''', (
            e.get('title', ''), e.get('date', ''), e.get('category', ''),
            e.get('location', ''), e.get('owner', ''), e.get('description', ''),
            1 if e.get('registration_open') else 0, int(e.get('max_participants', 0)),
            int(e.get('score', 0)), 1 if e.get('hidden') else 0, e.get('id')
        ))
        conn.commit()
        conn.close()
        _cache["events"]["data"] = None # Invalidate cache

def db_delete_event(event_id):
    with data_lock:
        conn = get_db_connection()
        conn.execute('DELETE FROM events WHERE id=?', (event_id,))
        conn.commit()
        conn.close()
        _cache["events"]["data"] = None # Invalidate cache

# =============================================================
# BACKUP SYSTEM
# =============================================================
BACKUP_FOLDER = 'backups'
MAX_BACKUP_DAYS = 7

def perform_system_backup():
    try:
        if not os.path.exists(BACKUP_FOLDER):
            os.makedirs(BACKUP_FOLDER)
            
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        current_backup_path = os.path.join(BACKUP_FOLDER, f"backup_{timestamp}")
        os.makedirs(current_backup_path)
        
        files_to_backup = [
            USER_FILE, DATA_FILE, PARTICIPATIONS_FILE, 
            REGISTRATIONS_FILE, 'carousel.json', 'email_config.json',
            'database.sqlite'
        ]
        
        for file_name in files_to_backup:
            if os.path.exists(file_name):
                shutil.copy2(file_name, os.path.join(current_backup_path, file_name))
        
        print(f"   [BACKUP] System backup completed: {timestamp}")
        cleanup_old_backups()
    except Exception as e:
        print(f"   [BACKUP] Error during backup: {e}")

def cleanup_old_backups():
    try:
        now = time.time()
        for folder in os.listdir(BACKUP_FOLDER):
            folder_path = os.path.join(BACKUP_FOLDER, folder)
            if os.path.isdir(folder_path):
                # Check creation time
                if os.path.getctime(folder_path) < now - (MAX_BACKUP_DAYS * 86400):
                    shutil.rmtree(folder_path)
                    print(f"   [BACKUP] Removed old backup: {folder}")
    except Exception as e:
        print(f"   [BACKUP] Error during cleanup: {e}")

def run_backup_scheduler():
    # Initial backup on startup
    perform_system_backup()
    while True:
        # Wait for 24 hours (86400 seconds)
        time.sleep(86400)
        perform_system_backup()

# Start scheduler thread
backup_thread = threading.Thread(target=run_backup_scheduler, daemon=True)
backup_thread.start()

# =============================================================

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/login')
def login_page():
    if 'username' in session:
        users = load_users()
        if session['username'] in users:
            role = users[session['username']]['role']
            if role in ['admin', 'major']:
                return redirect('/admin')
            else:
                return redirect('/')
    return send_from_directory('.', 'login.html')

@app.route('/admin')
def admin():
    if 'username' not in session:
        return redirect('/login')
    users = load_users()
    if session['username'] not in users or users[session['username']]['role'] not in ['admin', 'major']:
        return redirect('/')
    return send_from_directory('.', 'admin.html')

@app.route('/profile')
def profile():
    if 'username' not in session:
        return redirect('/login')
    users = load_users()
    if session['username'] not in users or users[session['username']]['role'] != 'student':
        return redirect('/')
    return send_from_directory('.', 'profile.html')


# Routes will follow...

# Auth API
@app.before_request
def update_activity():
    # 1. Public Routes: Fully accessible without session
    public_paths = [
        '/', '/login', '/api/login', '/api/register', '/register', 
        '/api/carousel', '/api/events', '/api/leaderboard', '/theme-loader.js',
        '/style.css', '/script.js', '/favicon.ico'
    ]
    
    if request.path in public_paths or request.path.startswith('/static') or request.path.startswith('/uploads'):
        return

    # 2. Session Update: If logged in, update last activity
    username = session.get('username')
    if username:
        with session_lock:
            ACTIVE_SESSIONS[username] = time.time()
        return
    
    # 3. Secure Routes: If not logged in and not public, block access
    if request.path.startswith('/api/'):
        return jsonify({"success": False, "message": "Session expired"}), 401
    return redirect('/login')

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    users = load_users()
    if username in users and check_password_hash(users[username]['password'], password):
        user_role = users[username].get('role')
        
        session['username'] = username
        with session_lock:
            ACTIVE_SESSIONS[username] = time.time()
        return jsonify({"success": True, "user": {"name": users[username]['name'], "role": user_role}})
    
    return jsonify({"success": False, "message": "Username หรือ Password ไม่ถูกต้อง"}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    username = session.get('username')
    if username:
        with session_lock:
            ACTIVE_SESSIONS.pop(username, None)
    session.pop('username', None)
    return jsonify({"success": True})

@app.route('/api/me', methods=['GET'])
def me():
    username = session.get('username')
    if username:
        users = load_users()
        if username in users:
            u = users[username]
            return jsonify({
                "success": True, 
                "user": {
                    "username": username,
                    "name": u['name'], 
                    "role": u['role'],
                    "major": u.get('major', u.get('name')),
                    "year": get_student_year(username) if u.get('role') == 'student' else None
                }
            })
    return jsonify({"success": False}), 401

# Password Management API
TOKENS_FILE = 'reset_tokens.json'

def load_tokens():
    with data_lock:
        if not os.path.exists(TOKENS_FILE):
            return {}
        with open(TOKENS_FILE, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except:
                return {}

def save_tokens(tokens):
    save_json(TOKENS_FILE, tokens)

@app.route('/reset-password')
def reset_password_page():
    return send_from_directory('.', 'reset_password.html')

@app.route('/api/user/change-password', methods=['POST'])
def change_password():
    username = session.get('username')
    if not username:
        return jsonify({"success": False, "message": "กรุณาเข้าสู่ระบบ"}), 401
    
    data = request.json
    current_pw = data.get('currentPassword')
    new_pw = data.get('newPassword')
    
    if not current_pw or not new_pw:
        return jsonify({"success": False, "message": "ข้อมูลไม่ครบถ้วน"}), 400
        
    with data_lock:
        users = load_users()
        # Check if existing password matches (handling hashed vs plain if necessary)
        # The current login uses check_password_hash, but let's see how register saves it.
        if not check_password_hash(users[username]['password'], current_pw):
            return jsonify({"success": False, "message": "รหัสผ่านเดิมไม่ถูกต้อง"}), 400
            
        users[username]['password'] = generate_password_hash(new_pw)
        db_save_user(username, users[username])
    return jsonify({"success": True, "message": "เปลี่ยนรหัสผ่านสำเร็จ"})

@app.route('/api/auth/forgot-password', methods=['POST'])
def forgot_password():
    email = request.json.get('email')
    if not email:
        return jsonify({"success": False, "message": "กรุณาระบุอีเมล"}), 400
        
    with data_lock:
        users = load_users()
        user_target = None
        username_target = None
        for uname, udata in users.items():
            if udata.get('email') == email:
                user_target = udata
                username_target = uname
                break
                
        if not user_target:
            return jsonify({"success": False, "message": "ไม่พบอีเมลนี้ในระบบ"}), 404
            
        # Generate Token
        token = uuid.uuid4().hex
        tokens = load_tokens()
        tokens[token] = {
            "username": username_target,
            "expiry": time.time() + (15 * 60) # 15 mins
        }
        save_tokens(tokens)
    
    # Send Email
    subject = "แจ้งเปลี่ยนรหัสผ่านใหม่ (Reset Password)"
    reset_link = f"{request.host_url}reset-password?token={token}"
    body = f"""
    <div style="font-family:Kanit,sans-serif;max-width:500px;margin:auto;padding:24px;background:#f8fafc;border-radius:12px;">
        <h2 style="color:#0284c7;">🔒 คำขอเปลี่ยนรหัสผ่าน</h2>
        <p>สวัสดีคุณ <strong>{user_target.get('name', username_target)}</strong></p>
        <p>เราได้รับคำขอเปลี่ยนรหัสผ่านสำหรับบัญชีของคุณ กรุณาคลิกปุ่มด้านล่างเพื่อดำเนินการต่อ:</p>
        <div style="text-align:center;margin:32px 0;">
            <a href="{reset_link}" style="background:#0284c7;color:white;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:bold;">เปลี่ยนรหัสผ่านใหม่</a>
        </div>
        <p style="color:#64748b;font-size:12px;">* ลิงก์นี้จะหมดอายุภายใน 15 นาที</p>
        <p style="color:#64748b;font-size:12px;">หากคุณไม่ได้เป็นผู้ทำรายการ กรุณาละเว้นอีเมลฉบับนี้</p>
    </div>
    """
    send_email_async(email, subject, body)
    return jsonify({"success": True, "message": "ส่งลิงก์เปลี่ยนรหัสผ่านไปทางอีเมลแล้ว"})

@app.route('/api/auth/reset-password', methods=['POST'])
def reset_password():
    data = request.json
    token = data.get('token')
    new_pw = data.get('newPassword')
    
    if not token or not new_pw:
        return jsonify({"success": False, "message": "ข้อมูลไม่ครบถ้วน"}), 400
        
    with data_lock:
        tokens = load_tokens()
        if token not in tokens:
            return jsonify({"success": False, "message": "Token ไม่ถูกต้องหรือหมดอายุ"}), 400
            
        token_data = tokens[token]
        if time.time() > token_data['expiry']:
            del tokens[token]
            save_tokens(tokens)
            return jsonify({"success": False, "message": "Token หมดอายุแล้ว"}), 400
            
        username = token_data['username']
        users = load_users()
        if username in users:
            users[username]['password'] = generate_password_hash(new_pw)
            db_save_user(username, users[username])
            
        # Clean up token
        del tokens[token]
        save_tokens(tokens)
    
    return jsonify({"success": True, "message": "เปลี่ยนรหัสผ่านใหม่สำเร็จแล้ว"})

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    name = data.get('name')
    major = data.get('major')
    email = data.get('email')
    
    if not username or not password or not name or not email or not major:
        return jsonify({"success": False, "message": "กรุณากรอกข้อมูลให้ครบถ้วน"}), 400

    # Strict Validation
    if not re.match(r'^\d+$', username):
        return jsonify({"success": False, "message": "รหัสนักศึกษาต้องเป็นตัวเลขเท่านั้น"}), 400
    
    if not re.match(r'^[ก-๙\s]+$', name):
        return jsonify({"success": False, "message": "ชื่อ-นามสกุล ต้องเป็นภาษาไทยเท่านั้นและห้ามมีอักขระพิเศษ"}), 400
        
    if '@' not in email:
        return jsonify({"success": False, "message": "กรุณาระบุอีเมลที่ถูกต้อง"}), 400

    with data_lock:
        users = load_users()
        if username in users:
            return jsonify({"success": False, "message": "รหัสนักศึกษานี้ถูกลงทะเบียนแล้ว"}), 400
        
        users[username] = {
            "password": generate_password_hash(password),
            "name": name,
            "email": email,
            "major": major,
            "role": "student"
        }
        db_save_user(username, users[username])
    
    # Send welcome email
    subject = "ยินดีต้อนรับเข้าสู่ระบบ University Activity Calendar"
    body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #333;">
        <h2>ยินดีต้อนรับคุณ {name}</h2>
        <p>คุณได้ทำการสมัครสมาชิกในระบบ <strong>University Activity Calendar</strong> เรียบร้อยแล้ว</p>
        <p><strong>ข้อมูลของคุณ:</strong></p>
        <ul>
            <li>รหัสนักศึกษา (Username): {username}</li>
            <li>สาขาวิชา: {major}</li>
        </ul>
        <p>คุณสามารถเข้าสู่ระบบเพื่อติดตามและส่งผลงานการเข้าร่วมกิจกรรมได้ทันที</p>
        <hr>
        <p style="font-size: 12px; color: #888;">อีเมลฉบับนี้ส่งจากระบบอัตโนมัติ กรุณาอย่าตอบกลับ</p>
    </body>
    </html>
    """
    send_email_async(email, subject, body)
    db_save_user(username, users[username])
    
    # Auto login
    session['username'] = username
    return jsonify({"success": True, "message": "สมัครสมาชิกสำเร็จ", "user": {"name": name, "role": "student"}})

@app.route('/api/admin/users', methods=['GET'])
def get_users():
    username = session.get('username')
    users = load_users()
    if not username or username not in users:
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    current_user = users[username]
    role = current_user.get('role')
    
    if role not in ['admin', 'major']:
        return jsonify({"success": False, "message": "Unauthorized"}), 403
        
    filtered_users = {}
    if role == 'admin':
        filtered_users = users
    elif role == 'major':
        my_major_name = current_user.get('name')
        for u_id, u_data in users.items():
            if u_data.get('role') == 'student' and u_data.get('major') == my_major_name:
                filtered_users[u_id] = u_data
            elif u_id == username:
                filtered_users[u_id] = u_data
                
    return jsonify(filtered_users)

@app.route('/api/admin/update-user', methods=['POST'])
@require_role('admin', 'major')
def update_user():
    username = session.get('username')
    data = request.json
    target_user = data.get('username')
    new_name = data.get('name')
    new_password = data.get('password')

    with data_lock:
        users = load_users()
        current_user = users[username]
        role = current_user.get('role')
            
        if target_user not in users:
            return jsonify({"success": False, "message": "ไม่พบผู้ใช้งาน"}), 404
            
        target_data = users[target_user]
        
        if role == 'major':
            my_major_name = current_user.get('name')
            if target_user != username and (target_data.get('role') != 'student' or target_data.get('major') != my_major_name):
                return jsonify({"success": False, "message": "คุณไม่มีสิทธิ์แก้ไขผู้ใช้งานนี้"}), 403
                
        if new_name:
            users[target_user]['name'] = new_name
        if new_password:
            users[target_user]['password'] = generate_password_hash(new_password)
            
        db_save_user(target_username, users[target_username])
    return jsonify({"success": True, "message": f"อัปเดตข้อมูลของ {target_user} เรียบร้อยแล้ว"})




@app.route('/api/carousel', methods=['GET'])
def get_carousel():
    return jsonify(load_carousel())

@app.route('/api/carousel/upload', methods=['POST'])
@require_role('admin')
def upload_carousel():
    
    if 'image' not in request.files:
        return jsonify({"success": False, "message": "No image part"}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({"success": False, "message": "No selected file"}), 400
        
    if not allowed_file(file.filename):
        return jsonify({"success": False, "message": "File type not allowed"}), 400
    
    if file:
        original_ext = os.path.splitext(file.filename)[1]
        # Use UUID but still secure the base to be safe
        filename = secure_filename(f"{uuid.uuid4()}{original_ext}")
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        
        # Add to carousel.json
        images = load_carousel()
        images.append(f"/uploads/{filename}")
        save_carousel(images)
        
        return jsonify({"success": True, "url": f"/uploads/{filename}"})
    return jsonify({"success": False})

@app.route('/api/carousel/delete/<int:index>', methods=['POST'])
def delete_carousel(index):
    username = session.get('username')
    users = load_users()
    if not username or users.get(username, {}).get('role') != 'admin':
        return jsonify({"success": False, "message": "Unauthorized"}), 403
        
    images = load_carousel()
    if 0 <= index < len(images):
        images.pop(index)
        save_carousel(images)
        return jsonify({"success": True})
    return jsonify({"success": False, "message": "Index out of range"}), 400

@app.route('/api/admin/carousel', methods=['POST'])
def update_carousel_list():
    username = session.get('username')
    users = load_users()
    if not username or users.get(username, {}).get('role') != 'admin':
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    images = request.json.get('images', [])
    save_carousel(images)
    return jsonify({"success": True, "message": "อัปเดตรูปภาพเรียบร้อยแล้ว"})

# Events API
@app.route('/api/events', methods=['GET'])
def get_events():
    events = load_events()
    regs = load_registrations()
    
    # Auto-open registration logic
    if process_auto_open(events):
        for e in events:
            db_update_event(e)

    # Calculate registered count for each event
    reg_counts = {}
    for r in regs:
        if r.get('status') != 'cancelled':
            eid = r.get('event_id')
            reg_counts[eid] = reg_counts.get(eid, 0) + 1

    for e in events:
        if 'owner' not in e:
            e['owner'] = "สโมสรนักศึกษา" # Default owner for old events
        e['registered_count'] = reg_counts.get(e['id'], 0)
    
    # Sort events by date (newest first) or by created_at
    events.sort(key=lambda x: x.get('date', ''), reverse=True)

    page = request.args.get('page', type=int)
    limit = request.args.get('limit', type=int)
    
    if page and limit:
        start = (page - 1) * limit
        end = start + limit
        return jsonify({
            "events": events[start:end],
            "total": len(events),
            "pages": (len(events) + limit - 1) // limit,
            "current_page": page
        })
        
    return jsonify(events)

@app.route('/api/events', methods=['POST'])
def add_event():
    username = session.get('username')
    if not username:
        return jsonify({"success": False, "message": "กรุณาเข้าสู่ระบบ"}), 401
    
    with data_lock:
        events = load_events()
        new_event = request.json
        
        # Security Validation
        title = new_event.get('title', '')
        if not title:
            return jsonify({"success": False, "message": "กรุณาระบุชื่อกิจกรรม"}), 400
        
        # Block script tags and obvious injection
        if '<script' in title.lower() or 'javascript:' in title.lower() or '<iframe' in title.lower():
            return jsonify({"success": False, "message": "ชื่อกิจกรรมมีอักขระที่ไม่ได้รับอนุญาต"}), 400
            
        desc = new_event.get('description', '')
        if '<script' in desc.lower() or 'javascript:' in desc.lower():
            return jsonify({"success": False, "message": "คำอธิบายมีอักขระที่ไม่ได้รับอนุญาต"}), 400

        new_event['id'] = str(uuid.uuid4())
        
        # Set Defaults
        if 'registration_open' not in new_event:
            new_event['registration_open'] = True
        
        try:
            new_event['max_participants'] = int(new_event.get('max_participants', 200))
        except:
            new_event['max_participants'] = 200
            
        users = load_users()
        
        # Permission Check for University Category
        if new_event.get('category') == 'กิจกรรมมหาวิทยาลัย' and users[username]['role'] != 'admin':
            return jsonify({"success": False, "message": "เฉพาะแอดมินส่วนกลางเท่านั้นที่สามารถเพิ่มกิจกรรมมหาวิทยาลัยได้"}), 403

        # Assign owner based on role
        if users[username]['role'] == 'admin' and new_event.get('owner'):
            pass # Admin can assign any owner
        else:
            new_event['owner'] = users[username]['name'] # Majors can only create for themselves
            
        new_event['created_at'] = datetime.now().isoformat()
        events.append(new_event)
        db_add_event(new_event)
    return jsonify({'success': True, 'event': new_event})

@app.route('/api/events/<event_id>', methods=['PUT'])
def update_event(event_id):
    username = session.get('username')
    if not username:
        return jsonify({"success": False, "message": "กรุณาเข้าสู่ระบบ"}), 401

    with data_lock:
        events = load_events()
        updated_event = request.json
        
        users = load_users()
        for i, event in enumerate(events):
            if event['id'] == event_id:
                event_owner = event.get('owner', 'สโมสรนักศึกษา')
                # Check permissions
                if users[username]['role'] != 'admin' and users[username]['name'] != event_owner:
                    return jsonify({"success": False, "message": "คุณไม่มีสิทธิ์แก้ไขกิจกรรมของสาขาอื่น"}), 403
                
                updated_event['id'] = event_id
                
                # Security Validation
                title = updated_event.get('title', '')
                if '<script' in title.lower() or 'javascript:' in title.lower():
                    return jsonify({"success": False, "message": "ชื่อกิจกรรมมีอักขระที่ไม่ได้รับอนุญาต"}), 400
                
                # Permission Check for University Category
                if updated_event.get('category') == 'กิจกรรมมหาวิทยาลัย' and users[username]['role'] != 'admin':
                    return jsonify({"success": False, "message": "เฉพาะแอดมินส่วนกลางเท่านั้นที่สามารถจัดการกิจกรรมมหาวิทยาลัยได้"}), 403

                # If admin, they might have changed the owner. If major, keep original owner.
                if users[username]['role'] != 'admin':
                    updated_event['owner'] = event_owner
                
                try:
                    updated_event['max_participants'] = int(updated_event.get('max_participants', 200))
                except:
                    pass
                
                # Preserve essential backend-managed fields
                updated_event['created_at'] = event.get('created_at')
                updated_event['registered_count'] = event.get('registered_count', 0)
                if 'hidden' in event:
                    updated_event['hidden'] = event['hidden']
                    
                events[i] = updated_event
                db_update_event(event)
                return jsonify({'success': True, 'event': updated_event})
                
        return jsonify({'success': False, 'message': 'Event not found'}), 404

@app.route('/api/events/delete/<event_id>', methods=['POST'])
def delete_event(event_id):
    username = session.get('username')
    if not username:
        return jsonify({"success": False, "message": "กรุณาเข้าสู่ระบบ"}), 401

    with data_lock:
        events = load_events()
        
        # Find event to check permission
        target_event = None
        for e in events:
            if e['id'] == event_id:
                target_event = e
                break
                
        if not target_event:
            return jsonify({'success': False, 'message': 'Event not found'}), 404
            
        users = load_users()
        event_owner = target_event.get('owner', 'สโมสรนักศึกษา')
        if users[username]['role'] != 'admin' and users[username]['name'] != event_owner:
            return jsonify({"success": False, "message": "คุณไม่มีสิทธิ์ลบกิจกรรมของสาขาอื่น"}), 403

        db_delete_event(event_id)
        return jsonify({'success': True})

@app.route('/api/events/<event_id>/toggle-visibility', methods=['POST'])
def toggle_event_visibility(event_id):
    username = session.get('username')
    if not username:
        return jsonify({"success": False, "message": "กรุณาเข้าสู่ระบบ"}), 401
    
    with data_lock:
        users = load_users()
        if users.get(username, {}).get('role') not in ['admin', 'major']:
            return jsonify({"success": False, "message": "Unauthorized"}), 403
        events = load_events()
        for event in events:
            if event['id'] == event_id:
                if users[username]['role'] != 'admin' and users[username]['name'] != event.get('owner', ''):
                    return jsonify({"success": False, "message": "คุณไม่มีสิทธิ์จัดการกิจกรรมนี้"}), 403
                event['hidden'] = not event.get('hidden', False)
                db_update_event(event)
                return jsonify({"success": True, "hidden": event['hidden']})
        return jsonify({"success": False, "message": "ไม่พบกิจกรรม"}), 404

# ==================== REGISTRATION SYSTEM ====================

@app.route('/api/events/<event_id>/register', methods=['POST'])
def register_event(event_id):
    username = session.get('username')
    if not username:
        return jsonify({"success": False, "message": "กรุณาเข้าสู่ระบบก่อน"}), 401
    users = load_users()
    if users.get(username, {}).get('role') != 'student':
        return jsonify({"success": False, "message": "เฉพาะนักศึกษาเท่านั้นที่จองกิจกรรมได้"}), 403
    
    with data_lock:
        events = load_events()
        # Auto-open check before processing registration
        if process_auto_open(events):
            for e in events:
                db_update_event(e)
            
        event = next((e for e in events if e['id'] == event_id), None)
        if not event:
            return jsonify({"success": False, "message": "ไม่พบกิจกรรม"}), 404
        if not event.get('registration_open', False):
            return jsonify({"success": False, "message": "กิจกรรมนี้ยังไม่เปิดรับการจอง"}), 400
        regs = load_registrations()
        # Check duplicate
        existing = next((r for r in regs if r['event_id'] == event_id and r['username'] == username and r['status'] != 'cancelled'), None)
        if existing:
            return jsonify({"success": False, "message": "คุณจองกิจกรรมนี้แล้ว"}), 400
        # Check capacity
        max_p = event.get('max_participants', 0)
        status = "confirmed"
        if max_p > 0:
            active_confirmed = sum(1 for r in regs if r['event_id'] == event_id and r['status'] == 'confirmed')
            if active_confirmed >= max_p:
                status = "waitlist"

        user_info = users[username]
        reg = {
            "id": "reg_" + uuid.uuid4().hex[:10],
            "event_id": event_id,
            "event_title": event.get('title', ''),
            "event_date": event.get('date', ''),
            "username": username,
            "name": user_info.get('name', username),
            "major": user_info.get('major', ''),
            "email": user_info.get('email', ''),
            "timestamp": time.strftime('%Y-%m-%dT%H:%M:%S'),
            "status": status
        }
        regs.append(reg)
        db_add_registration(reg)

    # Send confirmation email
    if user_info.get('email'):
        subject = f"ยืนยันการจอง: {event.get('title', '')}" if status == "confirmed" else f"สถานะสำรองที่นั่ง: {event.get('title', '')}"
        status_title = "✅ จองกิจกรรมสำเร็จ!" if status == "confirmed" else "⏳ คุณอยู่ในรายชื่อสำรอง"
        status_color = "#0284c7" if status == "confirmed" else "#f59e0b"
        status_desc = "ยืนยันที่นั่งแล้ว" if status == "confirmed" else "รายชื่อสำรอง (จะแจ้งให้ทราบหากมีที่นั่งว่าง)"
        
        body = f"""
        <div style="font-family:Kanit,sans-serif;max-width:500px;margin:auto;padding:24px;background:#f8fafc;border-radius:12px;">
            <h2 style="color:{status_color};">{status_title}</h2>
            <p>สวัสดี <strong>{user_info.get('name', username)}</strong></p>
            <div style="background:white;padding:16px;border-radius:8px;border-left:4px solid {status_color};margin:16px 0;">
                <p><strong>📅 กิจกรรม:</strong> {event.get('title', '')}</p>
                <p><strong>🗓️ วันที่:</strong> {event.get('date', '')}</p>
                <p><strong>📍 สถานที่:</strong> {event.get('location', 'ยังไม่ระบุ')}</p>
                <p><strong>🏷️ สถานะ:</strong> {status_desc}</p>
            </div>
            <p style="color:#64748b;font-size:13px;">คณะวิทยาศาสตร์และเทคโนโลยี มหาวิทยาลัยราชภัฏสกลนคร</p>
        </div>"""
        send_email_async(user_info['email'], subject, body)

    return jsonify({"success": True, "message": "จองสำเร็จ!" if status == "confirmed" else "ลงชื่อสำรองสำเร็จ!", "status": status, "registration": reg})

@app.route('/api/events/<event_id>/unregister', methods=['POST'])
def unregister_event(event_id):
    username = session.get('username')
    if not username:
        return jsonify({"success": False, "message": "กรุณาเข้าสู่ระบบ"}), 401
    
    with data_lock:
        regs = load_registrations()
        reg = next((r for r in regs if r['event_id'] == event_id and r['username'] == username and r['status'] != 'cancelled'), None)
        if not reg:
            return jsonify({"success": False, "message": "ไม่พบการจองของคุณ"}), 404
        reg['status'] = 'cancelled'
        db_update_registration_status(reg_id, 'cancelled')
        return jsonify({"success": True, "message": "ยกเลิกการจองแล้ว"})

@app.route('/api/registrations/<reg_id>/status', methods=['POST'])
@require_role('admin', 'major', 'student')
def update_registration_status(reg_id):
    username = session.get('username')
    users = load_users()
    user = users.get(username)

    data = request.json
    new_status = data.get('status')
    if not new_status:
        return jsonify({"success": False, "message": "กรุณาระบุสถานะ"}), 400

    with data_lock:
        regs = load_registrations()
        reg = next((r for r in regs if r['id'] == reg_id), None)
        if not reg:
            return jsonify({"success": False, "message": "ไม่พบข้อมูลการจอง"}), 404

        # Permission check: Admin/Major can change status, Student can only cancel their own
        if user['role'] not in ['admin', 'major'] and reg['username'] != username:
            return jsonify({"success": False, "message": "คุณไม่มีสิทธิ์จัดการการจองนี้"}), 403
        
        if user['role'] not in ['admin', 'major'] and new_status != 'cancelled':
            return jsonify({"success": False, "message": "คุณสามารถทำได้เพียงยกเลิกการจองเท่านั้น"}), 403

        reg['status'] = new_status
        db_update_registration_status(reg_id, new_status)
        
        # Add notification
        if new_status == 'confirmed':
            add_notification(reg['username'], "ยืนยันการจองแล้ว", f"การจองกิจกรรม {reg['event_title']} ของคุณได้รับการยืนยันแล้ว", "success")
        elif new_status == 'cancelled':
            add_notification(reg['username'], "ยกเลิกการจองแล้ว", f"การจองกิจกรรม {reg['event_title']} ของคุณถูกยกเลิก", "warning")
            
        return jsonify({"success": True, "message": f"อัปเดตสถานะเรียบร้อยแล้ว"})

@app.route('/api/my/registrations', methods=['GET'])
def my_registrations():
    username = session.get('username')
    if not username:
        return jsonify({"success": False, "message": "กรุณาเข้าสู่ระบบ"}), 401
    regs = load_registrations()
    my_regs = [r for r in regs if r['username'] == username]
    return jsonify(my_regs)

@app.route('/api/events/<event_id>/registrations', methods=['GET'])
@require_role('admin', 'major')
def event_registrations(event_id):
    regs = load_registrations()
    event_regs = [r for r in regs if r['event_id'] == event_id]
    return jsonify(event_regs)

@app.route('/api/events/<event_id>/my-registration', methods=['GET'])
def my_event_registration(event_id):
    username = session.get('username')
    if not username:
        return jsonify(None)
    regs = load_registrations()
    reg = next((r for r in regs if r['event_id'] == event_id and r['username'] == username and r['status'] != 'cancelled'), None)
    return jsonify(reg)

# =============================================================

@app.route('/api/student/participate', methods=['POST'])
def submit_participation():
    username = session.get('username')
    if not username:
        return jsonify({"success": False, "message": "กรุณาเข้าสู่ระบบ"}), 401
        
    users = load_users()
    if username not in users or users[username].get('role') != 'student':
        return jsonify({"success": False, "message": "เฉพาะนักศึกษาเท่านั้น"}), 403
        
    with data_lock:
        if 'file' not in request.files:
            return jsonify({"success": False, "message": "ไม่พบไฟล์รูปภาพ"}), 400
            
        file = request.files['file']
        event_id = request.form.get('event_id')
    
        if not event_id or file.filename == '':
            return jsonify({"success": False, "message": "ข้อมูลไม่ครบถ้วน"}), 400

        events = load_events()
        event = next((e for e in events if e['id'] == event_id), None)
        if not event:
            return jsonify({"success": False, "message": "ไม่พบกิจกรรม"}), 404
            
        # Check if already participated BEFORE saving file
        participations = load_participations()
        for p in participations:
            if p.get('username') == username and p.get('event_id') == event_id:
                return jsonify({"success": False, "message": "คุณได้ส่งภาพสำหรับกิจกรรมนี้ไปแล้ว"}), 400

        # Use server-side event data for integrity
        actual_title = event.get('title', 'กิจกรรม')
        actual_date = event.get('date', '')
        actual_score = int(event.get('score', 0))

        if file and allowed_file(file.filename):
            # Strict validation: check MIME type if possible, or just stay with extension but harden path
            ext = file.filename.rsplit('.', 1)[1].lower()
            # Ensure only allowed characters in filename and unique name
            raw_filename = f"{username}_{event_id}_{uuid.uuid4().hex[:8]}.{ext}"
            filename = secure_filename(raw_filename)
            filepath = os.path.join(ACTIVITIES_UPLOAD_FOLDER, filename)
            
            # Verify the path is still within the upload folder (prevent path traversal)
            if not os.path.abspath(filepath).startswith(os.path.abspath(ACTIVITIES_UPLOAD_FOLDER)):
                return jsonify({"success": False, "message": "Invalid file path"}), 400
                
            # 5MB size limit check
            file.seek(0, os.SEEK_END)
            file_size = file.tell()
            file.seek(0)
            if file_size > 5 * 1024 * 1024:
                return jsonify({"success": False, "message": "ไฟล์มีขนาดใหญ่เกินไป (จำกัด 5MB)"}), 400

            file.save(filepath)
            
            record = {
                "id": str(uuid.uuid4()),
                "username": username,
                "student_name": users[username]['name'],
                "major": users[username].get('major'),
                "event_id": event_id,
                "event_title": actual_title,
                "event_date": actual_date,
                "score": actual_score,
                "timestamp": datetime.now().isoformat(),
                "image_url": f"/uploads/activities/{filename}",
                "status": "pending"
            }
            db_save_participation(record)
            
            # Send confirmation email
            student_email = users[username].get('email')
            if student_email:
                subject = f"ยืนยันการส่งผลงานกิจกรรม: {actual_title}"
                body = f"""
                <html>
                <body style="font-family: Arial, sans-serif; color: #333;">
                    <h2>สวัสดีคุณ {users[username]['name']}</h2>
                    <p>ระบบได้รับภาพยืนยันการเข้าร่วมกิจกรรมของคุณเรียบร้อยแล้ว</p>
                    <div style="background: #f8fafc; padding: 15px; border-left: 4px solid #0284c7; margin: 20px 0;">
                        <p style="margin: 0;"><strong>กิจกรรม:</strong> {actual_title}</p>
                        <p style="margin: 5px 0 0 0;"><strong>วันที่เข้าร่วม:</strong> {actual_date}</p>
                    </div>
                    <p>แอดมินสาขาจะทำการตรวจสอบความถูกต้องของผลงานต่อไป ขอบคุณที่ให้ความร่วมมือครับ</p>
                    <hr>
                    <p style="font-size: 12px; color: #888;">อีเมลฉบับนี้ส่งจากระบบอัตโนมัติ กรุณาอย่าตอบกลับ</p>
                </body>
                </html>
                """
                send_email_async(student_email, subject, body)
            
            # Notify major/admin users about the new submission
            student_name = users[username]['name']
            student_major = users[username].get('major', '')
            all_users = load_users()
            for u, udata in all_users.items():
                if udata.get('role') == 'admin':
                    add_notification(u, "📋 มีผลงานใหม่รอตรวจสอบ",
                        f"{student_name} ส่งหลักฐานกิจกรรม '{actual_title}' รอการอนุมัติ", "info")
                elif udata.get('role') == 'major' and udata.get('name') == student_major:
                    add_notification(u, "📋 มีผลงานนักศึกษารอตรวจสอบ",
                        f"{student_name} ส่งหลักฐานกิจกรรม '{actual_title}' รอการอนุมัติ", "info")
            
            return jsonify({"success": True, "message": "บันทึกประวัติการเข้าร่วมสำเร็จ"})
    
    return jsonify({"success": False, "message": "ประเภทไฟล์ไม่ได้รับอนุญาต"}), 400

@app.route('/api/student/history', methods=['GET'])
def get_student_history():
    username = session.get('username')
    if not username:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
        
    participations = load_participations()
    my_history = [p for p in participations if p.get('username') == username]
    return jsonify(my_history)

@app.route('/api/admin/student/<username>/activities', methods=['GET'])
@require_role('admin', 'major')
def get_student_activities(username):
    
    parts = load_participations()
    events = load_events()
    event_dict = {e['id']: e for e in events}
    
    student_acts = []
    for p in parts:
        if p['username'] == username:
            evt = event_dict.get(p['event_id'])
            if evt:
                student_acts.append({
                    "id": p['id'],
                    "title": evt['title'],
                    "date": evt['date'],
                    "owner": evt['owner'],
                    "score": p.get('score', evt.get('score', 0)),
                    "status": p.get('status', 'pending')
                })
    
    return jsonify(student_acts)

@app.route('/api/admin/participations/<part_id>', methods=['PUT', 'DELETE'])
@require_role('admin')
def manage_participation(part_id):
        
    participations = load_participations()
    part_index = next((i for i, p in enumerate(participations) if p['id'] == part_id), None)
    
    if part_index is None:
        return jsonify({"success": False, "message": "ไม่พบข้อมูลประวัติ"}), 404
        
    if request.method == 'DELETE':
        db_delete_participation(part_id)
        return jsonify({"success": True, "message": "ลบประวัติเรียบร้อยแล้ว"})
        
    if request.method == 'PUT':
        data = request.json
        p = next((p for p in load_participations() if p['id'] == part_id), None)
        if p:
            p['score'] = data.get('score', p.get('score', 0))
            p['status'] = data.get('status', p.get('status', 'pending'))
            db_save_participation(p)
        return jsonify({"success": True, "message": "อัปเดตข้อมูลเรียบร้อยแล้ว"})

@app.route('/api/admin/participations', methods=['GET'])
@require_role('admin', 'major')
def get_admin_participations():
    username = session.get('username')
    users = load_users()
    current_user = users[username]
    role = current_user.get('role')
    
    participations = load_participations()
    
    if role == 'admin':
        return jsonify(participations)
    else:
        # Major can only see participations of their students
        my_major_name = current_user.get('name')
        filtered = [p for p in participations if p.get('major') == my_major_name]
        return jsonify(filtered)

@app.route('/uploads/activities/<filename>')
def uploaded_activity_file(filename):
    return send_from_directory(ACTIVITIES_UPLOAD_FOLDER, filename)

@app.route('/api/admin/event/<event_id>/students', methods=['GET'])
@require_role('admin', 'major')
def get_event_students(event_id):
    username = session.get('username')
    users = load_users()
    current_user = users[username]
    role = current_user.get('role')
    my_major_name = current_user.get('name')
    
    # Load participations for this event
    participations = load_participations()
    event_parts = {p['username']: p for p in participations if p.get('event_id') == event_id}
    
    result = []
    for u_id, u_data in users.items():
        if u_data.get('role') == 'student':
            # Major can only see their students
            if role == 'major' and u_data.get('major') != my_major_name:
                continue
                
            part = event_parts.get(u_id)
            if part:
                status = part.get('status', 'pending')
                image_url = part.get('image_url')
                part_id = part.get('id')
            else:
                status = 'not_participated'
                image_url = None
                part_id = None
                
            result.append({
                "username": u_id,
                "name": u_data.get('name'),
                "major": u_data.get('major'),
                "status": status,
                "image_url": image_url,
                "participation_id": part_id
            })
            
    return jsonify(result)

@app.route('/api/admin/participations/update_status', methods=['POST'])
@require_role('admin', 'major')
def update_participation_status():
    data = request.json
    event_id = data.get('event_id')
    updates = data.get('updates') # List of dicts: {"username": "123", "status": "approved"}
    
    if not event_id or not updates:
        return jsonify({"success": False, "message": "ข้อมูลไม่ครบถ้วน"}), 400
        
    with data_lock:
        events = load_events()
        event = next((e for e in events if e['id'] == event_id), None)
    if not event:
        return jsonify({"success": False, "message": "ไม่พบกิจกรรม"}), 404
        
    event_score = int(event.get('score', 0))
    event_title = event.get('title', 'กิจกรรม')
    
    participations = load_participations()
    users = load_users()
    
    for update in updates:
        target_username = update.get('username')
        new_status = update.get('status') # 'approved' or 'rejected'
        
        # Find existing participation
        part = next((p for p in participations if p.get('event_id') == event_id and p.get('username') == target_username), None)
        
        if part:
            part['status'] = new_status
            if 'score' not in part or part['score'] != event_score:
                part['score'] = event_score
        else:
            # If rejected/not participated and no record exists, create one
            part = {
                "id": str(uuid.uuid4()),
                "username": target_username,
                "student_name": users[target_username]['name'],
                "major": users[target_username].get('major'),
                "event_id": event_id,
                "event_title": event_title,
                "event_date": event.get('date', ''),
                "image_url": None,
                "status": new_status,
                "score": event_score
            }
            participations.append(part)
            
        # Send Email (for both new and updated records)
        student_email = users[target_username].get('email')
        if student_email:
            if new_status == 'approved':
                subject = f"ยืนยันการเข้าร่วมกิจกรรม: {event_title}"
                body = f"""
                <html><body style="font-family: Arial, sans-serif;">
                    <h2>ยินดีด้วยคุณ {users[target_username]['name']}!</h2>
                    <p>การเข้าร่วมกิจกรรม <strong>{event_title}</strong> ของคุณได้รับการอนุมัติเรียบร้อยแล้ว</p>
                    <p style="font-size: 18px; color: #16a34a;">คุณได้รับคะแนน: <strong>{event_score} คะแนน</strong></p>
                </body></html>
                """
                send_email_async(student_email, subject, body)
            elif new_status == 'rejected':
                subject = f"อัปเดตสถานะกิจกรรม: {event_title}"
                body = f"""
                <html><body style="font-family: Arial, sans-serif;">
                    <h2>เรียนคุณ {users[target_username]['name']}</h2>
                    <p>ระบบตรวจสอบพบว่าสถานะของคุณในกิจกรรม <strong>{event_title}</strong> คือ <span style="color: #dc2626; font-weight: bold;">ไม่ผ่าน / ไม่เข้าร่วม</span></p>
                    <p>หากมีข้อสงสัยโปรดติดต่อแอดมินสาขาของคุณ</p>
                </body></html>
                """
                send_email_async(student_email, subject, body)
                
        # Add Notification
        if new_status == 'approved':
            add_notification(target_username, "กิจกรรมผ่านแล้ว!", f"การเข้าร่วมกิจกรรม {event_title} ของคุณได้รับการอนุมัติ และคุณได้รับ {event_score} คะแนน", "success")
        elif new_status == 'rejected':
            add_notification(target_username, "กิจกรรมไม่ผ่าน", f"การเข้าร่วมกิจกรรม {event_title} ของคุณไม่ได้รับการอนุมัติ กรุณาติดต่อแอดมินสาขา", "danger")
                
    db_save_participation(participations[part_index])
    return jsonify({"success": True, "message": "อัปเดตสถานะเรียบร้อยแล้ว"})

@app.route('/api/admin/update-status-bulk', methods=['POST'])
@require_role('admin', 'major')
def update_status_bulk():
    username = session.get('username')
    users = load_users()
    current_user = users[username]
    role = current_user.get('role')
        
    data = request.json
    event_id = data.get('event_id')
    usernames = data.get('usernames', [])
    new_status = data.get('status')
    custom_scores = data.get('scores', {}) # Map: {username: score}
    
    if not event_id or not usernames or not new_status:
        return jsonify({"success": False, "message": "ข้อมูลไม่ครบถ้วน"}), 400
        
    with data_lock:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('BEGIN TRANSACTION')
        try:
            events = load_events()
            event = next((e for e in events if e['id'] == event_id), None)
            if not event: return jsonify({"success": False, "message": "ไม่พบกิจกรรม"}), 404
            
            default_score = int(event.get('score', 0))
            event_title = event.get('title', 'กิจกรรม')
            participations = load_participations()
            
            for target_u in usernames:
                if target_u not in users: continue
                
                # Check permission if major
                if role == 'major' and users[target_u].get('major') != current_user.get('name'):
                    continue 
                    
                part = next((p for p in participations if p.get('event_id') == event_id and p.get('username') == target_u), None)
                
                final_score = int(custom_scores.get(target_u, default_score))
                
                if part:
                    c.execute('UPDATE participations SET status=?, score=? WHERE id=?', (new_status, final_score, part['id']))
                else:
                    new_id = str(uuid.uuid4())
                    c.execute('''
                        INSERT INTO participations (
                            id, username, student_name, major, event_id, event_title,
                            event_date, score, timestamp, image_url, status
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        new_id, target_u, users[target_u]['name'], users[target_u].get('major'),
                        event_id, event_title, event.get('date', ''), 0,
                        datetime.now().isoformat(), None, new_status
                    ))
                    # Actually score should be set for new ones too? Yes.
                    c.execute('UPDATE participations SET score=? WHERE id=?', (final_score, new_id))
                    
                # Email Notification
                student_email = users[target_u].get('email')
                if student_email:
                    if new_status == 'approved':
                        subject = f"ยืนยันการเข้าร่วมกิจกรรม: {event_title}"
                        body = f"<html><body><h2>ยินดีด้วย!</h2><p>กิจกรรม {event_title} ได้รับการอนุมัติแล้ว คุณได้รับ {final_score} คะแนน</p></body></html>"
                        send_email_async(student_email, subject, body)
                    elif new_status == 'rejected':
                        subject = f"แจ้งเตือนสถานะกิจกรรม: {event_title}"
                        body = f"<html><body><h2>แจ้งเตือน</h2><p>ผลงานกิจกรรม {event_title} ของคุณไม่ผ่านการอนุมัติ</p></body></html>"
                        send_email_async(student_email, subject, body)
                    
                # Add Notification
                if new_status == 'approved':
                    # Need to do add_notification within transaction or separately. 
                    # add_notification uses its own lock/conn, which is fine but not in same transaction.
                    # For simplicity, we keep it separate as it is already.
                    add_notification(target_u, "กิจกรรมผ่านแล้ว!", f"การเข้าร่วมกิจกรรม {event_title} ของคุณได้รับการอนุมัติ และคุณได้รับ {final_score} คะแนน", "success")
                elif new_status == 'rejected':
                    add_notification(target_u, "กิจกรรมไม่ผ่าน", f"การเข้าร่วมกิจกรรม {event_title} ของคุณไม่ได้รับการอนุมัติ กรุณาติดต่อแอดมินสาขา", "danger")

            conn.commit()
            _cache["participations"]["data"] = None
        except Exception as e:
            conn.rollback()
            print(f"Bulk update error: {e}")
            return jsonify({"success": False, "message": str(e)}), 500
        finally:
            conn.close()
    return jsonify({"success": True, "message": "อัปเดตเรียบร้อยแล้ว"})

@app.route('/api/admin/reports/students', methods=['GET'])
@require_role('admin', 'major')
def get_student_report():
    
    with data_lock:
        users = load_users()
        events = load_events()
        participations = load_participations()
    
    event_scores = {e['id']: int(e.get('score', 0)) for e in events}
    
    # Pre-calculate scores for each student in one pass
    student_stats = {} # {username: {"score": 0, "count": 0}}
    for p in participations:
        if p.get('status') == 'approved':
            u_id = p.get('username')
            if u_id not in student_stats:
                student_stats[u_id] = {"score": 0, "count": 0}
            
            # Use score from participation record, fallback to event default
            score = p.get('score', event_scores.get(p.get('event_id'), 0))
            student_stats[u_id]["score"] += int(score)
            student_stats[u_id]["count"] += 1
    
    report = []
    current_username = session.get('username')
    current_user_role = users.get(current_username, {}).get('role')
    
    for u_id, u_info in users.items():
        role = u_info.get('role')
        # Include students for everyone, and major admins only for super admins
        if role == 'student' or (current_user_role == 'admin' and role == 'major'):
            stats = student_stats.get(u_id, {"score": 0, "count": 0})
            
            report.append({
                "username": u_id,
                "name": u_info.get('name'),
                "major": u_info.get('major') or u_info.get('name'), # Fallback for admins
                "score": stats["score"],
                "participated_count": stats["count"],
                "year": get_student_year(u_id) if role == 'student' else "Admin",
                "role": role
            })
            
    # Filter logic in backend
    major_filter = request.args.get('major', 'all')
    year_filter = request.args.get('year', 'all')
    search_query = request.args.get('search', '').lower()
    
    filtered_report = []
    for item in report:
        # Filter by Major
        if major_filter != 'all' and item['major'] != major_filter:
            continue
        
        # Filter by Year
        if year_filter != 'all' and str(item['year']) != year_filter:
            continue
            
        # Filter by Search
        if search_query:
            if search_query not in str(item['username']).lower() and search_query not in str(item['name']).lower():
                continue
        
        filtered_report.append(item)

    # Pagination
    page = request.args.get('page', type=int)
    limit = request.args.get('limit', type=int)
    
    if page and limit:
        start = (page - 1) * limit
        end = start + limit
        return jsonify({
            "data": filtered_report[start:end],
            "total": len(filtered_report),
            "pages": (len(filtered_report) + limit - 1) // limit,
            "current_page": page
        })

    return jsonify(filtered_report)

@app.route('/api/admin/reset-password', methods=['POST'])
@require_role('admin', 'major')
def admin_reset_password():
    
    data = request.json
    target_username = data.get('username')
    new_password = data.get('new_password', '123456') # Default or custom
    
    with data_lock:
        users = load_users()
        if target_username not in users:
            return jsonify({"success": False, "message": "ไม่พบผู้ใช้งาน"}), 404
            
        users[target_username]['password'] = generate_password_hash(new_password)
        db_save_user(target_username, users[target_username])
        return jsonify({"success": True, "message": f"รีเซ็ตรหัสผ่านเป็น '{new_password}' เรียบร้อยแล้ว"})

@app.route('/api/admin/participations/delete/<part_id>', methods=['POST'])
@require_role('admin')
def delete_participation(part_id):
        
    participations = load_participations()
    part_index = next((i for i, p in enumerate(participations) if p['id'] == part_id), None)
    
    if part_index is None:
        return jsonify({"success": False, "message": "ไม่พบข้อมูลประวัติ"}), 404
        
    p_id = participations[part_index]['id']
    db_delete_participation(p_id)
    return jsonify({"success": True, "message": "ลบประวัติเรียบร้อยแล้ว"})

@app.route('/api/admin/delete-user', methods=['POST'])
@require_role('admin', 'major')
def admin_delete_user():
    username = session.get('username')
    
    data = request.json
    target_username = data.get('username')
    
    with data_lock:
        users = load_users()
        current_user = users.get(username)
        if not current_user:
            return jsonify({"success": False, "message": "Unauthorized"}), 401
            
        role = current_user.get('role')
            
        if target_username not in users:
            return jsonify({"success": False, "message": "ไม่พบผู้ใช้งาน"}), 404
        
        target_data = users[target_username]
        if target_data.get('role') == 'admin':
            return jsonify({"success": False, "message": "ไม่สามารถลบแอดมินส่วนกลางได้"}), 403

        if role == 'major':
            my_major_name = current_user.get('name')
            if target_data.get('role') != 'student' or target_data.get('major') != my_major_name:
                return jsonify({"success": False, "message": "คุณไม่มีสิทธิ์ลบผู้ใช้งานนอกสาขา"}), 403
            
        db_delete_user(target_username)
        db_delete_user_participations(target_username)
        return jsonify({"success": True, "message": "ลบผู้ใช้งานและประวัติเรียบร้อยแล้ว"})

@app.route('/api/leaderboard', methods=['GET'])
def get_leaderboard():
    events = load_events()
    event_scores = {e['id']: int(e.get('score', 0)) for e in events}
    
    participations = load_participations()
    users = load_users()
    
    scores = {}
    for p in participations:
        if p.get('status') == 'approved':
            u_id = p.get('username')
            if u_id in users:
                if u_id not in scores:
                    scores[u_id] = 0
                scores[u_id] += p.get('score', event_scores.get(p.get('event_id'), 0))
            
    # Format result
    leaderboard = []
    for u_id, score in scores.items():
        if u_id in users and users[u_id].get('role') == 'student':
            leaderboard.append({
                "username": u_id,
                "name": users[u_id].get('name'),
                "major": users[u_id].get('major'),
                "score": score
            })
            
    leaderboard.sort(key=lambda x: x['score'], reverse=True)
    return jsonify(leaderboard[:10]) # Return Top 10

# --- Notifications API ---
@app.route('/api/notifications', methods=['GET'])
def get_notifications():
    username = session.get('username')
    if not username:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    conn = get_db_connection()
    rows = conn.execute('''
        SELECT * FROM notifications 
        WHERE username = ? 
        ORDER BY created_at DESC 
        LIMIT 50
    ''', (username,)).fetchall()
    conn.close()
    
    return jsonify([dict(r) for r in rows])

@app.route('/api/notifications/unread-count', methods=['GET'])
def get_unread_notification_count():
    username = session.get('username')
    if not username:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    conn = get_db_connection()
    count = conn.execute('''
        SELECT COUNT(*) FROM notifications 
        WHERE username = ? AND is_read = 0
    ''', (username,)).fetchone()[0]
    conn.close()
    
    return jsonify({"count": count})

@app.route('/api/notifications/mark-as-read', methods=['POST'])
def mark_notifications_as_read():
    username = session.get('username')
    if not username:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    data = request.json or {}
    notif_id = data.get('id')
    
    conn = get_db_connection()
    if notif_id:
        conn.execute('''
            UPDATE notifications SET is_read = 1 
            WHERE id = ? AND username = ?
        ''', (notif_id, username))
    else:
        # Mark all as read
        conn.execute('''
            UPDATE notifications SET is_read = 1 
            WHERE username = ?
        ''', (username,))
    
    conn.commit()
    conn.close()
    
    return jsonify({"success": True})

@app.route('/ui-shared.js')
def serve_ui_shared():
    return send_from_directory('.', 'ui-shared.js')

@app.route('/theme-loader.js')
def serve_theme_loader():
    return send_from_directory('.', 'theme-loader.js')

@app.route('/script.js')
def serve_script():
    return send_from_directory('.', 'script.js')

@app.route('/style.css')
def serve_style():
    return send_from_directory('.', 'style.css')

@app.route('/manual.html')
def serve_manual():
    return send_from_directory('.', 'manual.html')

@app.route('/favicon.ico')
def serve_favicon():
    return send_from_directory('.', 'favicon.ico')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    print("==================================================")
    print("   UNIVERSITY ACTIVITY CALENDAR - PRODUCTION MODE")
    print("==================================================")
    
    try:
        from waitress import serve
        print(f"   Running with Waitress (Production Grade)")
        print(f"   Port: {port}")
        print("   Capacity: 1,000+ Concurrent Users (12 Threads)")
        print("==================================================")
        serve(app, host='0.0.0.0', port=port, threads=12)
    except ImportError:
        print("   Waitress not found. Running in Development Mode...")
        app.run(debug=True, port=port, host='0.0.0.0')
