import os
import pytest

os.environ.setdefault('SECRET_KEY', 'test-secret-key-for-testing-only')
os.environ.setdefault('DATABASE_URL', 'postgresql://office_user:password@db:5432/office_services')
os.environ.setdefault('FLASK_ENV', 'testing')
os.environ.setdefault('WTF_CSRF_ENABLED', 'false')

from app import app as flask_app, db as _db


@pytest.fixture(scope='session')
def app():
    flask_app.config.update({
        'TESTING': True,
        'WTF_CSRF_ENABLED': False,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
    })
    with flask_app.app_context():
        _db.create_all()
        yield flask_app
        _db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def runner(app):
    return app.test_cli_runner()


@pytest.fixture
def auth_user(client, app):
    from werkzeug.security import generate_password_hash
    from app import User
    with app.app_context():
        user = User(username='testuser', password=generate_password_hash('testpass'), role='user')
        _db.session.add(user)
        _db.session.commit()
    with client.session_transaction() as sess:
        sess['user'] = 'testuser'
        sess['role'] = 'user'
    yield client
    with app.app_context():
        User.query.filter_by(username='testuser').delete()
        _db.session.commit()


@pytest.fixture
def auth_admin(client, app):
    from werkzeug.security import generate_password_hash
    from app import User
    with app.app_context():
        admin = User(username='admin_test', password=generate_password_hash('adminpass'), role='admin')
        _db.session.add(admin)
        _db.session.commit()
    with client.session_transaction() as sess:
        sess['user'] = 'admin_test'
        sess['role'] = 'admin'
    yield client
    with app.app_context():
        User.query.filter_by(username='admin_test').delete()
        _db.session.commit()
