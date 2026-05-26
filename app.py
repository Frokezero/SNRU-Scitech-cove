from dotenv import load_dotenv
import os
load_dotenv() # Load environment variables from .env if present

from flask import Flask, jsonify, request, send_from_directory, session, redirect, send_file, after_this_request
from werkzeug.security import generate_password_hash, check_password_hash
import json
from database import get_db_connection
import uuid
import re
import urllib.request
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
import hmac
import hashlib
import base64
import math

# Simple Cache for Performance
_cache = {
    "users": {"data": None, "time": 0},
    "events": {"data": None, "time": 0},
    "participations": {"data": None, "time": 0},
    "registrations": {"data": None, "time": 0}
}
CACHE_TTL = 2 # 2 seconds cache to reduce Disk I/O under high load

def safe_float(val, default):
    if val is None or val == "":
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default

def require_role(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            username = session.get('username')
            if not username:
                return jsonify({"success": False, "message": "กรุณาเข้าสู่ระบบ"}), 401
            user = db_get_user(username)
            if not user:
                return jsonify({"success": False, "message": "ไม่พบผู้ใช้งาน"}), 401
            if user.get('role') not in roles:
                return jsonify({"success": False, "message": "คุณไม่มีสิทธิ์เข้าถึงส่วนนี้"}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def send_email_async(to_email, subject, body):
    def send_email_task():
        try:
            # 1. Read from Environment Variables first
            sender_email = os.environ.get("SENDER_EMAIL")
            sender_password = os.environ.get("SENDER_PASSWORD")
            smtp_server = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
            try:
                smtp_port = int(os.environ.get("SMTP_PORT", 587))
            except:
                smtp_port = 587
            
            # 2. Fall back to email_config.json if not in env
            if not sender_email or not sender_password:
                if os.path.exists('email_config.json'):
                    with open('email_config.json', 'r', encoding='utf-8') as f:
                        config = json.load(f)
                    sender_email = config.get("sender_email")
                    sender_password = config.get("sender_password")
                    smtp_server = config.get("smtp_server", smtp_server)
                    try:
                        smtp_port = int(config.get("smtp_port", smtp_port))
                    except:
                        pass
            
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

def send_line_notification(to_id, message):
    def send_line_task():
        try:
            token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
            if not token or not to_id:
                return
            
            url = "https://api.line.me/v2/bot/message/push"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}"
            }
            body = {
                "to": to_id,
                "messages": [
                    {
                        "type": "text",
                        "text": message
                    }
                ]
            }
            
            req_data = json.dumps(body).encode('utf-8')
            req = urllib.request.Request(url, data=req_data, headers=headers, method='POST')
            with urllib.request.urlopen(req) as response:
                response.read()
        except Exception as e:
            print(f"Failed to send LINE notification to {to_id}: {e}")
            
    if not to_id:
        return
    thread = threading.Thread(target=send_line_task)
    thread.start()

