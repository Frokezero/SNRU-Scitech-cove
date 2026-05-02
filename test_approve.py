import json
from app import app, load_users

app.config['TESTING'] = True
client = app.test_client()

with client.session_transaction() as sess:
    sess['username'] = 'admin'

response = client.post('/api/admin/update-status-bulk', json={
    'event_id': 'b33eec84-f127-4c22-b522-cd21067218ae',
    'usernames': ['67102122111'],
    'status': 'approved',
    'scores': {'67102122111': 50}
})
print(f"Status Code: {response.status_code}")
try:
    print(response.get_json())
except Exception as e:
    print("Response text:", response.get_data(as_text=True))
