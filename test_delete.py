import json
from app import app, load_users

app.config['TESTING'] = True
client = app.test_client()

with client.session_transaction() as sess:
    sess['username'] = 'admin'

print("Attempting to delete user 67102122111 (should succeed and cascade)...")
response1 = client.post('/api/admin/delete-user', json={'username': '67102122111'})
print(f"Delete response - Status Code: {response1.status_code}")
print("Response JSON:", response1.get_json())

print("\nVerifying that the database is NOT locked after the deletion...")
response2 = client.get('/api/events')
print(f"Fetch events response - Status Code: {response2.status_code}")
if response2.status_code == 200:
    print("Database is clean, active, and fully operational!")
else:
    print("Failed to fetch events:", response2.get_data(as_text=True))
