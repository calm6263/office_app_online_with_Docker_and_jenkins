"""
نقطة دخول WSGI - يستخدمها Gunicorn في الإنتاج
تشغيل: gunicorn --config gunicorn.conf.py wsgi:application

Flask-Migrate CLI:
  flask db init       # مرة واحدة فقط
  flask db migrate -m "وصف التغيير"
  flask db upgrade
"""
from app import app, init_db

init_db()

application = app
