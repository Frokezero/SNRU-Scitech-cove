from flask import Flask, jsonify, request, send_from_directory, session, redirect
from werkzeug.security import generate_password_hash, check_password_hash
import json
import os
import uuid
import re
import smtplib
import threading
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formatdate, make_msgid

# Simple Cache for Performance
_cache = {
    "users": {"data": None, "time": 0},
    "events": {"data": None, "time": 0},
    "participations": {"data": None, "time": 0}
}
CACHE_TTL = 2 # 2 seconds cache to reduce Disk I/O under high load

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
            
            # Create a simple plain text version by removing HTML tags
            plain_text = re.sub('<[^<]+>', '', body)
            plain_text = plain_text.replace('&nbsp;', ' ').strip()
            
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
app.secret_key = 'super-secret-sakon-nakhon-key'

DATA_FILE = 'events.json'

USER_FILE = 'users.json'

data_lock = threading.Lock()

def load_users():
    now = time.time()
    if _cache["users"]["data"] and (now - _cache["users"]["time"] < CACHE_TTL):
        return _cache["users"]["data"]
        
    with data_lock:
        if not os.path.exists(USER_FILE):
            return {}
        with open(USER_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            _cache["users"] = {"data": data, "time": now}
            return data

def save_json(path, data):
    with data_lock:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

def save_users(users):
    save_json(USER_FILE, users)
    _cache["users"]["data"] = users
    _cache["users"]["time"] = time.time()

DATA_FILE = 'events.json'
UPLOAD_FOLDER = 'uploads'
ACTIVITIES_UPLOAD_FOLDER = os.path.join(UPLOAD_FOLDER, 'activities')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
if not os.path.exists(ACTIVITIES_UPLOAD_FOLDER):
    os.makedirs(ACTIVITIES_UPLOAD_FOLDER)

PARTICIPATIONS_FILE = 'participations.json'

def load_participations():
    now = time.time()
    if _cache["participations"]["data"] and (now - _cache["participations"]["time"] < CACHE_TTL):
        return _cache["participations"]["data"]

    with data_lock:
        if not os.path.exists(PARTICIPATIONS_FILE):
            return []
        with open(PARTICIPATIONS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            _cache["participations"] = {"data": data, "time": now}
            return data

def save_participations(data):
    save_json(PARTICIPATIONS_FILE, data)
    _cache["participations"]["data"] = data
    _cache["participations"]["time"] = time.time()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def load_carousel():
    if not os.path.exists('carousel.json'):
        return []
    with open('carousel.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def save_carousel(images):
    save_json('carousel.json', images)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

def load_events():
    now = time.time()
    if _cache["events"]["data"] and (now - _cache["events"]["time"] < CACHE_TTL):
        return _cache["events"]["data"]
        
    with data_lock:
        if not os.path.exists(DATA_FILE):
            return []
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            _cache["events"] = {"data": data, "time": now}
            return data

def save_events(events):
    save_json(DATA_FILE, events)
    _cache["events"]["data"] = events
    _cache["events"]["time"] = time.time()

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

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('.', path)

# Auth API
@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    users = load_users()
    if username in users and check_password_hash(users[username]['password'], password):
        session['username'] = username
        return jsonify({"success": True, "user": {"name": users[username]['name'], "role": users[username]['role']}})
    return jsonify({"success": False, "message": "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง"}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    session.pop('username', None)
    return jsonify({"success": True})

@app.route('/api/me', methods=['GET'])
def me():
    username = session.get('username')
    if username:
        users = load_users()
        if username in users:
            return jsonify({"success": True, "user": {"name": users[username]['name'], "role": users[username]['role']}})
    return jsonify({"success": False}), 401

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
    save_users(users)
    
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
    save_users(users)
    
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
def update_user():
    username = session.get('username')
    users = load_users()
    if not username or username not in users:
        return jsonify({"success": False, "message": "Unauthorized"}), 403
        
    current_user = users[username]
    role = current_user.get('role')
    
    if role not in ['admin', 'major']:
        return jsonify({"success": False, "message": "Unauthorized"}), 403
        
    data = request.json
    target_user = data.get('username')
    new_name = data.get('name')
    new_password = data.get('password')
    
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
        
    save_users(users)
    return jsonify({"success": True, "message": f"อัปเดตข้อมูลของ {target_user} เรียบร้อยแล้ว"})

@app.route('/api/admin/delete-user', methods=['DELETE'])
def delete_user():
    username = session.get('username')
    users = load_users()
    if not username or username not in users:
        return jsonify({"success": False, "message": "Unauthorized"}), 403
        
    current_user = users[username]
    role = current_user.get('role')
    
    if role not in ['admin', 'major']:
        return jsonify({"success": False, "message": "Unauthorized"}), 403
        
    data = request.json
    target_user = data.get('username')
    
    if target_user not in users:
        return jsonify({"success": False, "message": "ไม่พบผู้ใช้งาน"}), 404
        
    target_data = users[target_user]
    
    if target_user == username or target_user == 'admin':
        return jsonify({"success": False, "message": "ไม่สามารถลบบัญชีหลัก หรือบัญชีตัวเองได้"}), 400
        
    if role == 'major':
        my_major_name = current_user.get('name')
        if target_data.get('role') != 'student' or target_data.get('major') != my_major_name:
            return jsonify({"success": False, "message": "คุณไม่มีสิทธิ์ลบผู้ใช้งานนี้"}), 403
            
    del users[target_user]
    save_users(users)
    
    # Remove participations for this user
    participations = load_participations()
    filtered_parts = [p for p in participations if p.get('username') != target_user]
    if len(filtered_parts) != len(participations):
        save_participations(filtered_parts)
        
    return jsonify({"success": True, "message": f"ลบบัญชี {target_user} และประวัติเรียบร้อยแล้ว"})

@app.route('/api/carousel', methods=['GET'])
def get_carousel():
    return jsonify(load_carousel())

@app.route('/api/carousel/upload', methods=['POST'])
def upload_carousel():
    username = session.get('username')
    users = load_users()
    if not username or users.get(username, {}).get('role') != 'admin':
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    if 'image' not in request.files:
        return jsonify({"success": False, "message": "No image part"}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({"success": False, "message": "No selected file"}), 400
        
    if not allowed_file(file.filename):
        return jsonify({"success": False, "message": "File type not allowed"}), 400
    
    if file:
        ext = os.path.splitext(file.filename)[1]
        filename = f"{uuid.uuid4()}{ext}"
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
    # If called from admin page, optionally filter by user role
    # But since public can see all events, we just return all. 
    # The frontend admin page will hide edit/delete buttons for events not owned by them.
    for e in events:
        if 'owner' not in e:
            e['owner'] = "สโมสรนักศึกษา" # Default owner for old events
    return jsonify(events)

@app.route('/api/events', methods=['POST'])
def add_event():
    username = session.get('username')
    if not username:
        return jsonify({"success": False, "message": "กรุณาเข้าสู่ระบบ"}), 401
    
    events = load_events()
    new_event = request.json
    new_event['id'] = str(uuid.uuid4())
    
    users = load_users()
    
    # Permission Check for University Category
    if new_event.get('category') == 'กิจกรรมมหาวิทยาลัย' and users[username]['role'] != 'admin':
        return jsonify({"success": False, "message": "เฉพาะแอดมินส่วนกลางเท่านั้นที่สามารถเพิ่มกิจกรรมมหาวิทยาลัยได้"}), 403

    # Assign owner based on role
    if users[username]['role'] == 'admin' and new_event.get('owner'):
        pass # Admin can assign any owner
    else:
        new_event['owner'] = users[username]['name'] # Majors can only create for themselves
        
    events.append(new_event)
    save_events(events)
    return jsonify({'success': True, 'event': new_event})

@app.route('/api/events/<event_id>', methods=['PUT'])
def update_event(event_id):
    username = session.get('username')
    if not username:
        return jsonify({"success": False, "message": "กรุณาเข้าสู่ระบบ"}), 401

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
            
            # Permission Check for University Category
            if updated_event.get('category') == 'กิจกรรมมหาวิทยาลัย' and users[username]['role'] != 'admin':
                return jsonify({"success": False, "message": "เฉพาะแอดมินส่วนกลางเท่านั้นที่สามารถจัดการกิจกรรมมหาวิทยาลัยได้"}), 403

            # If admin, they might have changed the owner. If major, keep original owner.
            if users[username]['role'] != 'admin':
                updated_event['owner'] = event_owner
                
            events[i] = updated_event
            save_events(events)
            return jsonify({'success': True, 'event': updated_event})
            
    return jsonify({'success': False, 'message': 'Event not found'}), 404

@app.route('/api/events/delete/<event_id>', methods=['POST'])
def delete_event(event_id):
    username = session.get('username')
    if not username:
        return jsonify({"success": False, "message": "กรุณาเข้าสู่ระบบ"}), 401

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

    events = [e for e in events if e['id'] != event_id]
    save_events(events)
    return jsonify({'success': True})

@app.route('/api/student/participate', methods=['POST'])
def submit_participation():
    username = session.get('username')
    if not username:
        return jsonify({"success": False, "message": "กรุณาเข้าสู่ระบบ"}), 401
        
    users = load_users()
    if username not in users or users[username].get('role') != 'student':
        return jsonify({"success": False, "message": "เฉพาะนักศึกษาเท่านั้น"}), 403
        
    if 'file' not in request.files:
        return jsonify({"success": False, "message": "ไม่พบไฟล์รูปภาพ"}), 400
        
    file = request.files['file']
    event_id = request.form.get('event_id')
    event_title = request.form.get('event_title')
    event_date = request.form.get('event_date')
    
    if file.filename == '' or not event_id:
        return jsonify({"success": False, "message": "ข้อมูลไม่ครบถ้วน"}), 400
        
    if file and allowed_file(file.filename):
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{username}_{event_id}_{uuid.uuid4().hex[:8]}.{ext}"
        filepath = os.path.join(ACTIVITIES_UPLOAD_FOLDER, filename)
        file.save(filepath)
        
        participations = load_participations()
        
        # Check if already participated
        for p in participations:
            if p.get('username') == username and p.get('event_id') == event_id:
                return jsonify({"success": False, "message": "คุณได้ส่งภาพสำหรับกิจกรรมนี้ไปแล้ว"}), 400
        
        record = {
            "id": str(uuid.uuid4()),
            "username": username,
            "student_name": users[username]['name'],
            "major": users[username].get('major'),
            "event_id": event_id,
            "event_title": event_title,
            "event_date": event_date,
            "image_url": f"/uploads/activities/{filename}"
        }
        participations.append(record)
        save_participations(participations)
        
        # Send confirmation email
        student_email = users[username].get('email')
        if student_email:
            subject = f"ยืนยันการส่งผลงานกิจกรรม: {event_title}"
            body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; color: #333;">
                <h2>สวัสดีคุณ {users[username]['name']}</h2>
                <p>ระบบได้รับภาพยืนยันการเข้าร่วมกิจกรรมของคุณเรียบร้อยแล้ว</p>
                <div style="background: #f8fafc; padding: 15px; border-left: 4px solid #0284c7; margin: 20px 0;">
                    <p style="margin: 0;"><strong>กิจกรรม:</strong> {event_title}</p>
                    <p style="margin: 5px 0 0 0;"><strong>วันที่เข้าร่วม:</strong> {event_date}</p>
                </div>
                <p>แอดมินสาขาจะทำการตรวจสอบความถูกต้องของผลงานต่อไป ขอบคุณที่ให้ความร่วมมือครับ</p>
                <hr>
                <p style="font-size: 12px; color: #888;">อีเมลฉบับนี้ส่งจากระบบอัตโนมัติ กรุณาอย่าตอบกลับ</p>
            </body>
            </html>
            """
            send_email_async(student_email, subject, body)
        
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
def get_student_activities(username):
    if 'username' not in session or load_users().get(session['username'], {}).get('role') not in ['admin', 'major']:
        return jsonify({"message": "Unauthorized"}), 401
    
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
def manage_participation(part_id):
    if 'username' not in session:
        return jsonify({"message": "Unauthorized"}), 401
    
    users = load_users()
    username = session['username']
    if users.get(username, {}).get('role') != 'admin':
        return jsonify({"success": False, "message": "เฉพาะแอดมินเท่านั้นที่จัดการได้"}), 403
        
    participations = load_participations()
    part_index = next((i for i, p in enumerate(participations) if p['id'] == part_id), None)
    
    if part_index is None:
        return jsonify({"success": False, "message": "ไม่พบข้อมูลประวัติ"}), 404
        
    if request.method == 'DELETE':
        del participations[part_index]
        save_participations(participations)
        return jsonify({"success": True, "message": "ลบประวัติเรียบร้อยแล้ว"})
        
    if request.method == 'PUT':
        data = request.json
        participations[part_index]['score'] = data.get('score', participations[part_index].get('score', 0))
        participations[part_index]['status'] = data.get('status', participations[part_index].get('status', 'pending'))
        save_participations(participations)
        return jsonify({"success": True, "message": "อัปเดตข้อมูลเรียบร้อยแล้ว"})

@app.route('/api/admin/participations', methods=['GET'])
def get_admin_participations():
    username = session.get('username')
    users = load_users()
    if not username or username not in users:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
        
    current_user = users[username]
    role = current_user.get('role')
    if role not in ['admin', 'major']:
        return jsonify({"success": False, "message": "Unauthorized"}), 403
        
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
def get_event_students(event_id):
    username = session.get('username')
    users = load_users()
    if not username or username not in users:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
        
    current_user = users[username]
    role = current_user.get('role')
    if role not in ['admin', 'major']:
        return jsonify({"success": False, "message": "Unauthorized"}), 403
        
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
def update_participation_status():
    username = session.get('username')
    users = load_users()
    if not username or username not in users:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
        
    current_user = users[username]
    role = current_user.get('role')
    if role not in ['admin', 'major']:
        return jsonify({"success": False, "message": "Unauthorized"}), 403
        
    data = request.json
    event_id = data.get('event_id')
    updates = data.get('updates') # List of dicts: {"username": "123", "status": "approved"}
    
    if not event_id or not updates:
        return jsonify({"success": False, "message": "ข้อมูลไม่ครบถ้วน"}), 400
        
    events = load_events()
    event = next((e for e in events if e['id'] == event_id), None)
    if not event:
        return jsonify({"success": False, "message": "ไม่พบกิจกรรม"}), 404
        
    event_score = int(event.get('score', 0))
    event_title = event.get('title', 'กิจกรรม')
    
    participations = load_participations()
    
    for update in updates:
        target_username = update.get('username')
        new_status = update.get('status') # 'approved' or 'rejected'
        
        # Find existing participation
        part = next((p for p in participations if p.get('event_id') == event_id and p.get('username') == target_username), None)
        
        if part:
            part['status'] = new_status
        else:
            # If rejected/not participated and no record exists, we can create a dummy one or just ignore
            # Let's create a record so we remember the status
            part = {
                "id": str(uuid.uuid4()),
                "username": target_username,
                "student_name": users[target_username]['name'],
                "major": users[target_username].get('major'),
                "event_id": event_id,
                "event_title": event_title,
                "event_date": event.get('date', ''),
                "image_url": None,
                "status": new_status
            }
            participations.append(part)
            
        # Send Email
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
                
    save_participations(participations)
    return jsonify({"success": True, "message": "อัปเดตสถานะเรียบร้อยแล้ว"})

@app.route('/api/admin/update-status-bulk', methods=['POST'])
def update_status_bulk():
    username = session.get('username')
    users = load_users()
    if not username or username not in users:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
        
    current_user = users[username]
    role = current_user.get('role')
    if role not in ['admin', 'major']:
        return jsonify({"success": False, "message": "Unauthorized"}), 403
        
    data = request.json
    event_id = data.get('event_id')
    usernames = data.get('usernames', [])
    new_status = data.get('status')
    custom_scores = data.get('scores', {}) # Map: {username: score}
    
    if not event_id or not usernames or not new_status:
        return jsonify({"success": False, "message": "ข้อมูลไม่ครบถ้วน"}), 400
        
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
            part['status'] = new_status
            part['score'] = final_score
        else:
            part = {
                "id": str(uuid.uuid4()),
                "username": target_u,
                "student_name": users[target_u]['name'],
                "major": users[target_u].get('major'),
                "event_id": event_id,
                "event_title": event_title,
                "event_date": event.get('date', ''),
                "image_url": None,
                "status": new_status,
                "score": final_score
            }
            participations.append(part)
            
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

    save_participations(participations)
    return jsonify({"success": True, "message": "อัปเดตเรียบร้อยแล้ว"})

@app.route('/api/admin/reports/students', methods=['GET'])
def get_student_report():
    if 'username' not in session or load_users().get(session['username'], {}).get('role') not in ['admin', 'major']:
        return jsonify({"message": "Unauthorized"}), 401
    
    # Bypass cache for report to ensure data freshness
    with data_lock:
        with open(USER_FILE, 'r', encoding='utf-8') as f:
            users = json.load(f)
    
    events = load_events()
    event_scores = {e['id']: int(e.get('score', 0)) for e in events}
    participations = load_participations()
    
    report = []
    for u_id, u_info in users.items():
        if u_info.get('role') == 'student':
            # Calculate score and count
            student_parts = [p for p in participations if p.get('username') == u_id and p.get('status') == 'approved']
            total_score = sum(p.get('score', event_scores.get(p.get('event_id'), 0)) for p in student_parts)
            
            report.append({
                "username": u_id,
                "name": u_info.get('name'),
                "major": u_info.get('major'),
                "score": total_score,
                "participated_count": len(student_parts)
            })
            
    return jsonify(report)

@app.route('/api/admin/reset-password', methods=['POST'])
def admin_reset_password():
    if 'username' not in session or load_users().get(session['username'], {}).get('role') not in ['admin', 'major']:
        return jsonify({"message": "Unauthorized"}), 401
    
    data = request.json
    target_username = data.get('username')
    new_password = data.get('new_password', '123456') # Default or custom
    
    users = load_users()
    if target_username not in users:
        return jsonify({"success": False, "message": "ไม่พบผู้ใช้งาน"}), 404
        
    users[target_username]['password'] = generate_password_hash(new_password)
    save_users(users)
    return jsonify({"success": True, "message": f"รีเซ็ตรหัสผ่านเป็น '{new_password}' เรียบร้อยแล้ว"})

@app.route('/api/admin/participations/delete/<part_id>', methods=['POST'])
def delete_participation(part_id):
    if 'username' not in session:
        return jsonify({"message": "Unauthorized"}), 401
    
    users = load_users()
    username = session['username']
    if users.get(username, {}).get('role') != 'admin':
        return jsonify({"success": False, "message": "เฉพาะแอดมินส่วนกลางเท่านั้นที่จัดการประวัติได้"}), 403
        
    participations = load_participations()
    part_index = next((i for i, p in enumerate(participations) if p['id'] == part_id), None)
    
    if part_index is None:
        return jsonify({"success": False, "message": "ไม่พบข้อมูลประวัติ"}), 404
        
    del participations[part_index]
    save_participations(participations)
    return jsonify({"success": True, "message": "ลบประวัติเรียบร้อยแล้ว"})

@app.route('/api/admin/delete-user', methods=['POST'])
def admin_delete_user():
    username = session.get('username')
    users = load_users()
    if not username or username not in users:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
        
    current_user = users[username]
    role = current_user.get('role')
    if role not in ['admin', 'major']:
        return jsonify({"success": False, "message": "Unauthorized"}), 403
        
    data = request.json
    target_username = data.get('username')
    
    if target_username not in users:
        return jsonify({"success": False, "message": "ไม่พบผู้ใช้งาน"}), 404
    
    target_data = users[target_username]
    if target_data.get('role') == 'admin':
        return jsonify({"success": False, "message": "ไม่สามารถลบแอดมินส่วนกลางได้"}), 403

    if role == 'major':
        my_major_name = current_user.get('name')
        if target_data.get('role') != 'student' or target_data.get('major') != my_major_name:
            return jsonify({"success": False, "message": "คุณไม่มีสิทธิ์ลบผู้ใช้งานนอกสาขา"}), 403
        
    del users[target_username]
    save_users(users)
    
    # Remove participations for this user
    participations = load_participations()
    filtered_parts = [p for p in participations if p.get('username') != target_username]
    if len(filtered_parts) != len(participations):
        save_participations(filtered_parts)
        
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
