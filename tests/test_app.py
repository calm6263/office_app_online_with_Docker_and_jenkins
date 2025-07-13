import pytest
from app import app, db

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
        yield client

def test_home_page(client):
    response = client.get('/')
    assert response.status_code == 302  # Redirect to login

def test_login(client):
    response = client.post('/login', data={
        'username': 'ابراهيم',
        'password': '123456789**'
    }, follow_redirects=True)
    assert b'Main Page' in response.data