import urllib.request
import urllib.parse
import json
import threading
import time
import os
import sqlite3
from werkzeug.security import generate_password_hash
from datetime import datetime

BASE_URL = "http://127.0.0.1:5000"

def init_test_db():
    print("--- [SETUP] Preparing test data ---")
    conn = sqlite3.connect('database.sqlite')
    c = conn.cursor()
    
    # 1. Clean up old test data if exists
    test_usernames = [f"690000000{i}" for i in range(1, 10)] + ["6900000010"]
    test_usernames.append("admin_test")
    
    for username in test_usernames:
        c.execute('DELETE FROM participations WHERE username=?', (username,))
        c.execute('DELETE FROM registrations WHERE username=?', (username,))
        c.execute('DELETE FROM users WHERE username=?', (username,))
        
    c.execute("DELETE FROM events WHERE id='test-concurrency-event'")
    
    # 2. Insert test admin
    hashed_password = generate_password_hash("admin123")
    c.execute('''
        INSERT INTO users (username, password, name, email, major, role)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', ("admin_test", hashed_password, "ผู้ดูแลระบบทดสอบ", "admin_test@snru.ac.th", "วิทยาการคอมพิวเตอร์", "admin"))
    
    # 3. Insert test event with max_participants = 5
    c.execute('''
        INSERT INTO events (id, title, date, category, location, owner, description, registration_open, max_participants, score, status, created_at, registration_start, registration_end, latitude, longitude)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        "test-concurrency-event",
        "กิจกรรมทดสอบ Concurrency",
        "25 พ.ค. 69",
        "กิจกรรมระดับมหาวิทยาลัย",
        "หอประชุมใหญ่",
        "วิทยาการคอมพิวเตอร์",
        "คำอธิบายกิจกรรมทดสอบการเข้าจองพร้อมกัน",
        1,  # registration_open
        5,  # max_participants
        10, # score
        "อนุมัติแล้ว", # status
        datetime.now().strftime('%Y-%m-%dT%H:%M'),
        "2026-01-01T00:00", # registration_start
        "2026-12-31T23:59", # registration_end
        17.18994,
        104.09153
    ))
    
    conn.commit()
    conn.close()
    print("--- [SETUP] Test data prepared successfully ---")

def clean_test_db():
    print("\n--- [CLEANUP] Cleaning up test data ---")
    conn = sqlite3.connect('database.sqlite')
    c = conn.cursor()
    
    test_usernames = [f"690000000{i}" for i in range(1, 10)] + ["6900000010"]
    test_usernames.append("admin_test")
    
    for username in test_usernames:
        c.execute('DELETE FROM participations WHERE username=?', (username,))
        c.execute('DELETE FROM registrations WHERE username=?', (username,))
        c.execute('DELETE FROM users WHERE username=?', (username,))
        
    c.execute("DELETE FROM events WHERE id='test-concurrency-event'")
    
    conn.commit()
    conn.close()
    print("--- [CLEANUP] Test data cleaned successfully ---")

def make_request(path, data=None, method='GET', cookie=None):
    url = f"{BASE_URL}{path}"
    headers = {'Content-Type': 'application/json'}
    if cookie:
        headers['Cookie'] = cookie
    
    req_data = json.dumps(data).encode('utf-8') if data else None
    req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
    
    try:
        with urllib.request.urlopen(req) as response:
            res_data = response.read().decode('utf-8')
            cookie_header = response.getheader('Set-Cookie')
            return json.loads(res_data), cookie_header
    except Exception as e:
        if hasattr(e, 'read'):
            try:
                error_body = e.read().decode('utf-8')
                return json.loads(error_body), None
            except:
                pass
        return {"success": False, "message": str(e)}, None

