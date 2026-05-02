import json
from werkzeug.security import generate_password_hash

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
        ("ds", "สาขาวิชาวิทยาการข้อมูล")
    ]
    
    path = 'users.json'
    with open(path, 'r', encoding='utf-8') as f:
        users = json.load(f)
        
    # Keep admin
    admin_data = users.get('admin')
    new_users = {'admin': admin_data}
    
    password_hash = generate_password_hash('password')
    
    for username, name in majors:
        new_users[username] = {
            "password": password_hash,
            "name": name,
            "role": "major",
            "major": name
        }
        print(f"Created/Updated admin for: {name} (User: {username})")
        
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(new_users, f, ensure_ascii=False, indent=4)
    print("All major admin accounts created.")

if __name__ == "__main__":
    create_major_admins()
