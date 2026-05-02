import json
from werkzeug.security import generate_password_hash

def hash_passwords():
    with open('users.json', 'r', encoding='utf-8') as f:
        users = json.load(f)
    
    for username, data in users.items():
        pwd = data.get('password')
        # Check if already hashed (hashes usually start with 'scrypt:' or 'pbkdf2:')
        if pwd and not (pwd.startswith('scrypt:') or pwd.startswith('pbkdf2:')):
            data['password'] = generate_password_hash(pwd)
            print(f"Hashed password for {username}")
            
    with open('users.json', 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=4)
    print("User password hashing completed.")

if __name__ == "__main__":
    hash_passwords()