def get_premium_email_html(title, content_html, type_color='#0ea5e9', action_url=None, action_text=None):
    action_button_html = ""
    if action_url and action_text:
        action_button_html = f"""
        <div style="text-align: center; margin: 30px 0;">
            <a href="{action_url}" style="background: {type_color}; color: white; padding: 12px 30px; border-radius: 25px; text-decoration: none; font-weight: bold; font-size: 15px; box-shadow: 0 4px 15px {type_color}40; display: inline-block; transition: all 0.2s ease;">{action_text}</a>
        </div>
        """
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Kanit:wght@300;400;500;600;700&display=swap');
            body {{
                font-family: 'Kanit', 'Helvetica Neue', Helvetica, Arial, sans-serif;
                margin: 0;
                padding: 0;
                background-color: #f1f5f9;
                color: #1e293b;
            }}
        </style>
    </head>
    <body style="font-family: 'Kanit', sans-serif; background-color: #f1f5f9; padding: 30px 15px; margin: 0;">
        <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 24px; box-shadow: 0 10px 30px rgba(0,0,0,0.05); overflow: hidden; border: 1px solid #e2e8f0;">
            <!-- Top Color Header -->
            <div style="background: linear-gradient(135deg, {type_color} 0%, {type_color}dd 100%); padding: 35px 30px; text-align: center; color: white;">
                <h1 style="margin: 0; font-size: 24px; font-weight: 700; letter-spacing: 0.5px; text-shadow: 0 2px 4px rgba(0,0,0,0.1);">{title}</h1>
            </div>
            
            <!-- Main Content Area -->
            <div style="padding: 40px 35px; line-height: 1.6;">
                {content_html}
                
                {action_button_html}
            </div>
            
            <!-- Footer Area -->
            <div style="background-color: #f8fafc; padding: 25px 35px; text-align: center; border-top: 1px solid #f1f5f9;">
                <p style="margin: 0 0 8px 0; font-size: 13px; font-weight: 600; color: #475569;">คณะวิทยาศาสตร์และเทคโนโลยี มหาวิทยาลัยราชภัฏสกลนคร</p>
                <p style="margin: 0; font-size: 11px; color: #94a3b8; line-height: 1.4;">อีเมลฉบับนี้ส่งจากระบบอัตโนมัติโดยระบบปฏิทินกิจกรรมนักศึกษา กรุณาอย่าตอบกลับอีเมลนี้โดยตรง</p>
            </div>
        </div>
    </body>
    </html>
    """

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'super-secret-sakon-nakhon-key')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB upload limit
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_HTTPONLY'] = True

@app.teardown_appcontext
def close_db_connections(exception):
    from flask import g
    db_connections = getattr(g, '_db_connections', None)
    if db_connections:
        for conn in db_connections:
            try:
                conn.close()
            except Exception:
                pass

DATA_FILE = 'events.json'

USER_FILE = 'users.json'

data_lock = threading.RLock()

def load_users():
    with data_lock:
        conn = get_db_connection()
        rows = conn.execute('SELECT * FROM users').fetchall()
        conn.close()
        return {r['username']: dict(r) for r in rows}

def db_get_user(username):
    if not username:
        return None
    with data_lock:
        conn = get_db_connection()
        row = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
        return dict(row) if row else None

def db_save_user(username, data):
    with data_lock:
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO users (username, password, name, email, major, role, line_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(username) DO UPDATE SET
                password=excluded.password,
                name=excluded.name,
                email=excluded.email,
                major=excluded.major,
                role=excluded.role,
                line_id=excluded.line_id
        ''', (username, data.get('password',''), data.get('name',''), data.get('email',''), data.get('major',''), data.get('role','student'), data.get('line_id','')))
        conn.commit()
        conn.close()

def db_delete_user(username):
    with data_lock:
        conn = get_db_connection()
        # Delete dependent references first to satisfy foreign key constraints
        conn.execute('DELETE FROM participations WHERE username=?', (username,))
        conn.execute('DELETE FROM registrations WHERE username=?', (username,))
        conn.execute('DELETE FROM users WHERE username=?', (username,))
        conn.commit()
        conn.close()
        _cache["users"]["data"] = None
        _cache["participations"]["data"] = None
        _cache["registrations"]["data"] = None


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

login_attempts_lock = threading.RLock()
login_attempts = {} # {ip: {"count": X, "lockout_until": Y}}

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

def db_get_user_participations(username):
    if not username:
        return []
    with data_lock:
        conn = get_db_connection()
        rows = conn.execute('SELECT * FROM participations WHERE username = ?', (username,)).fetchall()
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

def db_get_user_registrations(username):
    if not username:
        return []
    with data_lock:
        conn = get_db_connection()
        rows = conn.execute('SELECT * FROM registrations WHERE username = ?', (username,)).fetchall()
        conn.close()
        return [dict(r) for r in rows]

def db_get_event_registrations(event_id):
    if not event_id:
        return []
    with data_lock:
        conn = get_db_connection()
        rows = conn.execute('SELECT * FROM registrations WHERE event_id = ?', (event_id,)).fetchall()
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
        
        # Extract all numbers from the date string
        numbers = re.findall(r'\d+', clean_date)
        if not numbers:
            return None
            
        # If only one number exists (e.g. 'เม.ย. 69' or 'ส.ค. 69'), it represents the year, default day to 1
        if len(numbers) == 1:
            day = 1
            year = int(numbers[0])
        else:
            # If multiple numbers exist (e.g. '15 มิ.ย. 69'), the first is day and the last is year
            day = int(numbers[0])
            year = int(numbers[-1])
        
        # Find Month (flexible matching)
        month = 1
        for m_name, m_idx in months_map.items():
            # Match month with or without trailing dot
            if m_name in clean_date or m_name.replace('.', '') in clean_date:
                month = m_idx
                break
        
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
    # Safe no-op as requested by user to remove the notification system
    return True

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
            e['registration_start'] = e.get('registration_start') or ""
            e['registration_end'] = e.get('registration_end') or ""
            e['latitude'] = safe_float(e.get('latitude'), 17.18994)
            e['longitude'] = safe_float(e.get('longitude'), 104.09153)
            
        _cache["events"] = {"data": data, "time": now}
        return data

def db_add_event(e):
    with data_lock:
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO events (
                id, title, date, category, location, owner, description,
                registration_open, max_participants, score, hidden, status, created_at,
                registration_start, registration_end, latitude, longitude
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            e.get('id'), e.get('title', ''), e.get('date', ''),
            e.get('category', ''), e.get('location', ''), e.get('owner', ''),
            e.get('description', ''), 1 if e.get('registration_open') else 0,
            int(e.get('max_participants', 0)), int(e.get('score', 0)),
            1 if e.get('hidden') else 0, e.get('status', 'รอการดำเนินการ'), e.get('created_at', ''),
            e.get('registration_start', ''), e.get('registration_end', ''),
            safe_float(e.get('latitude'), 17.18994), safe_float(e.get('longitude'), 104.09153)
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
                registration_open=?, max_participants=?, score=?, hidden=?, status=?,
                registration_start=?, registration_end=?, latitude=?, longitude=?
            WHERE id=?
        ''', (
            e.get('title', ''), e.get('date', ''), e.get('category', ''),
            e.get('location', ''), e.get('owner', ''), e.get('description', ''),
            1 if e.get('registration_open') else 0, int(e.get('max_participants', 0)),
            int(e.get('score', 0)), 1 if e.get('hidden') else 0, e.get('status', 'รอการดำเนินการ'),
            e.get('registration_start', ''), e.get('registration_end', ''),
            safe_float(e.get('latitude'), 17.18994), safe_float(e.get('longitude'), 104.09153), e.get('id')
        ))
        conn.commit()
        conn.close()
        _cache["events"]["data"] = None # Invalidate cache

def db_delete_event(event_id):
    with data_lock:
        conn = get_db_connection()
        # Delete dependent references first to satisfy foreign key constraints
        conn.execute('DELETE FROM participations WHERE event_id=?', (event_id,))
        conn.execute('DELETE FROM registrations WHERE event_id=?', (event_id,))
        conn.execute('DELETE FROM events WHERE id=?', (event_id,))
        conn.commit()
        conn.close()
        _cache["events"]["data"] = None # Invalidate cache
        _cache["participations"]["data"] = None # Invalidate cache
        _cache["registrations"]["data"] = None # Invalidate cache

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
# MANUAL BACKUP API
# =============================================================
@app.route('/api/admin/backup-db', methods=['GET'])
@require_role('admin')
def admin_backup_database():
    try:
        import tempfile
        import zipfile
        
        # Create a temporary directory/file to store the zip safely
        temp_dir = tempfile.mkdtemp()
        zip_path = os.path.join(temp_dir, f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip")
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Backup the SQLite database file
            if os.path.exists('database.sqlite'):
                zipf.write('database.sqlite', 'database.sqlite')
            # Include JSON data files to guarantee complete recovery
            for json_file in ['events.json', 'users.json', 'participations.json', 'registrations.json', 'carousel.json', 'email_config.json']:
                if os.path.exists(json_file):
                    zipf.write(json_file, json_file)
        
        # Safe cleanup of temp files after request has finished
        @after_this_request
        def cleanup(response):
            try:
                os.remove(zip_path)
                os.rmdir(temp_dir)
            except Exception as e:
                print(f"Cleanup error in backup: {e}")
            return response
            
        return send_file(
            zip_path,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f"scitech_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        )
    except Exception as e:
        return jsonify({"success": False, "message": f"การสำรองข้อมูลล้มเหลว: {str(e)}"}), 500

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


@app.route('/portfolio')
def portfolio():
    if 'username' not in session:
        return redirect('/login')
    users = load_users()
    if session['username'] not in users or users[session['username']]['role'] != 'student':
        return redirect('/')
    return send_from_directory('.', 'portfolio.html')

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
    if request.path == '/checkin':
        import urllib.parse
        return redirect(f'/login?next={urllib.parse.quote(request.full_path)}')
    return redirect('/login')

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    ip = request.remote_addr
    now = time.time()
    
    with login_attempts_lock:
        attempt = login_attempts.get(ip, {"count": 0, "lockout_until": 0})
        if attempt["lockout_until"] > now:
            remaining = int(attempt["lockout_until"] - now)
            minutes = remaining // 60
            seconds = remaining % 60
            return jsonify({
                "success": False, 
                "message": f"คุณถูกล็อกการเข้าใช้งานชั่วคราวเนื่องจากรหัสผ่านผิดเกินกำหนด โปรดลองใหม่ในอีก {minutes} นาที {seconds} วินาที"
            }), 429
            
    users = load_users()
    if username in users and check_password_hash(users[username]['password'], password):
        user_role = users[username].get('role')
        
        with login_attempts_lock:
            login_attempts.pop(ip, None)
            
        session['username'] = username
        with session_lock:
            ACTIVE_SESSIONS[username] = time.time()
        return jsonify({"success": True, "user": {"name": users[username]['name'], "role": user_role}})
        
    with login_attempts_lock:
        attempt = login_attempts.get(ip, {"count": 0, "lockout_until": 0})
        if attempt["lockout_until"] > 0 and attempt["lockout_until"] <= now:
            attempt["count"] = 0
            attempt["lockout_until"] = 0
            
        attempt["count"] += 1
        if attempt["count"] >= 5:
            attempt["lockout_until"] = now + 15 * 60
            login_attempts[ip] = attempt
            return jsonify({
                "success": False, 
                "message": "เข้าสู่ระบบล้มเหลวครบ 5 ครั้ง บัญชี/IP นี้ถูกระงับชั่วคราว 15 นาที"
            }), 429
        else:
            login_attempts[ip] = attempt
            remaining_attempts = 5 - attempt["count"]
            return jsonify({
                "success": False, 
                "message": f"Username หรือ Password ไม่ถูกต้อง (สามารถลองใหม่ได้อีก {remaining_attempts} ครั้ง)"
            }), 401

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
        u = db_get_user(username)
        if u:
            return jsonify({
                "success": True, 
                "user": {
                    "username": username,
                    "name": u['name'], 
                    "role": u['role'],
                    "major": u.get('major', u.get('name')),
                    "email": u.get('email', ''),
                    "line_id": u.get('line_id', ''),
                    "year": get_student_year(username) if u.get('role') == 'student' else None
                }
            })
    return jsonify({"success": False}), 401

@app.route('/api/user/update-profile', methods=['POST'])
def update_profile():
    username = session.get('username')
    if not username:
        return jsonify({"success": False, "message": "กรุณาเข้าสู่ระบบ"}), 401
    
    data = request.json
    new_email = data.get('email')
    new_line_id = data.get('line_id')
    
    with data_lock:
        u = db_get_user(username)
        if not u:
            return jsonify({"success": False, "message": "ไม่พบผู้ใช้งาน"}), 404
        
        if new_email:
            new_email = new_email.strip()
            # Simple email validation regex pattern
            if not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", new_email):
                return jsonify({"success": False, "message": "รูปแบบอีเมลไม่ถูกต้อง"}), 400
        
        u['email'] = new_email or ""
        u['line_id'] = new_line_id.strip() if new_line_id else ""
        db_save_user(username, u)
        
    return jsonify({"success": True, "message": "อัปเดตข้อมูลติดต่อเรียบร้อยแล้ว"})

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
    content_html = f"""
    <p style="font-size: 16px; margin-top: 0;">สวัสดีคุณ <strong>{user_target.get('name', username_target)}</strong>,</p>
    <p style="font-size: 15px; color: #334155;">เราได้รับคำร้องขอตั้งค่ารหัสผ่านใหม่สำหรับบัญชีผู้ใช้ระบบปฏิทินกิจกรรมของคุณ</p>
    <p style="font-size: 15px; color: #334155;">กรุณาคลิกปุ่มด้านล่างเพื่อดำเนินการเปลี่ยนรหัสผ่านใหม่ โดยลิงก์ความปลอดภัยนี้จะมีอายุการใช้งาน 15 นาที</p>
    <p style="font-size: 13px; color: #94a3b8; margin-top: 20px; border-top: 1px dashed #e2e8f0; padding-top: 15px;">* หากท่านไม่ได้ทำรายการส่งคำร้องนี้ กรุณาปล่อยผ่านและละเลยอีเมลฉบับนี้ได้ทันที</p>
    """
    body = get_premium_email_html(
        title="🔒 คำขอเปลี่ยนรหัสผ่าน",
        content_html=content_html,
        type_color="#0284c7",
        action_url=reset_link,
        action_text="เปลี่ยนรหัสผ่านใหม่"
    )
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
    content_html = f"""
    <p style="font-size: 16px; margin-top: 0;">สวัสดีคุณ <strong>{name}</strong>,</p>
    <p style="font-size: 15px; color: #334155;">การสมัครสมาชิกของท่านในระบบ <strong>ปฏิทินกิจกรรมนักศึกษา (University Activity Calendar)</strong> เสร็จสมบูรณ์แล้ว!</p>
    <div style="background: #f8fafc; padding: 20px; border-radius: 16px; border-left: 4px solid #8b5cf6; margin: 25px 0;">
        <h4 style="margin: 0 0 10px 0; color: #6d28d9; font-size: 14px; text-transform: uppercase;">ข้อมูลบัญชีผู้ใช้</h4>
        <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
            <tr>
                <td style="padding: 4px 0; color: #64748b; width: 40%;">รหัสนักศึกษา:</td>
                <td style="padding: 4px 0; font-weight: 600; color: #1e293b;">{username}</td>
            </tr>
            <tr>
                <td style="padding: 4px 0; color: #64748b;">สาขาวิชา:</td>
                <td style="padding: 4px 0; font-weight: 600; color: #1e293b;">{major}</td>
            </tr>
        </table>
    </div>
    <p style="font-size: 15px; margin-bottom: 0; color: #334155;">ท่านสามารถลงทะเบียนเข้าร่วมกิจกรรมต่าง ๆ เพื่อเก็บชั่วโมงคะแนนและสร้างพอร์ตโฟลิโอของคุณได้ทันที</p>
    """
    body = get_premium_email_html(
        title="🎉 ยินดีต้อนรับเข้าสู่ครอบครัว SciTech!",
        content_html=content_html,
        type_color="#8b5cf6",
        action_url=request.host_url,
        action_text="เข้าสู่ระบบเพื่อดูกิจกรรม"
    )
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
            
        db_save_user(target_user, users[target_user])
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

    current_time_str = datetime.now().strftime('%Y-%m-%dT%H:%M')
    for e in events:
        if 'owner' not in e:
            e['owner'] = "สโมสรนักศึกษา" # Default owner for old events
        e['registered_count'] = reg_counts.get(e['id'], 0)
        
        # Determine registration status dynamically based on dates
        reg_start = e.get('registration_start') or ""
        reg_end = e.get('registration_end') or ""
        if reg_start or reg_end:
            is_open = True
            if reg_start and current_time_str < reg_start:
                is_open = False
            if reg_end and current_time_str > reg_end:
                is_open = False
            e['registration_open'] = is_open
    
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
        new_event['registration_start'] = new_event.get('registration_start') or ""
        new_event['registration_end'] = new_event.get('registration_end') or ""
        
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
        
        # Trigger LINE notification for new event
        admin_line_id = os.environ.get("LINE_ADMIN_USER_ID")
        if admin_line_id:
            msg = f"🆕 กิจกรรมใหม่เปิดแล้ว! ขอเชิญร่วมกิจกรรม '{new_event.get('title')}' จัดขึ้นในวันที่ {new_event.get('date')} มาร่วมลงทะเบียนจองสิทธิ์กันได้เลยค่ะ/ครับ! ✨"
            send_line_notification(admin_line_id, msg)
            
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
                updated_event['registration_start'] = updated_event.get('registration_start') or ""
                updated_event['registration_end'] = updated_event.get('registration_end') or ""
                if 'hidden' in event:
                    updated_event['hidden'] = event['hidden']
                    
                events[i] = updated_event
                db_update_event(updated_event)
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
            
        current_time_str = datetime.now().strftime('%Y-%m-%dT%H:%M')
        reg_start = event.get('registration_start') or ""
        reg_end = event.get('registration_end') or ""
        
        if reg_start and current_time_str < reg_start:
            try:
                dt = datetime.strptime(reg_start, '%Y-%m-%dT%H:%M')
                start_formatted = dt.strftime('%d/%m/%Y %H:%M')
            except Exception:
                start_formatted = reg_start
            return jsonify({"success": False, "message": f"ยังไม่ถึงเวลาเปิดจองกิจกรรม (เปิดจองวันที่ {start_formatted})"}), 400
            
        if reg_end and current_time_str > reg_end:
            try:
                dt = datetime.strptime(reg_end, '%Y-%m-%dT%H:%M')
                end_formatted = dt.strftime('%d/%m/%Y %H:%M')
            except Exception:
                end_formatted = reg_end
            return jsonify({"success": False, "message": f"หมดเวลาเปิดจองกิจกรรมนี้แล้ว (ปิดจองวันที่ {end_formatted})"}), 400
            
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
        
    # Send notification
    notification_title = "📋 จองกิจกรรมสำเร็จ!" if status == "confirmed" else "⏳ อยู่ในรายชื่อสำรอง"
    notification_msg = f"คุณจองกิจกรรม {event.get('title', '')} เรียบร้อย" if status == "confirmed" else f"คุณอยู่ในรายชื่อสำรองสำหรับกิจกรรม {event.get('title', '')}"
    notification_type = "success" if status == "confirmed" else "info"
    add_notification(username, notification_title, notification_msg, notification_type)

    # Send confirmation email
    if user_info.get('email'):
        subject = f"ยืนยันการจอง: {event.get('title', '')}" if status == "confirmed" else f"สถานะสำรองที่นั่ง: {event.get('title', '')}"
        status_title = "✅ จองกิจกรรมสำเร็จ!" if status == "confirmed" else "⏳ คุณอยู่ในรายชื่อสำรอง"
        status_color = "#0284c7" if status == "confirmed" else "#f59e0b"
        status_desc = "ยืนยันที่นั่งแล้ว (Confirmed)" if status == "confirmed" else "รายชื่อสำรอง (Waitlist - จะแจ้งให้ทราบหากมีที่นั่งว่าง)"
        
        content_html = f"""
        <p style="font-size: 16px; margin-top: 0;">สวัสดีคุณ <strong>{user_info.get('name', username)}</strong>,</p>
        <p style="font-size: 15px; color: #334155;">ข้อมูลสถานะการจองกิจกรรมของท่านได้รับการบันทึกในระบบเรียบร้อยแล้ว ดังรายละเอียดด้านล่างนี้:</p>
        <div style="background: #f8fafc; padding: 20px; border-radius: 16px; border-left: 4px solid {status_color}; margin: 25px 0;">
            <h4 style="margin: 0 0 10px 0; color: {status_color}; font-size: 14px; text-transform: uppercase;">รายละเอียดกิจกรรม</h4>
            <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
                <tr>
                    <td style="padding: 6px 0; color: #64748b; width: 30%; vertical-align: top;">กิจกรรม:</td>
                    <td style="padding: 6px 0; font-weight: 600; color: #1e293b;">{event.get('title', '')}</td>
                </tr>
                <tr>
                    <td style="padding: 6px 0; color: #64748b; vertical-align: top;">วันที่จัด:</td>
                    <td style="padding: 6px 0; font-weight: 600; color: #1e293b;">{event.get('date', '')}</td>
                </tr>
                <tr>
                    <td style="padding: 6px 0; color: #64748b; vertical-align: top;">สถานที่:</td>
                    <td style="padding: 6px 0; font-weight: 600; color: #1e293b;">{event.get('location', 'ยังไม่ระบุ')}</td>
                </tr>
                <tr>
                    <td style="padding: 6px 0; color: #64748b; vertical-align: top;">สถานะที่นั่ง:</td>
                    <td style="padding: 6px 0; font-weight: 700; color: {status_color};">{status_desc}</td>
                </tr>
            </table>
        </div>
        """
        body = get_premium_email_html(
            title=status_title,
            content_html=content_html,
            type_color=status_color,
            action_url=request.host_url,
            action_text="ตรวจสอบประวัติการจอง"
        )
        send_email_async(user_info['email'], subject, body)

    # Trigger LINE notification
    # 1. Send to Student (if they have configured line_id)
    student_line_id = user_info.get('line_id')
    if student_line_id:
        status_thai = "สำเร็จแล้ว 🎉" if status == "confirmed" else "เรียบร้อยแล้ว (แต่อยู่ในคิวรายชื่อสำรอง)"
        std_msg = f"สวัสดีคุณ {user_info.get('name', username)}! คุณได้ทำรายการจองสิทธิ์เข้าร่วมกิจกรรม '{event.get('title', '')}' {status_thai}\n📅 วันที่จัด: {event.get('date', '')}\n📍 สถานที่: {event.get('location', 'ยังไม่ระบุ')}"
        send_line_notification(student_line_id, std_msg)
        
    # 2. Send to Admin / Group
    admin_line_id = os.environ.get("LINE_ADMIN_USER_ID")
    if admin_line_id:
        adm_msg = f"📢 แจ้งเตือนแอดมิน: นักศึกษา {user_info.get('name', username)} ({username}) ได้จองเข้าร่วมกิจกรรม '{event.get('title', '')}' เรียบร้อยแล้ว (สถานะ: {status})"
        send_line_notification(admin_line_id, adm_msg)

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
        db_update_registration_status(reg['id'], 'cancelled')
    
    # Send notification
    add_notification(username, "ยกเลิกการจองแล้ว", f"การจองกิจกรรม {reg.get('event_title', '')} ของคุณถูกยกเลิก", "warning")
    
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
    my_regs = db_get_user_registrations(username)
    return jsonify(my_regs)

@app.route('/api/events/<event_id>/registrations', methods=['GET'])
@require_role('admin', 'major')
def event_registrations(event_id):
    event_regs = db_get_event_registrations(event_id)
    return jsonify(event_regs)

@app.route('/api/events/<event_id>/my-registration', methods=['GET'])
def my_event_registration(event_id):
    username = session.get('username')
    if not username:
        return jsonify(None)
    regs = db_get_user_registrations(username)
    reg = next((r for r in regs if r['event_id'] == event_id and r['status'] != 'cancelled'), None)
    return jsonify(reg)

# =============================================================

@app.route('/api/student/participate', methods=['POST'])
def submit_participation():
    username = session.get('username')
    if not username:
        return jsonify({"success": False, "message": "กรุณาเข้าสู่ระบบ"}), 401
        
    user = db_get_user(username)
    if not user or user.get('role') != 'student':
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
        user_parts = db_get_user_participations(username)
        for p in user_parts:
            if p.get('event_id') == event_id:
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

            # Compress and save using Pillow to optimize server storage space
            saved_via_pillow = False
            try:
                from PIL import Image
                img = Image.open(file)
                
                # Convert RGBA/LA or Palette mode to RGB for standard format
                if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                    img = img.convert('RGB')
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Resize if larger than 1200px width/height while maintaining aspect ratio
                max_size = 1200
                width, height = img.size
                if width > max_size or height > max_size:
                    if width > height:
                        new_width = max_size
                        new_height = int(height * (max_size / width))
                    else:
                        new_height = max_size
                        new_width = int(width * (max_size / height))
                    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                # Save optimized image based on file extension
                if ext == 'png':
                    img.save(filepath, format='PNG', optimize=True)
                else:
                    img.save(filepath, format='JPEG', quality=80, optimize=True)
                saved_via_pillow = True
            except Exception as e:
                print(f"Pillow compression failed, falling back to raw save: {e}")
                # Reset stream pointer
                file.seek(0)
                
            if not saved_via_pillow:
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
                subject = f"📋 ได้รับเอกสาร/รูปภาพยืนยันผลงานแล้ว: {actual_title}"
                content_html = f"""
                <p>สวัสดีคุณ <strong>{users[username]['name']}</strong>,</p>
                <p>ระบบได้รับเอกสาร/รูปภาพหลักฐานยืนยันการเข้าร่วมกิจกรรมของคุณเรียบร้อยแล้ว รายละเอียดมีดังนี้:</p>
                <div style="background: #f8fafc; padding: 20px; border-radius: 12px; border-left: 4px solid #0284c7; margin: 20px 0;">
                    <p style="margin: 0 0 8px 0;"><strong>🏆 กิจกรรม:</strong> {actual_title}</p>
                    <p style="margin: 0 0 8px 0;"><strong>📅 วันที่จัดกิจกรรม:</strong> {actual_date}</p>
                    <p style="margin: 0;"><strong>⭐️ คะแนนเมื่ออนุมัติสำเร็จ:</strong> {actual_score} คะแนน</p>
                </div>
                <p>ขณะนี้ผลงานของคุณอยู่ในสถานะ <strong>"รอตรวจสอบ (Pending)"</strong> โดยแอดมินสาขาจะทำการตรวจสอบความถูกต้องของภาพถ่าย/หลักฐาน และอนุมัติชั่วโมงคะแนนกิจกรรมให้กับคุณในลำดับต่อไป</p>
                <p>ขอบคุณสำหรับการเข้าร่วมและส่งผลงานในครั้งนี้ครับ</p>
                """
                body = get_premium_email_html(
                    title="📋 ได้รับเอกสาร/รูปภาพยืนยันผลงานแล้ว",
                    content_html=content_html,
                    type_color='#0284c7'
                )
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
        
    my_history = db_get_user_participations(username)
    return jsonify(my_history)

@app.route('/api/admin/student/<username>/activities', methods=['GET'])
@require_role('admin', 'major')
def get_student_activities(username):
    
    parts = db_get_user_participations(username)
    events = load_events()
    event_dict = {e['id']: e for e in events}
    
    student_acts = []
    for p in parts:
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
        
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('BEGIN TRANSACTION')
        try:
            for update in updates:
                target_username = update.get('username')
                new_status = update.get('status') # 'approved' or 'rejected'
                
                if target_username not in users:
                    continue
                
                # Find existing participation
                part = next((p for p in participations if p.get('event_id') == event_id and p.get('username') == target_username), None)
                
                if part:
                    c.execute('UPDATE participations SET status=?, score=? WHERE id=?', (new_status, event_score, part['id']))
                else:
                    new_id = str(uuid.uuid4())
                    c.execute('''
                        INSERT INTO participations (
                            id, username, student_name, major, event_id, event_title,
                            event_date, score, timestamp, image_url, status
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        new_id, target_username, users[target_username]['name'], users[target_username].get('major'),
                        event_id, event_title, event.get('date', ''), event_score,
                        datetime.now().isoformat(), None, new_status
                    ))
                    
                # Send Email (for both new and updated records)
                student_email = users[target_username].get('email')
                if student_email:
                    if new_status == 'approved':
                        subject = f"🎉 ยินดีด้วย! การเข้าร่วมกิจกรรมได้รับการอนุมัติ: {event_title}"
                        content_html = f"""
                        <p>สวัสดีคุณ <strong>{users[target_username]['name']}</strong>,</p>
                        <p>เรามีความยินดีที่จะแจ้งให้ทราบว่า หลักฐานการเข้าร่วมกิจกรรมของคุณได้รับการตรวจสอบและ<strong>อนุมัติ (Approved)</strong> เรียบร้อยแล้ว!</p>
                        <div style="background: #f0fdf4; padding: 20px; border-radius: 12px; border-left: 4px solid #10b981; margin: 20px 0;">
                            <p style="margin: 0 0 8px 0;"><strong>🏆 กิจกรรม:</strong> {event_title}</p>
                            <p style="margin: 0 0 8px 0;"><strong>📅 วันที่จัดกิจกรรม:</strong> {event.get('date', '')}</p>
                            <p style="margin: 0; font-size: 18px; color: #10b981; font-weight: bold;"><strong>⭐️ คะแนนที่ได้รับ:</strong> +{event_score} คะแนน</p>
                        </div>
                        <p>คะแนนกิจกรรมนี้ได้รับการสะสมเข้าสู่บัญชีของคุณเรียบร้อยแล้ว คุณสามารถเข้าสู่ระบบเพื่อตรวจสอบคะแนนสะสมและดาวน์โหลดเกียรติบัตรอิเล็กทรอนิกส์ได้ทันที</p>
                        """
                        body = get_premium_email_html(
                            title="🎉 อนุมัติการเข้าร่วมกิจกรรมสำเร็จ",
                            content_html=content_html,
                            type_color='#10b981',
                            action_url=request.host_url + 'profile' if request else None,
                            action_text="ตรวจสอบคะแนนและเกียรติบัตร"
                        )
                        send_email_async(student_email, subject, body)
                    elif new_status == 'rejected':
                        subject = f"⚠️ แจ้งเตือน: หลักฐานกิจกรรมไม่ผ่านการอนุมัติ: {event_title}"
                        content_html = f"""
                        <p>สวัสดีคุณ <strong>{users[target_username]['name']}</strong>,</p>
                        <p>ระบบตรวจสอบพบว่าหลักฐานการเข้าร่วมกิจกรรม <strong>{event_title}</strong> ของคุณไม่ผ่านเกณฑ์การอนุมัติ หรือข้อมูลไม่สอดคล้องกับกิจกรรมดังกล่าว</p>
                        <div style="background: #fef2f2; padding: 20px; border-radius: 12px; border-left: 4px solid #ef4444; margin: 20px 0;">
                            <p style="margin: 0 0 8px 0;"><strong>🏆 กิจกรรม:</strong> {event_title}</p>
                            <p style="margin: 0 0 8px 0;"><strong>📅 วันที่จัดกิจกรรม:</strong> {event.get('date', '')}</p>
                            <p style="margin: 0; color: #ef4444; font-weight: bold;"><strong>❌ สถานะ:</strong> ไม่ผ่านการอนุมัติ (Rejected)</p>
                        </div>
                        <p>หากคุณเชื่อว่านี่เป็นข้อผิดพลาด หรือต้องการยื่นส่งหลักฐานใหม่อีกครั้ง กรุณาติดต่อประธานสาขาหรือแอดมินผู้ดูแลระบบของคณะวิชาเพื่อตรวจสอบเพิ่มเติม</p>
                        """
                        body = get_premium_email_html(
                            title="⚠️ กิจกรรมไม่ผ่านการอนุมัติ",
                            content_html=content_html,
                            type_color='#ef4444'
                        )
                        send_email_async(student_email, subject, body)
                        
                # Add Notification
                if new_status == 'approved':
                    add_notification(target_username, "กิจกรรมผ่านแล้ว!", f"การเข้าร่วมกิจกรรม {event_title} ของคุณได้รับการอนุมัติ และคุณได้รับ {event_score} คะแนน", "success")
                elif new_status == 'rejected':
                    add_notification(target_username, "กิจกรรมไม่ผ่าน", f"การเข้าร่วมกิจกรรม {event_title} ของคุณไม่ได้รับการอนุมัติ กรุณาติดต่อแอดมินสาขา", "danger")
                    
                # Trigger LINE Notification to Student
                student_line_id = users[target_username].get('line_id')
                if student_line_id:
                    if new_status == 'approved':
                        msg = f"🎉 ยินด้วยครับ! ผลงานกิจกรรม '{event_title}' ของคุณได้รับการตรวจสอบและอนุมัติเรียบร้อยแล้ว\n⭐ ได้รับคะแนน: +{event_score} คะแนนสะสม!"
                    elif new_status == 'rejected':
                        msg = f"⚠️ ผลงานหลักฐานกิจกรรม '{event_title}' ของคุณไม่ผ่านการอนุมัติ (Rejected)\nกรุณาเข้าสู่ระบบเพื่อดูรายละเอียดและอัปโหลดภาพหลักฐานใหม่อีกครั้งครับ"
                    send_line_notification(student_line_id, msg)
                    
            conn.commit()
            _cache["participations"]["data"] = None
        except Exception as e:
            conn.rollback()
            print(f"Update participation status error: {e}")
            return jsonify({"success": False, "message": str(e)}), 500
        finally:
            conn.close()
            
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
                        event_id, event_title, event.get('date', ''), final_score,
                        datetime.now().isoformat(), None, new_status
                    ))
                    
                # Email Notification
                student_email = users[target_u].get('email')
                if student_email:
                    if new_status == 'approved':
                        subject = f"🎉 ยินดีด้วย! การเข้าร่วมกิจกรรมได้รับการอนุมัติ: {event_title}"
                        content_html = f"""
                        <p>สวัสดีคุณ <strong>{users[target_u]['name']}</strong>,</p>
                        <p>เรามีความยินดีที่จะแจ้งให้ทราบว่า หลักฐานการเข้าร่วมกิจกรรมของคุณได้รับการตรวจสอบและ<strong>อนุมัติ (Approved)</strong> เรียบร้อยแล้ว!</p>
                        <div style="background: #f0fdf4; padding: 20px; border-radius: 12px; border-left: 4px solid #10b981; margin: 20px 0;">
                            <p style="margin: 0 0 8px 0;"><strong>🏆 กิจกรรม:</strong> {event_title}</p>
                            <p style="margin: 0 0 8px 0;"><strong>📅 วันที่จัดกิจกรรม:</strong> {event.get('date', '')}</p>
                            <p style="margin: 0; font-size: 18px; color: #10b981; font-weight: bold;"><strong>⭐️ คะแนนที่ได้รับ:</strong> +{final_score} คะแนน</p>
                        </div>
                        <p>คะแนนกิจกรรมนี้ได้รับการสะสมเข้าสู่บัญชีของคุณเรียบร้อยแล้ว คุณสามารถเข้าสู่ระบบเพื่อตรวจสอบคะแนนสะสมและดาวน์โหลดเกียรติบัตรอิเล็กทรอนิกส์ได้ทันที</p>
                        """
                        body = get_premium_email_html(
                            title="🎉 อนุมัติการเข้าร่วมกิจกรรมสำเร็จ",
                            content_html=content_html,
                            type_color='#10b981',
                            action_url=request.host_url + 'profile' if request else None,
                            action_text="ตรวจสอบคะแนนและเกียรติบัตร"
                        )
                        send_email_async(student_email, subject, body)
                    elif new_status == 'rejected':
                        subject = f"⚠️ แจ้งเตือน: หลักฐานกิจกรรมไม่ผ่านการอนุมัติ: {event_title}"
                        content_html = f"""
                        <p>สวัสดีคุณ <strong>{users[target_u]['name']}</strong>,</p>
                        <p>ระบบตรวจสอบพบว่าหลักฐานการเข้าร่วมกิจกรรม <strong>{event_title}</strong> ของคุณไม่ผ่านเกณฑ์การอนุมัติ หรือข้อมูลไม่สอดคล้องกับกิจกรรมดังกล่าว</p>
                        <div style="background: #fef2f2; padding: 20px; border-radius: 12px; border-left: 4px solid #ef4444; margin: 20px 0;">
                            <p style="margin: 0 0 8px 0;"><strong>🏆 กิจกรรม:</strong> {event_title}</p>
                            <p style="margin: 0 0 8px 0;"><strong>📅 วันที่จัดกิจกรรม:</strong> {event.get('date', '')}</p>
                            <p style="margin: 0; color: #ef4444; font-weight: bold;"><strong>❌ สถานะ:</strong> ไม่ผ่านการอนุมัติ (Rejected)</p>
                        </div>
                        <p>หากคุณเชื่อว่านี่เป็นข้อผิดพลาด หรือต้องการยื่นส่งหลักฐานใหม่อีกครั้ง กรุณาติดต่อประธานสาขาหรือแอดมินผู้ดูแลระบบของคณะวิชาเพื่อตรวจสอบเพิ่มเติม</p>
                        """
                        body = get_premium_email_html(
                            title="⚠️ กิจกรรมไม่ผ่านการอนุมัติ",
                            content_html=content_html,
                            type_color='#ef4444'
                        )
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
    
    role_filter = request.args.get('role', 'all')
    
    for u_id, u_info in users.items():
        role = u_info.get('role')
        if role_filter != 'all' and role != role_filter:
            continue
            
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

@app.route('/api/admin/reports/attendance', methods=['GET'])
@require_role('admin', 'major')
def get_attendance_report():
    username = session.get('username')
    users = load_users()
    current_user = users.get(username)
    if not current_user:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    role = current_user.get('role')
    
    event_id = request.args.get('event_id')
    major_filter = request.args.get('major')
    
    if not event_id:
        return jsonify({"success": False, "message": "กรุณาระบุรหัสกิจกรรม"}), 400
        
    # Isolation Enforcer: Major can only query their own major
    if role == 'major':
        major_filter = current_user.get('name')
        
    conn = get_db_connection()
    try:
        # Load the target event to verify existence and get standard details
        event_row = conn.execute('SELECT * FROM events WHERE id = ?', (event_id,)).fetchone()
        if not event_row:
            return jsonify({"success": False, "message": "ไม่พบกิจกรรมดังกล่าว"}), 404
        event = dict(event_row)
        
        # Build query for students in that major (or all majors if admin and major_filter == 'all')
        query_students = "SELECT username, name, major FROM users WHERE role = 'student'"
        params_students = []
        
        if major_filter and major_filter != 'all':
            query_students += " AND major = ?"
            params_students.append(major_filter)
            
        # Execute query to get target students list
        student_rows = conn.execute(query_students, params_students).fetchall()
        students = [dict(r) for r in student_rows]
        
        # Load participations and registrations for this event
        participation_rows = conn.execute('SELECT * FROM participations WHERE event_id = ?', (event_id,)).fetchall()
        participations = {p['username']: dict(p) for p in participation_rows}
        
        registration_rows = conn.execute('SELECT * FROM registrations WHERE event_id = ?', (event_id,)).fetchall()
        registrations = {r['username']: dict(r) for r in registration_rows}
        
        result_students = []
        
        stats = {
            "total": len(students),
            "approved": 0,
            "pending": 0,
            "rejected": 0,
            "registered": 0,
            "not_attended": 0
        }
        
        for student in students:
            u_id = student['username']
            p = participations.get(u_id)
            r = registrations.get(u_id)
            
            status = 'not_attended'
            score = 0
            timestamp = None
            image_url = None
            
            # Precedence check
            if p:
                p_status = p.get('status', 'pending')
                score = p.get('score', 0)
                timestamp = p.get('timestamp')
                image_url = p.get('image_url')
                
                if p_status == 'approved':
                    status = 'approved'
                elif p_status == 'pending':
                    status = 'pending'
                elif p_status == 'rejected':
                    status = 'rejected'
            elif r and r.get('status') != 'cancelled':
                status = 'registered'
                timestamp = r.get('timestamp')
                
            # Update stats
            if status == 'approved':
                stats['approved'] += 1
            elif status == 'pending':
                stats['pending'] += 1
            elif status == 'rejected':
                stats['rejected'] += 1
            elif status == 'registered':
                stats['registered'] += 1
            else:
                stats['not_attended'] += 1
                
            result_students.append({
                "username": u_id,
                "name": student['name'],
                "major": student['major'],
                "status": status,
                "score": score,
                "timestamp": timestamp,
                "image_url": image_url
            })
            
        # Sort by Username (student ID) ascending
        result_students.sort(key=lambda s: s['username'])
        
        return jsonify({
            "success": True,
            "event": {
                "id": event['id'],
                "title": event['title'],
                "date": event['date'],
                "score": event.get('score', 0)
            },
            "stats": stats,
            "students": result_students
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        conn.close()

@app.route('/api/admin/reset-password', methods=['POST'])
@require_role('admin', 'major')
def admin_reset_password():
    username = session.get('username')
    data = request.json
    target_username = data.get('username')
    new_password = data.get('new_password', '123456') # Default or custom
    
    with data_lock:
        users = load_users()
        current_user = users.get(username)
        if not current_user:
            return jsonify({"success": False, "message": "Unauthorized"}), 401
            
        role = current_user.get('role')
        
        if target_username not in users:
            return jsonify({"success": False, "message": "ไม่พบผู้ใช้งาน"}), 404
            
        target_data = users[target_username]
        
        if role == 'major':
            my_major_name = current_user.get('name')
            if target_username != username and (target_data.get('role') != 'student' or target_data.get('major') != my_major_name):
                return jsonify({"success": False, "message": "คุณไม่มีสิทธิ์รีเซ็ตรหัสผ่านของผู้ใช้งานนี้"}), 403
                
        users[target_username]['password'] = generate_password_hash(new_password)
        db_save_user(target_username, users[target_username])
        return jsonify({"success": True, "message": f"รีเซ็ตรหัสผ่านเป็น '{new_password}' เรียบร้อยแล้ว"})

@app.route('/api/admin/participations/delete/<part_id>', methods=['POST'])
@require_role('admin')
def delete_participation(part_id):
        
    participations = load_participations()
    part = next((p for p in participations if p['id'] == part_id), None)
    
    if part is None:
        return jsonify({"success": False, "message": "ไม่พบข้อมูลประวัติ"}), 404
        
    db_delete_participation(part_id)
    return jsonify({"success": True, "message": "ลบประวัติเรียบร้อยแล้ว"})

@app.route('/api/admin/delete-user', methods=['POST'])
@require_role('admin', 'major')
def admin_delete_user():
    username = session.get('username')
    
    data = request.json
    target_username = data.get('username')
    
    try:
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
            return jsonify({"success": True, "message": "ลบผู้ใช้งานและประวัติทั้งหมดเรียบร้อยแล้ว"})
    except Exception as e:
        print(f"Delete user error: {e}")
        return jsonify({"success": False, "message": f"ไม่สามารถลบผู้ใช้งานได้เนื่องจากข้อผิดพลาดของระบบ: {str(e)}"}), 500

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
    
    # Safe empty response as notifications are removed
    return jsonify([])

@app.route('/api/notifications/unread-count', methods=['GET'])
def get_unread_notification_count():
    username = session.get('username')
    if not username:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    # Safe zero-count response
    return jsonify({"count": 0})

@app.route('/api/notifications/mark-as-read', methods=['POST'])
def mark_notifications_as_read():
    username = session.get('username')
    if not username:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    # Safe success response without db operation
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

# =============================================================
# SECURE QR CODE & GPS CHECK-IN SYSTEM
# =============================================================
def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371.0  # Earth radius in km
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    a = math.sin(delta_phi / 2.0)**2 + \
        math.cos(phi1) * math.cos(phi2) * \
        math.sin(delta_lambda / 2.0)**2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c * 1000.0  # distance in meters

@app.route('/api/admin/event/<event_id>/checkin-token', methods=['GET'])
@require_role('admin', 'major')
def get_event_checkin_token(event_id):
    username = session.get('username')
    users = load_users()
    user = users.get(username)
    
    conn = get_db_connection()
    event_row = conn.execute('SELECT * FROM events WHERE id = ?', (event_id,)).fetchone()
    conn.close()
    
    if not event_row:
        return jsonify({"success": False, "message": "ไม่พบกิจกรรม"}), 404
        
    event = dict(event_row)
    if user['role'] != 'admin' and event.get('owner') != user['name']:
        return jsonify({"success": False, "message": "คุณไม่มีสิทธิ์สร้าง Token สำหรับกิจกรรมนี้"}), 403
        
    payload = {
        "event_id": event_id,
        "timestamp": time.time()
    }
    payload_str = json.dumps(payload)
    signature = hmac.new(app.secret_key.encode('utf-8'), payload_str.encode('utf-8'), hashlib.sha256).hexdigest()
    
    combined = f"{payload_str}.{signature}"
    token = base64.urlsafe_b64encode(combined.encode('utf-8')).decode('utf-8')
    
    return jsonify({
        "success": True, 
        "token": token, 
        "event_id": event_id,
        "latitude": safe_float(event.get('latitude'), 17.18994),
        "longitude": safe_float(event.get('longitude'), 104.09153)
    })

@app.route('/checkin')
def student_checkin_page():
    username = session.get('username')
    if not username:
        return redirect('/login')
    return send_from_directory('.', 'checkin.html')

@app.route('/api/student/checkin', methods=['POST'])
def process_student_checkin():
    username = session.get('username')
    if not username:
        return jsonify({"success": False, "message": "กรุณาเข้าสู่ระบบ"}), 401
        
    user = db_get_user(username)
    if not user or user.get('role') != 'student':
        return jsonify({"success": False, "message": "เฉพาะนักศึกษาเท่านั้นที่สามารถเช็คอินเข้าร่วมกิจกรรมได้"}), 403
        
    data = request.json
    token = data.get('token')
    student_lat = data.get('latitude')
    student_lng = data.get('longitude')
    
    if not token:
        return jsonify({"success": False, "message": "ไม่พบรหัส Token"}), 400
        
    try:
        decoded_bytes = base64.urlsafe_b64decode(token.encode('utf-8'))
        decoded_str = decoded_bytes.decode('utf-8')
        
        parts = decoded_str.rsplit('.', 1)
        if len(parts) != 2:
            return jsonify({"success": False, "message": "โครงสร้าง Token ไม่ถูกต้อง"}), 400
            
        payload_str, signature = parts
        
        expected_sig = hmac.new(app.secret_key.encode('utf-8'), payload_str.encode('utf-8'), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected_sig, signature):
            return jsonify({"success": False, "message": "Token เช็คอินไม่ถูกต้องหรือถูกลักลอบแก้ไข"}), 400
            
        payload = json.loads(payload_str)
        event_id = payload.get('event_id')
        token_time = payload.get('timestamp', 0)
        
        if time.time() - token_time > 60:
            return jsonify({"success": False, "message": "คิวอาร์โค้ดนี้หมดอายุแล้ว (จำกัดเวลา 60 วินาที) กรุณาสแกนรหัสล่าสุดจากหน้าจอแอดมิน"}), 400
            
    except Exception as e:
        return jsonify({"success": False, "message": f"เกิดข้อผิดพลาดในการตรวจสอบ Token: {str(e)}"}), 400
        
    conn = get_db_connection()
    event_row = conn.execute('SELECT * FROM events WHERE id = ?', (event_id,)).fetchone()
    conn.close()
    
    if not event_row:
        return jsonify({"success": False, "message": "ไม่พบข้อมูลกิจกรรมนี้ในระบบ"}), 404
        
    event = dict(event_row)
    event_lat = safe_float(event.get('latitude'), 17.18994)
    event_lng = safe_float(event.get('longitude'), 104.09153)
    
    if event_lat != 0.0 and event_lng != 0.0:
        if student_lat is None or student_lng is None:
            return jsonify({"success": False, "message": "ระบบต้องการพิกัด GPS เพื่อยืนยันว่าคุณเข้าร่วมกิจกรรมจริง กรุณาอนุญาตสิทธิ์เข้าถึงพิกัดบนอุปกรณ์ของคุณ"}), 400
            
        try:
            dist = haversine_distance(float(student_lat), float(student_lng), float(event_lat), float(event_lng))
            if dist > 500.0:
                return jsonify({"success": False, "message": f"คุณไม่ได้อยู่ในสถานที่จัดกิจกรรม (พิกัดปัจจุบันของคุณห่างจากจุดจัดกิจกรรม {dist:.1f} เมตร เกินกำหนด 500 เมตร)"}), 400
        except Exception as e:
            return jsonify({"success": False, "message": f"เกิดข้อผิดพลาดในการตรวจสอบพิกัด: {str(e)}"}), 400
            
    user_parts = db_get_user_participations(username)
    for p in user_parts:
        if p.get('event_id') == event_id:
            return jsonify({"success": False, "message": "คุณทำการเช็คอินหรือส่งผลงานสำหรับกิจกรรมนี้เรียบร้อยแล้ว"}), 400
            
    record = {
        "id": "part_" + uuid.uuid4().hex[:10],
        "username": username,
        "student_name": user['name'],
        "major": user.get('major'),
        "event_id": event_id,
        "event_title": event.get('title'),
        "event_date": event.get('date'),
        "score": int(event.get('score', 0)),
        "timestamp": datetime.now().isoformat(),
        "image_url": "/static/images/qr_checkin.png",
        "status": "approved"
    }
    db_save_participation(record)
    
    student_email = user.get('email')
    if student_email:
        subject = f"✅ เช็คอินสำเร็จ: {event.get('title')}"
        body = f"""
        <div style="font-family:Kanit,sans-serif;max-width:500px;margin:auto;padding:24px;background:#f8fafc;border-radius:12px;">
            <h2 style="color:#10b981;">✅ เช็คอินและสะสมคะแนนสำเร็จ!</h2>
            <p>สวัสดีคุณ <strong>{user['name']}</strong></p>
            <div style="background:white;padding:16px;border-radius:8px;border-left:4px solid #10b981;margin:16px 0;">
                <p><strong>📅 กิจกรรม:</strong> {event.get('title')}</p>
                <p><strong>🗓️ วันที่:</strong> {event.get('date')}</p>
                <p><strong>📍 สถานที่:</strong> {event.get('location', 'ยังไม่ระบุ')}</p>
                <p><strong>⭐️ คะแนนที่ได้รับ:</strong> {event.get('score', 0)} คะแนน</p>
            </div>
            <p style="color:#64748b;font-size:13px;">ระบบปฏิทินกิจกรรม คณะวิทยาศาสตร์และเทคโนโลยี มหาวิทยาลัยราชภัฏสกลนคร</p>
        </div>"""
        send_email_async(student_email, subject, body)
        
    return jsonify({
        "success": True, 
        "message": "เช็คอินและสะสมแต้มชั่วโมงกิจกรรมสำเร็จแล้ว!",
        "event": {
            "title": event.get('title'),
            "score": event.get('score'),
            "date": event.get('date')
        }
    })

# =============================================================

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
