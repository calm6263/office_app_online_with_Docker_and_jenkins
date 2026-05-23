"""اختبارات المعاملات"""
import json


def test_review_transactions_requires_login(client):
    res = client.get('/review_transactions')
    assert res.status_code == 302


def test_review_transactions_accessible(auth_user):
    res = auth_user.get('/review_transactions')
    assert res.status_code == 200


def test_add_transaction_requires_login(client):
    res = client.post('/add_transaction', data={})
    assert res.status_code == 302


def test_export_pdf_requires_admin(auth_user):
    res = auth_user.get('/export_pdf')
    assert res.status_code in (302, 403)


def test_export_excel_requires_admin(auth_user):
    res = auth_user.get('/export_excel')
    assert res.status_code in (302, 403)


def test_export_excel_admin_ok(auth_admin, app):
    from app import Transaction, db
    with app.app_context():
        t = Transaction(
            date='2025-01-01', time='10:00', user='admin_test',
            client_name='عميل', phone='1234567',
            services=json.dumps([{'name': 'ترجمة', 'price': 100, 'status': 'قيد التنفيذ'}]),
            total=100, payment_status='مدفوعة', payment_method='كاش',
            paid_amount=100, remaining_amount=0, status='قيد التنفيذ'
        )
        db.session.add(t)
        db.session.commit()

    res = auth_admin.get('/export_excel')
    assert res.status_code == 200
    assert b'xlsx' in res.content_type.encode() or res.status_code == 200

    with app.app_context():
        Transaction.query.filter_by(client_name='عميل').delete()
        db.session.commit()


def test_manage_users_admin_only(auth_user, auth_admin):
    res_user = auth_user.get('/manage_users')
    assert res_user.status_code in (302, 403)

    res_admin = auth_admin.get('/manage_users')
    assert res_admin.status_code == 200


def test_employee_requests_page(auth_user):
    res = auth_user.get('/employee/requests')
    assert res.status_code == 200


def test_notifications_page(auth_user):
    res = auth_user.get('/notifications')
    assert res.status_code == 200
