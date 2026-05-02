import json
import random
from werkzeug.security import generate_password_hash

# List of majors based on login.html dropdown
MAJORS = [
    "สาขาวิชาเคมี",
    "สาขาวิชาฟิสิกส์",
    "สาขาวิชาชีววิทยา",
    "สาขาวิชาคณิตศาสตร์",
    "สาขาวิชาสถิติ",
    "สาขาวิชาวิทยาการคอมพิวเตอร์",
    "สาขาวิชาเทคโนโลยีสารสนเทศ",
    "สาขาวิชาวิทยาศาสตร์สิ่งแวดล้อม",
    "สาขาวิชาคหกรรมศาสตร์",
    "สาขาวิชาสาธารณสุขศาสตร์"
]

FIRST_NAMES = ["สมชาย", "สมศรี", "สมเดช", "มาลี", "วิชัย", "กนกวรรณ", "ณัฐวุฒิ", "อรทัย", "จิรายุ", "สุพรรษา", "ธนพล", "พิมพา"]
LAST_NAMES = ["ใจดี", "มีสุข", "รักเรียน", "เก่งการ", "ขยันยิ่ง", "อดทน", "ตั้งใจ", "พากเพียร", "ดีงาม", "เจริญรุ่ง", "มั่นคง", "สดใส"]

def load_users():
    with open('users.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def save_users(users):
    with open('users.json', 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=4)

def generate_students():
    users = load_users()
    
    # We will use a single password hash to save time since it's just mock data
    print("Generating common password hash for '1234'...")
    common_hash = generate_password_hash('1234')
    
    student_count = 0
    start_id = 6610000000
    
    for major in MAJORS:
        # Generate a random number between 10 and 30 for this major
        num_students = random.randint(10, 30)
        print(f"Generating {num_students} students for {major}...")
        
        for _ in range(num_students):
            student_id = str(start_id + student_count)
            fname = random.choice(FIRST_NAMES)
            lname = random.choice(LAST_NAMES)
            full_name = f"{fname} {lname}"
            
            users[student_id] = {
                "password": common_hash,
                "name": full_name,
                "major": major,
                "role": "student"
            }
            student_count += 1
            
    save_users(users)
    print(f"Successfully generated {student_count} test students!")

if __name__ == '__main__':
    generate_students()
