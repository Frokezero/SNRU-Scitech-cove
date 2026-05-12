import json
from werkzeug.security import generate_password_hash
import os

def create_major_admins():
    majors = [
        ("major_sci", "คณะวิทยาศาสตร์และเทคโนโลยี"),
        ("smo", "สโมสรนักศึกษา"),
        ("chem", "สาขาวิชาเคมี"),
        ("phys", "สาขาวิชาฟิสิกส์"),
        ("bio", "สาขาวิชาชีววิทยา"),
        ("math", "สาขาวิชาคณิตศาสตร์"),
        ("env", "สาขาวิชาวิทยาศาสตร์สิ่งแวดล้อม"),
        ("cs", "สาขาวิชาวิทยาการคอมพิวเตอร์"),
        ("ph", "สาขาวิชาสาธารณสุขศาสตร์"),
        ("dt", "สาขาวิชาเทคโนโลยีคอมพิวเตอร์และดิจิทัล"),
        ("ds", "สาขาวิชาวิทยาการข้อมูล"),
        ("stat", "สาขาวิชาสถิติ"),
        ("it", "สาขาวิชาเทคโนโลยีสารสนเทศ"),
        ("he", "สาขาวิชาคหกรรมศาสตร์")
    ]
    
    path = 'users.json'
    users = {}
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            users = json.load(f)
            
    # Hash for 'password'
    password_hash = generate_password_hash('password')
    
    for username, name in majors:
        if username not in users:
            users[username] = {
                "password": password_hash,
                "name": name,
                "role": "major",
                "major": name
            }
            print(f"Created admin for: {name} (User: {username})")
        else:
            # Update role and name if already exists but role is wrong or name changed
            users[username]["name"] = name
            users[username]["role"] = "major"
            users[username]["major"] = name
            print(f"Updated existing user to major: {name} (User: {username})")
        
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=4)
    print("All major admin accounts checked/created. Student accounts preserved.")

if __name__ == "__main__":
    create_major_admins()
