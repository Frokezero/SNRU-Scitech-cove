from flask import Flask, jsonify, request, send_from_directory, session
import json
import os
import uuid

app = Flask(__name__)
app.secret_key = 'super-secret-sakon-nakhon-key'

DATA_FILE = 'events.json'

USER_FILE = 'users.json'

def load_users():
    if not os.path.exists(USER_FILE):
        return {}
    with open(USER_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_users(users):
    with open(USER_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=4)

DATA_FILE = 'events.json'
UPLOAD_FOLDER = 'uploads'

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def load_carousel():
    if not os.path.exists('carousel.json'):
        return []
    with open('carousel.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def save_carousel(images):
    with open('carousel.json', 'w', encoding='utf-8') as f:
        json.dump(images, f, ensure_ascii=False, indent=4)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

def load_events():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_events(events):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(events, f, ensure_ascii=False, indent=2)

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/admin')
def admin():
    return send_from_directory('.', 'admin.html')

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
    if username in users and users[username]['password'] == password:
        session['username'] = username
        return jsonify({"success": True, "user": users[username]})
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
            return jsonify({"success": True, "user": users[username]})
    return jsonify({"success": False}), 401

@app.route('/api/admin/users', methods=['GET'])
def get_users():
    username = session.get('username')
    users = load_users()
    if not username or users.get(username, {}).get('role') != 'admin':
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    # Return user list without passwords (or with, since admin manages them)
    return jsonify(users)

@app.route('/api/admin/change-password', methods=['POST'])
def change_password():
    username = session.get('username')
    users = load_users()
    if not username or users.get(username, {}).get('role') != 'admin':
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    data = request.json
    target_user = data.get('username')
    new_password = data.get('password')
    
    if target_user in users:
        users[target_user]['password'] = new_password
        save_users(users)
        return jsonify({"success": True, "message": f"เปลี่ยนรหัสผ่านของ {target_user} เรียบร้อยแล้ว"})
    
    return jsonify({"success": False, "message": "ไม่พบผู้ใช้งาน"}), 404

@app.route('/api/carousel', methods=['GET'])
def get_carousel():
    return jsonify(load_carousel())

@app.route('/api/admin/upload-carousel', methods=['POST'])
def upload_carousel():
    username = session.get('username')
    users = load_users()
    if not username or users.get(username, {}).get('role') != 'admin':
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    if 'file' not in request.files:
        return jsonify({"success": False, "message": "No file part"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "message": "No selected file"}), 400
    
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
            
            # If admin, they might have changed the owner. If major, keep original owner.
            if users[username]['role'] != 'admin':
                updated_event['owner'] = event_owner
                
            events[i] = updated_event
            save_events(events)
            return jsonify({'success': True, 'event': updated_event})
            
    return jsonify({'success': False, 'message': 'Event not found'}), 404

@app.route('/api/events/<event_id>', methods=['DELETE'])
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

if __name__ == '__main__':
    print("========================================")
    print("   Starting Activity Calendar Server (with Auth)")
    print("   User View: http://127.0.0.1:5000/")
    print("   Admin Panel: http://127.0.0.1:5000/admin")
    print("========================================")
    app.run(debug=True, port=5000)