def student_flow(student_id, name, results_dict):
    """Simulates a student registering, logging in, and booking the event concurrently."""
    username = f"690000000{student_id}" if student_id < 10 else f"69000000{student_id}"
    email = f"{username}@snru.ac.th"
    password = "student123"
    
    # 1. Register API
    reg_data = {
        "username": username,
        "password": password,
        "name": name,
        "major": "วิทยาการคอมพิวเตอร์",
        "email": email
    }
    reg_res, _ = make_request("/api/register", reg_data, "POST")
    if not reg_res.get("success"):
        results_dict[username] = {"phase": "register", "success": False, "message": reg_res.get("message")}
        print(f"[FAIL] Register failed for {username}: {reg_res.get('message')}")
        return
        
    # 2. Login API
    login_res, cookie = make_request("/api/login", {"username": username, "password": password}, "POST")
    if not cookie:
        results_dict[username] = {"phase": "login", "success": False, "message": login_res.get("message")}
        print(f"[FAIL] Login failed for {username}: {login_res.get('message')}")
        return
        
    # 3. Book Event API
    book_res, _ = make_request(f"/api/events/test-concurrency-event/register", None, "POST", cookie)
    
    results_dict[username] = {
        "phase": "book",
        "success": book_res.get("success", False),
        "message": book_res.get("message"),
        "status": book_res.get("status") or ("waitlist" if "เต็ม" in book_res.get("message", "") else "unknown")
    }
    print(f"[OK] Book result for {username}: success={book_res.get('success')}, message={book_res.get('message')}")

def test_concurrency():
    # 1. Initialize SQLite values
    init_test_db()
    
    # 2. Start Flask Server in background daemon thread
    print("--- [SERVER] Starting server in background ---")
    from app import app
    def start_flask():
        app.run(port=5000, debug=False, use_reloader=False)
        
    server_thread = threading.Thread(target=start_flask, daemon=True)
    server_thread.start()
    time.sleep(2) # Allow server to boot
    
    # 3. Simulate 10 students concurrently booking an event with max capacity of 5
    student_names = [
        "สมชาย หนึ่ง", "สมชาย สอง", "สมชาย สาม", "สมชาย สี่", "สมชาย ห้า",
        "สมชาย หก", "สมชาย เจ็ด", "สมชาย แปด", "สมชาย เก้า", "สมชาย สิบ"
    ]
    
    results = {}
    threads = []
    
    print("\n--- [START] Simulating concurrent registrations and bookings (Stress / Concurrency) ---")
    start_time = time.time()
    
    for i in range(1, 11):
        name = student_names[i-1]
        t = threading.Thread(target=student_flow, args=(i, name, results))
        threads.append(t)
        t.start()
        
    for t in threads:
        t.join()
        
    duration = time.time() - start_time
    print(f"--- [END] Processed 10 concurrent student sessions in {duration:.3f} seconds ---")
    
    # 4. Verification & Validation
    print("\n--- [VERIFY] Checking database registrations & locks ---")
    
    conn = sqlite3.connect('database.sqlite')
    conn.row_factory = sqlite3.Row
    registrations = conn.execute("SELECT * FROM registrations WHERE event_id='test-concurrency-event'").fetchall()
    conn.close()
    
    confirmed_regs = [r for r in registrations if r['status'] == 'confirmed']
    waitlist_regs = [r for r in registrations if r['status'] == 'waitlist']
    
    print(f"Total registrations in DB: {len(registrations)}")
    print(f"   - Confirmed: {len(confirmed_regs)} (Target: 5)")
    print(f"   - Waitlist: {len(waitlist_regs)} (Target: 5)")
    
    success = True
    if len(registrations) != 10:
        print("[FAIL] Error: Total registration count in DB is not 10!")
        success = False
    if len(confirmed_regs) != 5:
        print(f"[FAIL] Error: Confirmed bookings count is {len(confirmed_regs)}, expected 5!")
        success = False
    if len(waitlist_regs) != 5:
        print(f"[FAIL] Error: Waitlist bookings count is {len(waitlist_regs)}, expected 5!")
        success = False
        
    if success:
        print("[SUCCESS] WAL Lock Concurrency & Capacity Enforcer verified successfully!")
    else:
        print("[FAIL] Verification failed. Check Transaction Locks or Database Integrity.")
        
    # 5. Clean up DB
    clean_test_db()

if __name__ == "__main__":
    test_concurrency()
