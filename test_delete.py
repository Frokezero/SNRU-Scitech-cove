import json
from app import app, load_users

app.config['TESTING'] = True
client = app.test_client()

with client.session_transaction() as sess:
    sess['username'] = 'admin'

response = client.post('/api/admin/delete-user', json={'username': 'test_student'})
print(f"Status Code: {response.status_code}")
try:
    print(response.get_json())
except Exception as e:
    print("Response text:", response.get_data(as_text=True))
