import os
import multiprocessing

# الارتباط
bind = "0.0.0.0:5000"

# العمال
workers = int(os.environ.get('GUNICORN_WORKERS', multiprocessing.cpu_count() * 2 + 1))
worker_class = "sync"
threads = 2

# المهلة الزمنية
timeout = int(os.environ.get('GUNICORN_TIMEOUT', 120))
graceful_timeout = 30
keepalive = 5

# الأمان
limit_request_line = 4096
limit_request_fields = 100
limit_request_field_size = 8190

# السجلات
accesslog = "-"
errorlog = "-"
loglevel = "warning"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s'

# إعادة التشغيل عند الخطأ
max_requests = 1000
max_requests_jitter = 100
preload_app = False
