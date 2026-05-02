import json
from werkzeug.security import generate_password_hash

USER_FILE = 'users.json'

def migrate():
    try:
        with open(USER_FILE, 'r', encoding='utf-8') as f:
            users = json.load(f)
            
        count = 0
        for username, data in users.items():
            if not data['password'].startswith('scrypt:'):
                data['password'] = generate_password_hash(data['password'])
                count += 1
                
        if count > 0:
            with open(USER_FILE, 'w', encoding='utf-8') as f:
                json.dump(users, f, ensure_ascii=False, indent=4)
            print(f"Migrated {count} passwords successfully.")
        else:
            print("No passwords needed migration.")
    except Exception as e:
        print(f"Error migrating passwords: {e}")

if __name__ == '__main__':
    migrate()
