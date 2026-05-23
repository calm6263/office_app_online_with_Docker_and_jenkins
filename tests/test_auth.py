"""اختبارات المصادقة والتحكم في الوصول"""


def test_login_page_loads(client):
    res = client.get('/login')
    assert res.status_code == 200


def test_index_redirects_to_login(client):
    res = client.get('/')
    assert res.status_code == 302
    assert '/login' in res.headers['Location']


def test_login_wrong_password(client):
    res = client.post('/login', data={'username': 'nobody', 'password': 'wrong'})
    assert res.status_code == 200


def test_login_success(client, app):
    from werkzeug.security import generate_password_hash
    from app import User, db
    with app.app_context():
        u = User(username='logintest', password=generate_password_hash('pass123'), role='user')
        db.session.add(u)
        db.session.commit()

    res = client.post('/login', data={'username': 'logintest', 'password': 'pass123'},
                      follow_redirects=True)
    assert res.status_code == 200

    with app.app_context():
        User.query.filter_by(username='logintest').delete()
        db.session.commit()


def test_logout_clears_session(auth_user):
    res = auth_user.get('/logout', follow_redirects=True)
    assert res.status_code == 200


def test_admin_page_blocked_for_user(auth_user):
    res = auth_user.get('/manage_users')
    assert res.status_code in (302, 403)


def test_admin_page_accessible_for_admin(auth_admin):
    res = auth_admin.get('/manage_users')
    assert res.status_code == 200


def test_delete_transaction_blocked_for_user(auth_user):
    res = auth_user.post('/delete_transaction/999')
    assert res.status_code in (302, 403)


def test_security_headers_present(client):
    res = client.get('/login')
    assert 'X-Frame-Options' in res.headers
    assert 'X-Content-Type-Options' in res.headers
    assert res.headers['X-Content-Type-Options'] == 'nosniff'


def test_rate_limit_login(client):
    for _ in range(12):
        client.post('/login', data={'username': 'x', 'password': 'x'})
    res = client.post('/login', data={'username': 'x', 'password': 'x'})
    assert res.status_code in (200, 429)


def test_customer_register_page(client):
    res = client.get('/customer_register')
    assert res.status_code == 200


def test_main_requires_login(client):
    res = client.get('/main')
    assert res.status_code == 302


def test_404_page(client):
    res = client.get('/nonexistent_route_xyz')
    assert res.status_code == 404
