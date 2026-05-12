import urllib.request
import urllib.parse
import json
import threading
import uuid
import time
from datetime import datetime
import re

BASE_URL = "http://127.0.0.1:5000"

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
        return {"success": False, "message": str(e)}, None

def register_user(username, password, name, major):
    data = {
        "username": username,
        "password": password,
        "name": name,
        "major": major,
        "email": f"{username}@test.com"
    }
    res, _ = make_request("/api/register", data, 'POST') # Fixed path to /api/register
    return res

def login_user(username, password):
    res, cookie = make_request("/api/auth/login", {"username": username, "password": password}, 'POST')
    return cookie, res

def register_for_event(cookie, event_id):
    res, _ = make_request(f"/api/events/{event_id}/register", None, 'POST', cookie)
    return res

def test_concurrency():
    print("Setting up test users...")
    cookies = []
    for i in range(5):
        uname = f"testuser_{uuid.uuid4().hex[:6]}"
        reg_res = register_user(uname, "password123", f"Test User {i}", "Computer Science")
        if not reg_res.get('success'):
            print(f"Failed to register {uname}: {reg_res.get('message')}")
            continue
        cookie, login_res = login_user(uname, "password123")
        if cookie:
            cookies.append(cookie)
    
    # event_id = "test-event-concurrency"
    # For now, just test the date parsing logic since server might not be running
    pass

def parse_thai_date_to_comparable(date_str):
    if not date_str or not isinstance(date_str, str):
        return None
    months_map = {
        'ม.ค': 1, 'ก.พ': 2, 'มี.ค': 3, 'เม.ย': 4, 'พ.ค': 5, 'มิ.ย': 6,
        'ก.ค': 7, 'ส.ค': 8, 'ก.ย': 9, 'ต.ค': 10, 'พ.ย': 11, 'ธ.ค': 12
    }
    try:
        clean_date = date_str.strip()
        day_match = re.search(r'^\d+', clean_date)
        if not day_match: day_match = re.search(r'\d+', clean_date)
        day = int(day_match.group()) if day_match else 1
        month = 1
        for m_name, m_idx in months_map.items():
            if m_name in clean_date or m_name.replace('.', '') in clean_date:
                month = m_idx
                break
        year_match = re.search(r'(25\d{2}|20\d{2}|[5-7]\d)', clean_date)
        year = int(year_match.group()) if year_match else 2569
        if year < 100: year += 2500
        elif year < 2100: year += 543
        return datetime(year - 543, month, day).date()
    except Exception as e:
        return None

if __name__ == "__main__":
    test_dates = [
        "12 ม.ค. 2569",
        "1 กพ 69",
        "15 มิ.ย. 69 (อาทิตย์)",
        "31 ธ.ค. 2026",
        "10 ก.ย 2569",
        "5 มกราคม 2569"
    ]
    
    print("Testing date parsing logic:")
    for d in test_dates:
        parsed = parse_thai_date_to_comparable(d)
        print(f"'{d}' -> {parsed}")
