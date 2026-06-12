import pytest
import json
from app import app, db_save_user

@pytest.fixture
def client():
    app.config['TESTING'] = True
    
    # Ensure database is initialized and has a test admin user
    from database import init_db, get_db_connection
    from werkzeug.security import generate_password_hash
    init_db()
    
    conn = get_db_connection()
    conn.execute('''
        INSERT OR REPLACE INTO users (username, password, name, email, major, role)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', ('admin', generate_password_hash('password'), 'Test Admin', 'admin@example.com', 'CS', 'admin'))
    conn.commit()
    conn.close()
    
    with app.test_client() as client:
        yield client

def test_login_page_loads(client):
    """Test that the index/login page loads successfully"""
    rv = client.get('/')
    assert rv.status_code == 200

def test_unauthorized_admin_access(client):
    """Test that accessing admin APIs without session returns 401/302"""
    rv = client.get('/api/admin/dashboard-stats')
    # Should redirect to login or return 401
    assert rv.status_code in [302, 401]

def test_dashboard_stats_with_session(client):
    """Test dashboard stats with an active session"""
    with client.session_transaction() as sess:
        sess['username'] = 'admin'
        
    rv = client.get('/api/admin/dashboard-stats')
    assert rv.status_code == 200
    data = json.loads(rv.data)
    assert data['success'] is True
    assert 'total_students' in data
