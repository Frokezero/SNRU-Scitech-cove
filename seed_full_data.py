import json
import os
import uuid
import random

# Base paths
USERS_FILE = 'users.json'
EVENTS_FILE = 'events.json'
PARTICIPATIONS_FILE = 'participations.json'

def load_json(path, default):
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return default

def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def seed():
    # 1. Users
    users = {
        "admin": {
            "password": "admin",
            "name": "แอดมินส่วนกลาง",
            "role": "admin"
        },
        "major_sci": {
            "password": "password",
            "name": "คณะวิทยาศาสตร์และเทคโนโลยี",
            "role": "major",
            "major": "คณะวิทยาศาสตร์และเทคโนโลยี"
        },
        "chemistry": {
            "password": "password",
            "name": "สาขาวิชาเคมี",
            "role": "major",
            "major": "สาขาวิชาเคมี"
        }
    }

    majors = ["สาขาวิชาเคมี", "สาขาวิชาฟิสิกส์", "สาขาวิชาชีววิทยา", "สาขาวิชาคณิตศาสตร์", "สาขาวิชาวิทยาการคอมพิวเตอร์"]
    
    # Create 10 test students
    for i in range(1, 11):
        username = f"student_{i:02d}"
        users[username] = {
            "password": "password",
            "name": f"นักศึกษา ทดสอบที่ {i}",
            "role": "student",
            "major": random.choice(majors)
        }

    save_json(USERS_FILE, users)

    # 2. Events
    event_ids = []
    events = [
        {
            "id": str(uuid.uuid4()),
            "date": "10 ม.ค. 69",
            "title": "ปฐมนิเทศนักศึกษาใหม่ 2569",
            "status": "เสร็จสิ้น",
            "score": 50,
            "owner": "แอดมินส่วนกลาง",
            "category": "กิจกรรมมหาวิทยาลัย"
        },
        {
            "id": str(uuid.uuid4()),
            "date": "15 ก.พ. 69",
            "title": "กิจกรรมค่ายอาสาพัฒนาชนบท",
            "status": "รอการดำเนินการ",
            "score": 100,
            "owner": "สโมสรนักศึกษา",
            "category": "กิจกรรมสาขาวิชา"
        },
        {
            "id": str(uuid.uuid4()),
            "date": "20 มี.ค. 69",
            "title": "Open House 2026",
            "status": "เสร็จสิ้น",
            "score": 30,
            "owner": "คณะวิทยาศาสตร์และเทคโนโลยี",
            "category": "กิจกรรมมหาวิทยาลัย"
        }
    ]
    
    for e in events:
        event_ids.append(e['id'])
    
    save_json(EVENTS_FILE, events)

    # 3. Participations (Mix of statuses)
    participations = []
    # Approved ones for leaderboard
    for i in range(1, 6):
        participations.append({
            "username": f"student_{i:02d}",
            "event_id": events[0]['id'],
            "event_title": events[0]['title'],
            "event_date": "2026-01-10",
            "image_url": "https://images.unsplash.com/photo-1523050853064-dbad350e707a?q=80&w=200&h=200&fit=crop",
            "status": "approved",
            "timestamp": "2026-01-11T10:00:00"
        })

    # Pending ones for testing Admin modal
    for i in range(6, 9):
        participations.append({
            "username": f"student_{i:02d}",
            "event_id": events[0]['id'],
            "event_title": events[0]['title'],
            "event_date": "2026-01-10",
            "image_url": "https://images.unsplash.com/photo-1517245386807-bb43f82c33c4?q=80&w=200&h=200&fit=crop",
            "status": "pending",
            "timestamp": "2026-01-12T14:30:00"
        })

    save_json(PARTICIPATIONS_FILE, participations)
    print("Successfully seeded all data with categories and scores.")

if __name__ == "__main__":
    seed()
