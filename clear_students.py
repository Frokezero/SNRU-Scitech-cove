import json

def keep_admins_only():
    with open('users.json', 'r', encoding='utf-8') as f:
        users = json.load(f)
    
    new_users = {}
    for username, data in users.items():
        if username == 'admin' or data.get('role') == 'major':
            new_users[username] = data
            
    with open('users.json', 'w', encoding='utf-8') as f:
        json.dump(new_users, f, ensure_ascii=False, indent=4)
    print(f"Cleaned users.json. Remaining users: {list(new_users.keys())}")

if __name__ == "__main__":
    keep_admins_only()
