from functools import wraps
from flask import session, redirect, url_for, flash, jsonify, request


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': 'يجب تسجيل الدخول'}), 401
            return redirect(url_for('login'))
        if session.get('role') != 'admin':
            if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': 'غير مصرح'}), 403
            flash('ليس لديك صلاحية لهذا الإجراء', 'danger')
            return redirect(url_for('main'))
        return f(*args, **kwargs)
    return decorated


def customer_login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'customer_id' not in session:
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated
