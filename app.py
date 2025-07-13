import os
import shutil
import glob
import threading
import time
import logging
import traceback
import json
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from arabic_reshaper import reshape
from bidi.algorithm import get_display
import pandas as pd
import io
from sqlalchemy import extract, func, case, Index, and_, or_
from sqlalchemy.orm import load_only, joinedload
import time
from sqlalchemy.exc import OperationalError

# تحديد المسار الأساسي للمشروع
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your_secret_key_here')
DATABASE_URI = os.environ.get('DATABASE_URL', 'postgresql://user:password@db:5432/office_services')
if DATABASE_URI.startswith("postgres://"):
    DATABASE_URI = DATABASE_URI.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# تحديث المسارات لاستخدام المسار المطلق
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'static', 'transaction_files')
app.config['BACKUP_DIR'] = os.path.join(BASE_DIR, 'database_backups')
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx', 'txt'}

# تحسين إعدادات جلسة قاعدة البيانات
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 300,
    'pool_size': 10,
    'max_overflow': 20
}
app.logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
app.logger.addHandler(handler)
db = SQLAlchemy(app)

# تسجيل فلتر from_json لجينجا
@app.template_filter('from_json')
def from_json_filter(data):
    return json.loads(data)

# فلتر جديد لتحويل التاريخ
@app.template_filter('to_date')
def to_date_filter(date_str):
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except:
        return None

# إعداد نظام التسجيل للأخطاء
logging.basicConfig(
    filename=os.path.join(BASE_DIR, 'office_app.log'),
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# قائمة الخدمات مع الأسعار الافتراضية
SERVICES = [
    {"name": "ترجمة مستندات", "price": 0},
    {"name": "تصديق أوراق", "price": 0},
    {"name": "طباعة ملون", "price": 0},
    {"name": "طباعة أبيض وأسود", "price": 0},
    {"name": "طباعة A5", "price": 0},
    {"name": "سكنر", "price": 0},
    {"name": "ايس كريم", "price": 0},
    {"name": "قرطاسية", "price": 0},
    {"name": "عطور", "price": 0},
    {"name": "دفتر", "price": 0},
    {"name": "قلم", "price": 0},
    {"name": "شاحن", "price": 0},
    {"name": "وصلة", "price": 0},
    {"name": "مشروب بارد", "price": 0},
    {"name": "خدمة أونلاين", "price": 0},
    {"name": "ترجمة باسبور", "price": 0},
    {"name": "خدمة أخرى 1", "price": 0},
    {"name": "خدمة أخرى 2", "price": 0},
    {"name": "التسجيل على الجامعة", "price": 0},
    {"name": "خارجية", "price": 0},
    {"name": "عدلية", "price": 0},
    {"name": "ابوستيل", "price": 0},
    {"name": "ترجمة دبلوم (مع ختم طبق الأصل)", "price": 0},
    {"name": "ترجمة دبلوم (بدون ختم طبق الأصل)", "price": 0}
]

# نماذج قاعدة البيانات
class User(db.Model):
    __tablename__ = 'users'  # تغيير هنا من 'user' إلى 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='user')

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)     
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)
    link = db.Column(db.String(200))  # رابط مرتبط بالإشعار

    user = db.relationship('User', backref=db.backref('notifications', lazy='dynamic'))

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False, unique=True)
    email = db.Column(db.String(100))
    password = db.Column(db.String(255))  # تأكد من أن الطول 255
    registration_date = db.Column(db.DateTime, default=datetime.utcnow)

class ServiceRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    service_type = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default='جديد')  # جديد، قيد المعالجة، مكتمل، ملغي
    request_date = db.Column(db.DateTime, default=datetime.utcnow)
    transaction_id = db.Column(db.Integer, db.ForeignKey('transaction.id'))

    customer = db.relationship('Customer', backref=db.backref('requests', lazy=True))
    transaction = db.relationship('Transaction', backref=db.backref('service_request', uselist=False))

class RequestFile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey('service_request.id'))
    file_path = db.Column(db.String(200))
    file_type = db.Column(db.String(20))

    request = db.relationship('ServiceRequest', backref=db.backref('files', lazy=True))

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(20), nullable=False, index=True)
    time = db.Column(db.String(10), nullable=False)
    user = db.Column(db.String(50), nullable=False, index=True)
    client_name = db.Column(db.String(100), nullable=False, index=True)
    phone = db.Column(db.String(20), index=True)
    office_location = db.Column(db.String(50))
    services = db.Column(db.Text, nullable=False)
    university_name = db.Column(db.String(100))
    quantity = db.Column(db.Integer)
    total = db.Column(db.Float)
    payment_status = db.Column(db.String(20), index=True)
    payment_method = db.Column(db.String(20), index=True)
    receiver_number = db.Column(db.String(20))
    paid_amount = db.Column(db.Float, default=0.0)
    remaining_amount = db.Column(db.Float, default=0.0)
    paid_by = db.Column(db.String(50))  # تم التصحيح هنا ✅
    receive_date = db.Column(db.String(20), index=True)
    delivery_date = db.Column(db.String(20), index=True)
    notes = db.Column(db.Text)
    source_language = db.Column(db.String(50), index=True)
    target_language = db.Column(db.String(50), index=True)
    status = db.Column(db.String(20), default='قيد التنفيذ', index=True)
    paid_date = db.Column(db.Date)  # تم التصحيح هنا ✅
    is_pending = db.Column(db.Boolean, default=True, index=True)
    is_edit = db.Column(db.Boolean, default=False)
    # فهارس مركبة لأداء أفضل
    __table_args__ = (
        Index('idx_date_client', 'date', 'client_name'),
        Index('idx_date_payment', 'date', 'payment_status'),
        Index('idx_date_status', 'date', 'status'),
        Index('idx_payment_status_method', 'payment_status', 'payment_method'),
        Index('idx_client_phone', 'client_name', 'phone'),
    )

class TransactionFile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey('transaction.id'), index=True)
    file_path = db.Column(db.String(200))
    file_type = db.Column(db.String(20))  # image, pdf, word

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, index=True)  # تم التغيير هنا ✅
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(200))
    paid_by = db.Column(db.String(50))

# وظائف مساعدة
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def create_notification(username, message, link=None):
    """إنشاء إشعار جديد للمستخدم"""
    user = User.query.filter_by(username=username).first()
    if user:
        notification = Notification(
            user_id=user.id,
            message=message,
            link=link
        )
        db.session.add(notification)
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logging.error(f"خطأ في إنشاء إشعار: {str(e)}")

def auto_backup():
    """تنفيذ نسخ احتياطي يومي للحفاظ على آخر 7 نسخ"""
    base_dir = os.path.abspath(os.path.dirname(__file__))
    backup_dir = app.config['BACKUP_DIR']
    os.makedirs(backup_dir, exist_ok=True)
    
    while True:
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = os.path.join(backup_dir, f"office_backup_{timestamp}.sql")
            
            # استخدام pg_dump لعمل نسخة احتياطية
            db_user = os.environ.get('POSTGRES_USER', 'user')
            db_password = os.environ.get('POSTGRES_PASSWORD', 'password')
            db_name = os.environ.get('POSTGRES_DB', 'office_services')
            
            # بناء أمر النسخ الاحتياطي
            command = f"pg_dump -U {db_user} -h db -d {db_name} > {backup_file}"
            os.environ['PGPASSWORD'] = db_password
            
            # تنفيذ النسخ الاحتياطي
            os.system(command)
            
            # حذف النسخ القديمة
            backups = glob.glob(os.path.join(backup_dir, "office_backup_*.sql"))
            backups.sort(key=os.path.getmtime, reverse=True)
            
            for old_backup in backups[7:]:
                try:
                    os.remove(old_backup)
                except Exception as e:
                    logging.error(f"فشل حذف نسخة احتياطية: {str(e)}")
            
            time.sleep(24 * 60 * 60)  # الانتظار 24 ساعة
            
        except Exception as e:
            logging.error(f"فشل النسخ الاحتياطي: {str(e)}\n{traceback.format_exc()}")
            time.sleep(60 * 60)  # الانتظار ساعة ثم إعادة المحاولة

# بدء النسخ الاحتياطي في خيط منفصل
if not getattr(app, 'backup_thread_started', False):
    backup_thread = threading.Thread(target=auto_backup)
    backup_thread.daemon = True
    backup_thread.start()
    app.backup_thread_started = True

# إنشاء مجلدات باستخدام المسارات المطلقة
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['BACKUP_DIR'], exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, 'static', 'reports'), exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, 'static', 'fonts'), exist_ok=True)

# المسارات
@app.route('/')
def index():
    if 'user' in session or 'customer_id' in session:
        if 'user' in session:
            return redirect(url_for('main'))
        else:
            return redirect(url_for('customer_dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user'] = username
            return redirect(url_for('main'))
        else:
            flash('بيانات الدخول غير صحيحة', 'danger')
    
    return render_template('login.html')

@app.route('/customer_login', methods=['POST'])
def customer_login():
    if request.method == 'POST':
        phone = request.form['phone']
        password = request.form['password']
        
        app.logger.debug(f"Attempting login for phone: {phone}")
        
        customer = Customer.query.filter_by(phone=phone).first()
        
        if customer:
            app.logger.debug(f"Customer found: {customer.id} - {customer.name}")
            app.logger.debug(f"Stored password hash: {customer.password}")
            
            # التحقق من كلمة المرور
            if check_password_hash(customer.password, password):
                session['customer_id'] = customer.id
                app.logger.debug("Login successful, redirecting to dashboard")
                return redirect(url_for('customer_dashboard'))
            else:
                app.logger.warning("Password verification failed")
        else:
            app.logger.warning(f"No customer found for phone: {phone}")
        
        flash('بيانات الدخول غير صحيحة', 'danger')
    
    return redirect(url_for('index'))

@app.route('/customer_register', methods=['GET', 'POST'])  # تم التعديل هنا
def customer_register():
    if request.method == 'POST':
        name = request.form['name']
        phone = request.form['phone']
        email = request.form['email']
        password = request.form['password']
        
        # التحقق من صحة البريد الإلكتروني
        if not email or '@' not in email:
            flash('يرجى إدخال بريد إلكتروني صحيح', 'danger')
            return redirect(url_for('customer_register'))
        
        existing = Customer.query.filter_by(phone=phone).first()
        if existing:
            flash('رقم الهاتف مسجل مسبقاً', 'danger')
            return redirect(url_for('customer_register'))
        
        new_customer = Customer(
            name=name,
            phone=phone,
            email=email,
            password=generate_password_hash(password)
        )
        db.session.add(new_customer)
        db.session.commit()
        app.logger.debug(f"تم تسجيل عميل جديد: ID={new_customer.id}, الهاتف={new_customer.phone}")

        flash('تم إنشاء حسابك بنجاح، يمكنك تسجيل الدخول الآن', 'success')
        return redirect(url_for('index'))
    
    # تمرير قائمة الخدمات المطلوبة
    required_services = [
        "ترجمة مستندات", "تصديق أوراق", "عدلية", "خارجية",
        "ابوستيل", "التسجيل على الجامعة", "ترجمة باسبور"
    ]
    
    return render_template('customer_register.html', services=required_services)

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

@app.route('/customer_logout')
def customer_logout():
    session.pop('customer_id', None)
    return redirect(url_for('index'))

@app.route('/main')
def main():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    today = datetime.now().strftime('%Y-%m-%d')
    return render_template('main.html', user=session['user'], today=today, 
                          services=SERVICES)

@app.route('/customer_dashboard')
def customer_dashboard():
    if 'customer_id' not in session:
        return redirect(url_for('index'))
    
    customer = Customer.query.get(session['customer_id'])
    requests = ServiceRequest.query.filter_by(customer_id=customer.id).order_by(ServiceRequest.request_date.desc()).all()
    
    return render_template('customer_dashboard.html', customer=customer, requests=requests)

@app.route('/new_service_request', methods=['GET', 'POST'])
def new_service_request():
    if 'customer_id' not in session:
        return redirect(url_for('index'))
    
    # فلترة الخدمات لاستخدام خدمات الترجمة فقط
    translation_services = [s for s in SERVICES if "ترجمة" in s['name']]

    if request.method == 'POST':
        try:
            service_type = request.form['service_type']
            description = request.form['description']
            
            new_request = ServiceRequest(
                customer_id=session['customer_id'],
                service_type=service_type,
                description=description,
                status='جديد'
            )
            db.session.add(new_request)
            db.session.flush()  # للحصول على ID
            
            # حفظ الملفات
            if 'document_files' in request.files:
                files = request.files.getlist('document_files')
                for file in files:
                    if file and allowed_file(file.filename):
                        filename = secure_filename(file.filename)
                        # حفظ الملفات في مجلد الطلبات داخل مجلد المعاملات
                        request_folder = os.path.join(app.config['UPLOAD_FOLDER'], 'customer_requests', str(new_request.id))
                        os.makedirs(request_folder, exist_ok=True)
                        filepath = os.path.join(request_folder, filename)
                        file.save(filepath)
                        
                        ext = filename.rsplit('.', 1)[1].lower()
                        file_type = 'word' if ext in ['doc', 'docx'] else 'pdf' if ext == 'pdf' else 'image'
                        
                        # حفظ المسار النسبي فقط
                        relative_path = os.path.join('transaction_files', 'customer_requests', str(new_request.id), filename).replace('\\', '/')
                        
                        file_record = RequestFile(
                            request_id=new_request.id,
                            file_path=relative_path,
                            file_type=file_type
                        )
                        db.session.add(file_record)
            
            db.session.commit()
            flash('تم تقديم طلبك بنجاح، سنقوم بالاتصال بك قريباً', 'success')
            return redirect(url_for('customer_dashboard'))
        
        except Exception as e:
            db.session.rollback()
            logging.error(f"فشل في تقديم الطلب: {str(e)}")
            flash(f'حدث خطأ أثناء تقديم الطلب: {str(e)}', 'danger')  # إضافة تفاصيل الخطأ
    
    # تمرير قائمة الخدمات للقالب
    return render_template('new_request.html', services=translation_services)


@app.route('/add_transaction', methods=['POST'])
def add_transaction():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    try:
        # جمع البيانات من النموذج بشكل صحيح
        services_list = []
        all_service_names = [service['name'] for service in SERVICES]
        
        # إنشاء قائمة بالخدمات المختارة وأسعارها
        selected_services = {}
        for service_name in all_service_names:
            price_key = f'price_{service_name}'
            if service_name in request.form.getlist('services[]'):
                price_str = request.form.get(price_key, '0')
                try:
                    price = float(price_str) if price_str else 0.0
                    if price <= 0:
                        flash(f'سعر غير صالح للخدمة: {service_name}', 'warning')
                        return redirect(url_for('main'))
                except:
                    flash(f'سعر غير صالح للخدمة: {service_name}', 'warning')
                    return redirect(url_for('main'))
                
                selected_services[service_name] = {
                    "price": price,
                    "status": "قيد التنفيذ"
                }
        
        # التحقق من وجود خدمات وأسعار صالحة
        if len(selected_services) == 0:
            flash('يرجى اختيار خدمة واحدة على الأقل', 'warning')
            return redirect(url_for('main'))
        
        # تحويل القاموس إلى قائمة
        for name, data in selected_services.items():
            services_list.append({
                "name": name, 
                "price": data["price"],
                "status": data["status"]
            })
        
        # حساب الإجمالي
        total_price = sum(item['price'] for item in services_list) * int(request.form['quantity'])
        
        if total_price <= 0:
            flash('السعر الإجمالي يجب أن يكون أكبر من صفر', 'warning')
            return redirect(url_for('main'))
        
        # الحصول على الوقت الحالي (ساعة ودقيقة)
        current_time = datetime.now().strftime('%H:%M')
        
        # تحديد تاريخ الدفع الفعلي وحقول الدفع
        payment_status = request.form['payment_status']
        is_pending = payment_status in ['لاحقاً', 'تقسيط']
        
        # تحديد حقول الدفع بناءً على حالة الدفع
        if payment_status == 'مدفوعة':
            paid_amount = total_price
            remaining_amount = 0.0
            paid_date = datetime.now().date()
        elif payment_status == 'لاحقاً':
            paid_amount = 0.0
            remaining_amount = total_price
            paid_date = None
        elif payment_status == 'تقسيط':
            paid_amount = float(request.form.get('paid_amount', 0)) or 0.0
            remaining_amount = total_price - paid_amount
            paid_date = datetime.now().date()   # تاريخ الدفع للجزء المدفوع
        
        data = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'time': current_time,
            'user': session['user'],
            'client_name': request.form['client_name'],
            'phone': request.form['phone'],
            'office_location': request.form['office_location'],
            'services': json.dumps(services_list, ensure_ascii=False),
            'university_name': request.form.get('university_name', ''),
            'quantity': int(request.form['quantity']),
            'total': total_price,
            'payment_status': payment_status,
            'payment_method': request.form['payment_method'],
            'receiver_number': request.form.get('receiver_number', ''),
            'paid_amount': paid_amount,
            'remaining_amount': remaining_amount,
            'paid_by': '',
            'receive_date': request.form.get('receive_date', ''),
            'delivery_date': request.form.get('delivery_date', ''),
            'notes': request.form.get('notes', ''),
            'source_language': request.form.get('source_language', ''),
            'target_language': request.form.get('target_language', ''),
            'status': 'قيد التنفيذ',  # الحالة الافتراضية الجديدة
            'paid_date': paid_date,  # تاريخ الدفع الفعلي
            'is_pending': is_pending,  # حالة الدفع
            'is_edit': False  # ليست معاملة معدلة
        }
        
        # التحقق من البيانات
        if not data['client_name']:
            flash('يرجى إدخال اسم العميل', 'warning')
            return redirect(url_for('main'))
        
        if data['quantity'] <= 0:
            flash('العدد يجب أن يكون أكبر من صفر', 'warning')
            return redirect(url_for('main'))
        
        if total_price <= 0:
            flash('السعر الإجمالي يجب أن يكون أكبر من صفر', 'warning')
            return redirect(url_for('main'))
        
        # حفظ المعاملة
        transaction = Transaction(**data)
        db.session.add(transaction)
        db.session.flush()  # الحصول على ID قبل الـ commit
        
        # حفظ الملفات
        if 'document_files' in request.files:
            files = request.files.getlist('document_files')
            for file in files:
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    # إنشاء مجلد للمعاملات باستخدام المسار المطلق
                    transaction_folder = os.path.join(app.config['UPLOAD_FOLDER'], str(transaction.id))
                    os.makedirs(transaction_folder, exist_ok=True)
                    filepath = os.path.join(transaction_folder, filename)
                    file.save(filepath)
                        
                    # تحديد نوع الملف
                    ext = filename.rsplit('.', 1)[1].lower()
                    if ext in ['pdf']:
                        file_type = 'pdf'
                    elif ext in ['doc', 'docx']:
                        file_type = 'word'
                    else:
                        file_type = 'image'
                    
                    file_record = TransactionFile(
                        transaction_id=transaction.id,
                        file_path=os.path.join('transaction_files', str(transaction.id), filename).replace('\\', '/'),
                        file_type=file_type
                    )
                    db.session.add(file_record)
        
        db.session.commit()
        
        # إنشاء إشعار للمستخدم
        create_notification(
            session['user'], 
            f'تمت إضافة معاملة جديدة رقم #{transaction.id} للعميل {transaction.client_name}'
        )
        
        flash('تمت إضافة المعاملة بنجاح', 'success')
    
    except Exception as e:
        db.session.rollback()
        logging.error(f"خطأ في إضافة معاملة: {str(e)}\n{traceback.format_exc()}")
        flash('حدث خطأ أثناء إضافة المعاملة', 'danger')
    
    return redirect(url_for('main'))

@app.route('/review_transactions')
def review_transactions():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    # تحديد الحقول المطلوبة فقط
    fields_to_load = [
        Transaction.id, 
        Transaction.date, 
        Transaction.time, 
        Transaction.user, 
        Transaction.client_name, 
        Transaction.phone, 
        Transaction.office_location,
        Transaction.services, 
        Transaction.university_name, 
        Transaction.quantity, 
        Transaction.total, 
        Transaction.payment_status,
        Transaction.payment_method, 
        Transaction.receiver_number, 
        Transaction.paid_amount, 
        Transaction.remaining_amount,
        Transaction.receive_date, 
        Transaction.delivery_date, 
        Transaction.notes, 
        Transaction.source_language, 
        Transaction.target_language,
        Transaction.status, 
        Transaction.paid_by, 
        Transaction.paid_date, 
        Transaction.is_pending,
        Transaction.is_edit
    ]
    
    # تطبيق الفلاتر مع تحديد الحقول
    query = Transaction.query.options(load_only(*fields_to_load)).filter(Transaction.status != 'ملغية (تم التعديل)')
    
    filter_pending = request.args.get('pending', 'false') == 'true'
    simplified = request.args.get('simplified', 'false') == 'true'
    status_filter = request.args.get('status_filter', '')  # الفلتر الجديد
    date_partition = request.args.get('date_partition', '')  # تجزئة التاريخ
    
    # فلترة المعاملات غير المدفوعة (لاحقاً أو تقسيط)
    if filter_pending or simplified:
        query = query.filter(Transaction.payment_status.in_(['لاحقاً', 'تقسيط']))
    
    # فلترة حسب حالة المعاملة
    if status_filter:
        query = query.filter(Transaction.status == status_filter)
    
    # فلاتر إضافية
    client_name = request.args.get('client_name')
    if client_name:
        query = query.filter(Transaction.client_name.like(f'%{client_name}%'))
    
    phone_filter = request.args.get('phone')
    if phone_filter:
        query = query.filter(Transaction.phone.like(f'%{phone_filter}%'))
    
    payment_status_filter = request.args.get('payment_status')
    if payment_status_filter and payment_status_filter != 'الكل':
        query = query.filter_by(payment_status=payment_status_filter)
    
    # فلتر جديد: طريقة الدفع (كاش أو أونلاين)
    payment_method_filter = request.args.get('payment_method')
    if payment_method_filter and payment_method_filter != 'الكل':
        query = query.filter(Transaction.payment_method == payment_method_filter)
    
    date_filter = request.args.get('date_filter')
    if date_filter:
        today = datetime.now().date()
        
        if date_filter == 'today':
            query = query.filter(Transaction.date == today.strftime('%Y-%m-%d'))
        elif date_filter == 'yesterday':
            yesterday = today - timedelta(days=1)
            query = query.filter(Transaction.date == yesterday.strftime('%Y-%m-%d'))
        elif date_filter == 'this_week':
            start_of_week = today - timedelta(days=today.weekday())
            end_of_week = start_of_week + timedelta(days=6)
            query = query.filter(Transaction.date.between(
                start_of_week.strftime('%Y-%m-%d'),
                end_of_week.strftime('%Y-%m-%d')
            ))
        elif date_filter == 'this_month':
            start_of_month = today.replace(day=1)
            end_of_month = (start_of_month + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            query = query.filter(Transaction.date.between(
                start_of_month.strftime('%Y-%m-%d'),
                end_of_month.strftime('%Y-%m-%d')
            ))
        elif date_filter == 'last_month':
            first_day_current_month = today.replace(day=1)
            last_month_end = first_day_current_month - timedelta(days=1)
            last_month_start = last_month_end.replace(day=1)
            query = query.filter(Transaction.date.between(
                last_month_start.strftime('%Y-%m-%d'),
                last_month_end.strftime('%Y-%m-%d')
            ))
    
    # فلترة حسب النطاق الزمني
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    if start_date and end_date:
        query = query.filter(Transaction.date.between(start_date, end_date))
    
    # فلترة حسب اللغة المصدر (نص حر)
    source_lang_filter = request.args.get('source_language')
    if source_lang_filter:
        query = query.filter(Transaction.source_language.like(f'%{source_lang_filter}%'))
    
    # فلترة حسب اللغة الهدف (نص حر)
    target_lang_filter = request.args.get('target_language')
    if target_lang_filter:
        query = query.filter(Transaction.target_language.like(f'%{target_lang_filter}%'))
    
    # فلترة حسب الخدمة (بحث جزئي)
    service_filter = request.args.get('service_filter')
    if service_filter and service_filter != 'الكل':
        query = query.filter(Transaction.services.like(f'%"{service_filter}"%'))
    
    # فلترة حسب الوقت
    start_time = request.args.get('start_time')
    end_time = request.args.get('end_time')
    if start_time and end_time:
        query = query.filter(Transaction.time >= start_time, Transaction.time <= end_time)
    
    # تجزئة البيانات حسب التاريخ
    if date_partition:
        partition_field = {
            'daily': Transaction.date,
            'weekly': func.strftime('%Y-%W', Transaction.date),
            'monthly': func.strftime('%Y-%m', Transaction.date)
        }.get(date_partition, Transaction.date)
        
        query = query.group_by(partition_field)
    
    # الترقيم
    page = request.args.get('page', 1, type=int)
    per_page = 10
    transactions_pagination = query.order_by(Transaction.date.desc(), Transaction.time.desc()).paginate(page=page, per_page=per_page)
    transactions = transactions_pagination.items
    
    # حساب الإحصائيات باستخدام استعلامات تجميعية
    stats = {
        'daily_gross_income': 0,  # الجديد: الدخل اليومي الإجمالي
        'daily_income': 0,        # الجديد: الدخل اليومي الصافي
        'monthly_gross_income': 0, # الجديد: الدخل الشهري الإجمالي
        'monthly_income': 0,      # الجديد: الدخل الشهري الصافي
        'daily_count': 0,
    }
    
    today = datetime.now().date()
    today_str = today.strftime('%Y-%m-%d')
    current_month = today.month
    current_year = today.year
    
    # حساب الدخل اليومي الإجمالي (جميع المدفوعات بتاريخ اليوم)
    daily_income_query = db.session.query(
        func.sum(Transaction.paid_amount)
    ).filter(
        Transaction.paid_date == today_str
    ).scalar() or 0
    
    stats['daily_gross_income'] = daily_income_query
    
    # حساب المعاملات اليومية (جميع المعاملات التي تم إنشاؤها اليوم)
    daily_created_transactions = db.session.query(
        func.count(Transaction.id)
    ).filter(
        Transaction.date == today_str
    ).scalar() or 0
    
    stats['daily_count'] = daily_created_transactions
    
    # حساب الدخل الشهري الإجمالي: جميع المدفوعات في الشهر الحالي
    monthly_income_query = db.session.query(
    func.sum(Transaction.paid_amount)
    ).filter(
    extract('month', func.cast(Transaction.paid_date, db.Date)) == current_month,
    extract('year', func.cast(Transaction.paid_date, db.Date)) == current_year
    ).scalar() or 0
    
    stats['monthly_gross_income'] = monthly_income_query
    
    # حساب إجمالي المصاريف
    total_expenses = db.session.query(
        func.sum(Expense.amount)
    ).scalar() or 0
    
    # حساب المصاريف اليومية
    daily_expenses = db.session.query(
        func.sum(Expense.amount)
    ).filter(
        Expense.date == today_str
    ).scalar() or 0

# حساب المصاريف الشهرية
    monthly_expenses = db.session.query(
          func.sum(Expense.amount)
    ).filter(
          extract('month', Expense.date) == current_month,
          extract('year', Expense.date) == current_year
    ).scalar() or 0
    
    # حساب الدخل اليومي الصافي
    stats['daily_income'] = stats['daily_gross_income'] - daily_expenses
    
    # حساب الدخل الشهري الصافي
    stats['monthly_income'] = stats['monthly_gross_income'] - monthly_expenses
    
    # حساب إجمالي الديون المستحقة باستخدام استعلام فعال
    pending_total = db.session.query(
        func.sum(
            case(
                (Transaction.payment_status == 'لاحقاً', Transaction.total),
                (Transaction.payment_status == 'تقسيط', Transaction.remaining_amount),
                else_=0
            )
        )
    ).filter(Transaction.is_pending == True).scalar() or 0
    
    # احسب مواعيد التسليم القريبة (خلال 3 أيام)
    today = datetime.now().date()
    three_days_later = today + timedelta(days=3)
    
    upcoming_deliveries = Transaction.query.filter(
        Transaction.delivery_date != None,
        Transaction.delivery_date <= three_days_later.strftime('%Y-%m-%d'),
        Transaction.delivery_date >= today.strftime('%Y-%m-%d'),
        Transaction.status != 'تم الإنجاز'
    ).options(load_only(Transaction.id, Transaction.client_name, Transaction.delivery_date)).all()
    
    # جلب الإشعارات للمستخدم الحالي
    user = User.query.filter_by(username=session['user']).first()
    notifications = []
    unread_count = 0
    if user:
        notifications = Notification.query.filter_by(user_id=user.id).order_by(Notification.timestamp.desc()).limit(5).all()
        unread_count = Notification.query.filter_by(user_id=user.id, is_read=False).count()
    
    # حساب الإحصائيات المالية للمعاملات المصفاة
    filtered_stats = {
        'total_sum': 0,
        'paid_sum': 0,
        'remaining_sum': 0,
        'count': len(transactions)
    }
    
    if transactions:
        # استخدام استعلام تجميعي بدلاً من معالجة في الذاكرة
        aggregated = db.session.query(
            func.sum(Transaction.total),
            func.sum(Transaction.paid_amount),
            func.sum(Transaction.remaining_amount)
        ).filter(Transaction.id.in_([t.id for t in transactions])).first()
        
        if aggregated:
            filtered_stats['total_sum'] = aggregated[0] or 0
            filtered_stats['paid_sum'] = aggregated[1] or 0
            filtered_stats['remaining_sum'] = aggregated[2] or 0
    
    # ترجمة المصطلحات للروسية
    russian_translations = {
        "مدفوعة": "Оплачено",
        "لاحقاً": "Позже",
        "تقسيط": "Рассрочка",
        "قيد التنفيذ": "В процессе",
        "تم الإنجاز": "Завершено",
        "كاش": "Наличные",
        "أونلاين": "Онлайн"
    }
    
    return render_template(
        'review_transactions.html',
        transactions=transactions,
        stats=stats,
        filtered_stats=filtered_stats,  # تمرير الإحصائيات المصفاة
        filter_pending=filter_pending,
        simplified=simplified,
        user=session['user'],
        services=SERVICES,
        expenses=Expense.query.all(),  # إضافة المصاريف للعرض
        total_expenses=total_expenses,
        daily_expenses=daily_expenses,
        pending_total=pending_total,  # الجديد: الديون المستحقة
        pagination=transactions_pagination,
        upcoming_deliveries=upcoming_deliveries,
        today=today,
        notifications=notifications,
        unread_count=unread_count,
        highlight_from_request=True,
        russian_translations=russian_translations
    )

@app.route('/update_to_paid/<int:transaction_id>', methods=['POST'])
def update_to_paid(transaction_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    
    try:
        transaction = Transaction.query.get(transaction_id)
        if transaction:
            transaction.payment_status = 'مدفوعة'
            transaction.paid_date = datetime.now().strftime('%Y-%m-%d')  # تحديث تاريخ الدفع الفعلي
            transaction.paid_by = session['user']
            transaction.paid_amount = transaction.total
            transaction.remaining_amount = 0
            transaction.is_pending = False  # تحديث الحالة
            db.session.commit()
            
            # إنشاء إشعار للمستخدم
            create_notification(
                session['user'], 
                f'تم دفع معاملة رقم #{transaction.id} للعميل {transaction.client_name}',
                url_for('review_transactions')
            )
            
            flash('تم تحديث حالة الدفع بنجاح', 'success')
        else:
            flash('المعاملة غير موجودة', 'danger')
    except Exception as e:
        db.session.rollback()
        logging.error(f"خطأ في تحديث حالة الدفع: {str(e)}")
        flash('حدث خطأ أثناء تحديث حالة الدفع', 'danger')
    
    return redirect(request.referrer or url_for('review_transactions'))

@app.route('/complete_transaction/<int:transaction_id>', methods=['POST'])
def complete_transaction(transaction_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    
    try:
        transaction = Transaction.query.get(transaction_id)
        if transaction:
            # تحديث حالة المعاملة العامة
            transaction.status = 'تم الإنجاز'
            
            # تحديث حالة جميع الخدمات
            services = json.loads(transaction.services) if transaction.services else []
            for service in services:
                if service.get('status') != 'تم الإنجاز':
                    service['status'] = 'تم الإنجاز'
            transaction.services = json.dumps(services, ensure_ascii=False)
            
            db.session.commit()
            
            # إنشاء إشعار للمستخدم
            create_notification(
                session['user'], 
                f'تم إنجاز معاملة رقم #{transaction.id} للعميل {transaction.client_name}',
                url_for('review_transactions')
            )
            
            flash('تم نقل المعاملة إلى حالة "تم الإنجاز" وإنجاز جميع الخدمات بنجاح', 'success')
        else:
            flash('المعاملة غير موجودة', 'danger')
    except Exception as e:
        db.session.rollback()
        logging.error(f"خطأ في نقل حالة المعاملة: {str(e)}")
        flash('حدث خطأ أثناء نقل حالة المعاملة', 'danger')
    
    return redirect(request.referrer or url_for('review_transactions'))

@app.route('/complete_service/<int:transaction_id>/<service_name>', methods=['POST'])
def complete_service(transaction_id, service_name):
    if 'user' not in session:
        flash('يجب تسجيل الدخول أولاً', 'danger')
        return redirect(url_for('login'))
    
    transaction = Transaction.query.get(transaction_id)
    if not transaction:
        flash('المعاملة غير موجودة', 'danger')
        return redirect(request.referrer)
    
    try:
        services = json.loads(transaction.services) if transaction.services else []
        updated = False
        
        # تحديث حالة الخدمة المحددة
        for service in services:
            if service['name'] == service_name:
                service['status'] = 'تم الإنجاز'
                updated = True
                break
        
        if updated:
            transaction.services = json.dumps(services, ensure_ascii=False)
            db.session.commit()
            
            # إنشاء إشعار للمستخدم
            create_notification(
                session['user'], 
                f'تم إنجاز خدمة {service_name} في معاملة رقم #{transaction.id}',
                url_for('review_transactions')
            )
            
            flash(f'تم إنجاز خدمة {service_name} بنجاح', 'success')
        else:
            flash('لم يتم العثور على الخدمة', 'warning')
            
    except Exception as e:
        db.session.rollback()
        logging.error(f"خطأ في إنجاز الخدمة: {str(e)}")
        flash('حدث خطأ أثناء إنجاز الخدمة', 'danger')
    
    return redirect(request.referrer)

@app.route('/edit_transaction/<int:transaction_id>', methods=['GET', 'POST'])
def edit_transaction(transaction_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    
    original_transaction = Transaction.query.get_or_404(transaction_id)
    
    services_data = json.loads(original_transaction.services) if original_transaction.services else []
    
    # إزالة التحقق من الصلاحية - أي مستخدم يمكنه تعديل أي معاملة
    if request.method == 'POST':
        try:
            # حذف المعاملة الأصلية وملفاتها
            files = TransactionFile.query.filter_by(transaction_id=original_transaction.id).all()
            for file in files:
                try:
                    file_path = os.path.join(BASE_DIR, 'static', file.file_path)
                    if os.path.exists(file_path):
                        os.remove(file_path)
                except Exception as e:
                    logging.error(f"خطأ في حذف الملف: {str(e)}")
                db.session.delete(file)
            
            # حذف مجلد المعاملة
            transaction_folder = os.path.join(app.config['UPLOAD_FOLDER'], str(original_transaction.id))
            if os.path.exists(transaction_folder):
                try:
                    shutil.rmtree(transaction_folder)
                except Exception as e:
                    logging.error(f"فشل حذف مجلد المعاملة: {str(e)}")
            
            db.session.delete(original_transaction)
            db.session.flush()
            
            # إنشاء معاملة جديدة بالبيانات المعدلة
            services_list = []
            service_names = request.form.getlist('services[]')
            
            # إنشاء قائمة بالخدمات المختارة وأسعارها وحالاتها
            for service_name in service_names:
                if service_name:  # إذا كانت الخدمة مختارة
                    price_key = f'price_{service_name}'
                    status_key = f'status_{service_name}'
                    
                    price_str = request.form.get(price_key, '0')
                    status = request.form.get(status_key, 'قيد التنفيذ')
                    
                    try:
                        price = float(price_str) if price_str else 0.0
                        if price <= 0:
                            flash(f'سعر غير صالح للخدمة: {service_name}', 'danger')
                            return redirect(url_for('edit_transaction', transaction_id=transaction_id))
                    except:
                        flash(f'سعر غير صالح للخدمة: {service_name}', 'danger')
                        return redirect(url_for('edit_transaction', transaction_id=transaction_id))
                    
                    services_list.append({
                        "name": service_name,
                        "price": price,
                        "status": status
                    })
            
            # التحقق من وجود خدمات وأسعار صالحة
            if len(services_list) == 0:
                flash('يرجى اختيار خدمة واحدة على الأقل', 'danger')
                return redirect(url_for('edit_transaction', transaction_id=transaction_id))
            
            # حساب الإجمالي
            total_price = sum(item['price'] for item in services_list)
            quantity = int(request.form['quantity'])
            total_price = total_price * quantity
            
            # تحديد تاريخ الدفع الفعلي وحقول الدفع
            payment_status = request.form['payment_status']
            is_pending = payment_status in ['لاحقاً', 'تقسيط']
            
            # تحديد حقول الدفع بناءً على حالة الدفع
            if payment_status == 'مدفوعة':
                paid_amount = total_price
                remaining_amount = 0.0
                paid_date = datetime.now().strftime('%Y-%m-%d')
            elif payment_status == 'لاحقاً':
                paid_amount = 0.0
                remaining_amount = total_price
                paid_date = None
            elif payment_status == 'تقسيط':
                paid_amount = float(request.form.get('paid_amount', 0)) or 0.0
                remaining_amount = total_price - paid_amount
                paid_date = datetime.now().strftime('%Y-%m-%d')  # تاريخ الدفع للجزء المدفوع
            
            # إنشاء معاملة جديدة بالبيانات المعدلة
            edited_transaction = Transaction(
                date=datetime.now().strftime('%Y-%m-%d'),
                time=datetime.now().strftime('%H:%M'),
                user=session['user'],
                client_name=request.form['client_name'],
                phone=request.form['phone'],
                office_location=request.form['office_location'],
                services=json.dumps(services_list, ensure_ascii=False),
                university_name=request.form.get('university_name', ''),
                quantity=quantity,
                total=total_price,
                payment_status=payment_status,
                payment_method=request.form['payment_method'],
                receiver_number=request.form.get('receiver_number', ''),
                paid_amount=paid_amount,
                remaining_amount=remaining_amount,
                paid_by='',
                receive_date=request.form.get('receive_date', ''),
                delivery_date=request.form.get('delivery_date', ''),
                notes=f"تم التعديل على المعاملة الأصلية #{original_transaction.id}\n" + request.form.get('notes', ''),
                source_language=request.form.get('source_language', ''),
                target_language=request.form.get('target_language', ''),
                status=request.form.get('status', 'قيد التنفيذ'),
                paid_date=paid_date,
                is_pending=is_pending,
                is_edit=True  # علامة أن هذه معاملة معدلة
            )
            
            # حفظ المعاملة المعدلة
            db.session.add(edited_transaction)
            db.session.flush()
            
            # حفظ الملفات الجديدة للمعاملة المعدلة
            if 'document_files' in request.files:
                files = request.files.getlist('document_files')
                for file in files:
                    if file and allowed_file(file.filename):
                        filename = secure_filename(file.filename)
                        # إنشاء مجلد للمعاملات إذا لم يكن موجوداً
                        transaction_folder = os.path.join(app.config['UPLOAD_FOLDER'], str(edited_transaction.id))
                        os.makedirs(transaction_folder, exist_ok=True)
                        filepath = os.path.join(transaction_folder, filename)
                        file.save(filepath)
                        
                        # تحديد نوع الملف
                        ext = filename.rsplit('.', 1)[1].lower()
                        if ext in ['pdf']:
                            file_type = 'pdf'
                        elif ext in ['doc', 'docx']:
                            file_type = 'word'
                        else:
                            file_type = 'image'
                        
                        file_record = TransactionFile(
                            transaction_id=edited_transaction.id,
                            file_path=os.path.join('transaction_files', str(edited_transaction.id), filename).replace('\\', '/'),
                            file_type=file_type
                        )
                        db.session.add(file_record)
            
            db.session.commit()
            
            # إنشاء إشعار للمستخدم
            create_notification(
                session['user'], 
                f'تم تعديل معاملة رقم #{original_transaction.id} وإنشاء معاملة جديدة #{edited_transaction.id}',
                url_for('review_transactions')
            )
            
            flash('تم تحديث المعاملة بنجاح وإنشاء معاملة جديدة', 'success')
            return redirect(url_for('review_transactions'))
        except Exception as e:
            db.session.rollback()
            logging.error(f"خطأ في تعديل المعاملة: {str(e)}\n{traceback.format_exc()}")
            flash(f'حدث خطأ أثناء تعديل المعاملة: {str(e)}', 'danger')
            # إعادة تحميل الصفحة مع البيانات المدخلة
            services_data = services_list
    
    # جلب الملفات المرفقة
    files = TransactionFile.query.filter_by(transaction_id=transaction_id).all()
    
    # إنشاء قاموس للخدمات المختارة للبحث السريع
    selected_services_dict = {service['name']: service for service in services_data}
    
    return render_template(
        'edit_transaction.html',
        transaction=original_transaction,
        services=SERVICES,
        selected_services=services_data,
        selected_services_dict=selected_services_dict,
        files=files,
        user=session['user']
    )


@app.route('/delete_transaction/<int:transaction_id>', methods=['POST'])
def delete_transaction(transaction_id):
    if 'user' not in session or session['user'] != 'ابراهيم':
        flash('ليس لديك صلاحية لهذا الإجراء', 'danger')
        return redirect(url_for('review_transactions'))
    
    try:
        transaction = Transaction.query.get(transaction_id)
        if transaction:
            # حذف الملفات المرتبطة
            files = TransactionFile.query.filter_by(transaction_id=transaction_id).all()
            for file in files:
                try:
                    file_path = os.path.join(BASE_DIR, 'static', file.file_path)
                    if os.path.exists(file_path):
                        os.remove(file_path)
                except Exception as e:
                    logging.error(f"خطأ في حذف الملف: {str(e)}")
                db.session.delete(file)
            
            # حذف مجلد المعاملة
            transaction_folder = os.path.join(app.config['UPLOAD_FOLDER'], str(transaction_id))
            if os.path.exists(transaction_folder):
                try:
                    shutil.rmtree(transaction_folder)
                except Exception as e:
                    logging.error(f"فشل حذف مجلد المعاملة: {str(e)}")
            
            db.session.delete(transaction)
            db.session.commit()
            
            # إنشاء إشعار للمستخدم
            create_notification(
                session['user'], 
                f'تم حذف معاملة رقم #{transaction_id}',
                url_for('review_transactions')
            )
            
            flash('تم حذف المعاملة بنجاح', 'success')
        else:
            flash('المعاملة غير موجودة', 'danger')
    except Exception as e:
        db.session.rollback()
        logging.error(f"خطأ في حذف المعاملة: {str(e)}")
        flash('حدث خطأ أثناء حذف المعاملة', 'danger')
    
    return redirect(url_for('review_transactions')) 

@app.route('/transaction_files/<int:transaction_id>')
def transaction_files(transaction_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    
    transaction = Transaction.query.get(transaction_id)
    files = TransactionFile.query.filter_by(transaction_id=transaction_id).all()
    
    return render_template(
        'transaction_files.html',
        transaction=transaction,
        files=files,
        user=session['user']
    )

@app.route('/delete_file/<int:file_id>', methods=['POST'])
def delete_file(file_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    
    file_record = TransactionFile.query.get(file_id)
    if not file_record:
        flash('الملف غير موجود', 'danger')
        return redirect(request.referrer)
    
    # التحقق من الصلاحية: إما المستخدم هو الذي أضاف المعاملة أو هو المدير
    transaction = Transaction.query.get(file_record.transaction_id)
    if session['user'] != transaction.user and session['user'] != 'ابراهيم':
        flash('ليس لديك صلاحية لحذف هذا الملف', 'danger')
        return redirect(request.referrer)
    
    try:
        # حذف الملف من النظام
        file_path = os.path.join(BASE_DIR, 'static', file_record.file_path)
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # حذف السجل من قاعدة البيانات
        db.session.delete(file_record)
        db.session.commit()
        
        # إنشاء إشعار للمستخدم
        create_notification(
            session['user'], 
            f'تم حذف ملف من معاملة رقم #{transaction.id}',
            url_for('transaction_files', transaction_id=transaction.id)
        )
        
        flash('تم حذف الملف بنجاح', 'success')
    except Exception as e:
        db.session.rollback()
        logging.error(f"خطأ في حذف الملف: {str(e)}")
        flash('حدث خطأ أثناء حذف الملف', 'danger')
    
    return redirect(request.referrer)

@app.route('/export_pdf')
def export_pdf():
    if 'user' not in session or session['user'] != 'ابراهيم':
        flash('ليس لديك صلاحية لهذا الإجراء', 'danger')
        return redirect(url_for('review_transactions'))
    
    try:
        # جلب الحقول الضرورية فقط
        fields = [
            Transaction.id,
            Transaction.date,
            Transaction.time,
            Transaction.user,
            Transaction.client_name,
            Transaction.phone,
            Transaction.office_location,
            Transaction.services,
            Transaction.university_name,
            Transaction.quantity,
            Transaction.total,
            Transaction.payment_status,
            Transaction.payment_method,
            Transaction.receiver_number,
            Transaction.paid_amount,
            Transaction.remaining_amount,
            Transaction.receive_date,
            Transaction.delivery_date,
            Transaction.source_language,
            Transaction.target_language,
            Transaction.status,
            Transaction.paid_date
        ]
        
        # جلب جميع المعاملات مع الحقول المحددة فقط
        transactions = Transaction.query.options(load_only(*fields)).order_by(
            Transaction.date.desc(), 
            Transaction.time.desc()
        ).all()
        
        # إنشاء ملف PDF
        pdf_file = os.path.join(BASE_DIR, 'static', 'reports', 'transactions_report.pdf')
        os.makedirs(os.path.dirname(pdf_file), exist_ok=True)
        
        c = canvas.Canvas(pdf_file, pagesize=A4)
        width, height = A4
        
        # تسجيل خط عربي
        try:
            # استخدام خط يدعم العربية
            font_path = os.path.join(BASE_DIR, 'static', 'fonts', 'Amiri-Regular.ttf')
            pdfmetrics.registerFont(TTFont('Arabic', font_path))
            c.setFont("Arabic", 12)
        except Exception as e:
            logging.error(f"خطأ في تسجيل الخط: {str(e)}")
            try:
                # محاولة استخدام خط بديل
                pdfmetrics.registerFont(TTFont('Arabic', 'Arial'))
                c.setFont("Arabic", 12)
            except:
                c.setFont("Helvetica", 12)
        
        # دالة مساعدة لكتابة النص العربي
        def draw_arabic_text(text, x, y, font_size=12):
            if not text:
                return
            reshaped_text = reshape(text)
            bidi_text = get_display(reshaped_text)
            try:
                c.setFont("Arabic", font_size)
            except:
                c.setFont("Helvetica", font_size)
            c.drawString(x, y, bidi_text)
        
        # عنوان التقرير
        title = "تقرير المعاملات"
        draw_arabic_text(title, 50, height - 50, 16)
        
        # تاريخ التقرير
        report_date = datetime.now().strftime("%Y-%m-%d %H:%M")
        date_text = f"تاريخ التقرير: {report_date}"
        draw_arabic_text(date_text, width - 200, height - 50)
        
        # عناوين الأعمدة
        headers = [
            "رقم", "التاريخ", "الوقت", "المستخدم", "اسم العميل", "الهاتف", "المكان",
            "الخدمة", "الجامعة", "العدد", "الإجمالي",
            "حالة الدفع", "طريقة الدفع", "رقم المستلم", 
            "المدفوع", "المتبقي", "تاريخ الاستلام", "تاريخ التسليم", "الحالة", "تاريخ الدفع"
        ]
        
        y_position = height - 100
        x_positions = [40, 70, 100, 130, 180, 230, 280, 330, 380, 430, 470, 520, 570, 620, 670, 720, 770, 820, 870, 920]
        
        for i, header in enumerate(headers):
            draw_arabic_text(header, x_positions[i], y_position)
        
        # بيانات المعاملات
        y_position -= 30
        for trans in transactions:
            services_list = json.loads(trans.services) if trans.services else []
            services_text = ", ".join([f"{s['name']} ({s['price']}) - {s['status']}" for s in services_list])
            
            row = [
                str(trans.id),
                trans.date,
                trans.time,
                trans.user,
                trans.client_name,
                trans.phone or "",
                trans.office_location or "",
                services_text,
                trans.university_name or "",
                str(trans.quantity),
                f"{trans.total:.2f}",
                trans.payment_status,
                trans.payment_method,
                trans.receiver_number or "",
                f"{trans.paid_amount:.2f}",
                f"{trans.remaining_amount:.2f}",
                trans.receive_date or "",
                trans.delivery_date or "",
                trans.status,
                trans.paid_date or ""  # الجديد: تاريخ الدفع الفعلي
            ]
            
            for i, value in enumerate(row):
                draw_arabic_text(value, x_positions[i], y_position)
            
            y_position -= 15
            if y_position < 50:
                c.showPage()
                y_position = height - 50
                # إعادة تعيين الخط للصفحة الجديدة
                try:
                    c.setFont("Arabic", 12)
                except:
                    c.setFont("Helvetica", 12)
        
        c.save()
        
        return send_file(pdf_file, as_attachment=True)
    
    except Exception as e:
        logging.error(f"خطأ في تصدير PDF: {str(e)}\n{traceback.format_exc()}")
        flash('حدث خطأ أثناء تصدير التقرير', 'danger')
        return redirect(url_for('review_transactions'))

@app.route('/export_excel')
def export_excel():
    if 'user' not in session or session['user'] != 'ابراهيم':
        flash('ليس لديك صلاحية لهذا الإجراء', 'danger')
        return redirect(url_for('review_transactions'))
    
    try:
        # تحديد الحقول المطلوبة فقط
        fields = [
            Transaction.id,
            Transaction.date,
            Transaction.time,
            Transaction.user,
            Transaction.client_name,
            Transaction.phone,
            Transaction.office_location,
            Transaction.services,
            Transaction.university_name,
            Transaction.quantity,
            Transaction.total,
            Transaction.payment_status,
            Transaction.payment_method,
            Transaction.receiver_number,
            Transaction.paid_amount,
            Transaction.remaining_amount,
            Transaction.receive_date,
            Transaction.delivery_date,
            Transaction.source_language,
            Transaction.target_language,
            Transaction.status,
            Transaction.paid_date
        ]
        
        # جلب البيانات مع الحقول المحددة فقط
        transactions = Transaction.query.options(load_only(*fields)).order_by(
            Transaction.date.desc(), 
            Transaction.time.desc()
        ).all()
        
        # تحضير البيانات لملف Excel
        data = []
        for trans in transactions:
            services_list = json.loads(trans.services) if trans.services else []
            services_text = ", ".join([f"{s['name']} ({s['price']}) - {s['status']}" for s in services_list])
            
            data.append({
                "رقم": trans.id,
                "التاريخ": trans.date,
                "الوقت": trans.time,
                "المستخدم": trans.user,
                "اسم العميل": trans.client_name,
                "الهاتف": trans.phone or "",
                "المكان": trans.office_location or "",
                "الخدمة": services_text,
                "الجامعة": trans.university_name or "",
                "العدد": trans.quantity,
                "الإجمالي": trans.total,
                "حالة الدفع": trans.payment_status,
                "طريقة الدفع": trans.payment_method,
                "رقم المستلم": trans.receiver_number or "",
                "المدفوع": trans.paid_amount,
                "المتبقي": trans.remaining_amount,
                "تاريخ الاستلام": trans.receive_date or "",
                "تاريخ التسليم": trans.delivery_date or "",
                "اللغة المصدر": trans.source_language or "",
                "اللغة الهدف": trans.target_language or "",
                "الحالة": trans.status,
                "تاريخ الدفع الفعلي": trans.paid_date or ""  # الجديد
            })
        
        # إنشاء DataFrame
        df = pd.DataFrame(data)
        
        # إنشاء ملف Excel في الذاكرة
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='المعاملات', index=False)
            
            # تنسيق الأعمدة
            worksheet = writer.sheets['المعاملات']
            for idx, col in enumerate(df.columns):
                max_len = max(df[col].astype(str).map(len).max(), len(col)) + 2
                worksheet.column_dimensions[chr(65 + idx)].width = max_len
        
        output.seek(0)
        
        # إرسال الملف
        return send_file(
            output,
            as_attachment=True,
            download_name=f"transactions_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    
    except Exception as e:
        logging.error(f"خطأ في تصدير Excel: {str(e)}\n{traceback.format_exc()}")
        flash('حدث خطأ أثناء تصدير التقرير', 'danger')
        return redirect(url_for('review_transactions'))

@app.route('/print_transaction/<int:transaction_id>')
def print_transaction(transaction_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    
    transaction = Transaction.query.get_or_404(transaction_id)
    services_list = json.loads(transaction.services) if transaction.services else []
    
    return render_template(
        'print_transaction.html',
        transaction=transaction,
        services_list=services_list,
        datetime=datetime
    )

@app.route('/manage_users')
def manage_users():
    if 'user' not in session or session['user'] != 'ابراهيم':
        flash('ليس لديك صلاحية لهذه الصفحة', 'danger')
        return redirect(url_for('main'))
    
    users = User.query.all()
    return render_template('manage_users.html', users=users)

@app.route('/add_user', methods=['POST'])
def add_user():
    if 'user' not in session or session['user'] != 'ابراهيم':
        return jsonify({'success': False, 'message': 'غير مصرح'}), 403
    
    try:
        username = request.form['username']
        password = request.form['password']
        
        if not username or not password:
            return jsonify({'success': False, 'message': 'يرجى ملء جميع الحقول'}), 400
        
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            return jsonify({'success': False, 'message': 'اسم المستخدم موجود مسبقاً'}), 400
        
        new_user = User(
            username=username,
            password=generate_password_hash(password)
        )
        db.session.add(new_user)
        db.session.commit()
        
        # إنشاء إشعار للمدير
        create_notification(
            session['user'], 
            f'تمت إضافة مستخدم جديد: {username}'
        )
        
        return jsonify({'success': True, 'message': 'تمت إضافة المستخدم بنجاح'})
    
    except Exception as e:
        db.session.rollback()
        logging.error(f"خطأ في إضافة مستخدم: {str(e)}")
        return jsonify({'success': False, 'message': 'حدث خطأ أثناء الإضافة'}), 500

@app.route('/update_user/<int:user_id>', methods=['POST'])
def update_user(user_id):
    if 'user' not in session or session['user'] != 'ابراهيم':
        return jsonify({'success': False, 'message': 'غير مصرح'}), 403
    
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'success': False, 'message': 'المستخدم غير موجود'}), 404
        
        new_password = request.form['password']
        if not new_password:
            return jsonify({'success': False, 'message': 'يرجى إدخال كلمة مرور'}), 400
        
        user.password = generate_password_hash(new_password)
        db.session.commit()
        
        # إنشاء إشعار للمدير
        create_notification(
            session['user'], 
            f'تم تحديث كلمة مرور المستخدم: {user.username}'
        )
        
        return jsonify({'success': True, 'message': 'تم تحديث كلمة المرور بنجاح'})
    
    except Exception as e:
        db.session.rollback()
        logging.error(f"خطأ في تحديث مستخدم: {str(e)}")
        return jsonify({'success': False, 'message': 'حدث خطأ أثناء التحديث'}), 500

@app.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if 'user' not in session or session['user'] != 'ابراهيم':
        return jsonify({'success': False, 'message': 'غير مصرح'}), 403
    
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'success': False, 'message': 'المستخدم غير موجود'}), 404
        
        if user.username == 'ابراهيم':
            return jsonify({'success': False, 'message': 'لا يمكن حذف المستخدم ابراهيم'}), 400
        
        db.session.delete(user)
        db.session.commit()
        
        # إنشاء إشعار للمدير
        create_notification(
            session['user'], 
            f'تم حذف المستخدم: {user.username}'
        )
        
        return jsonify({'success': True, 'message': 'تم حذف المستخدم بنجاح'})
    
    except Exception as e:
        db.session.rollback()
        logging.error(f"خطأ في حذف مستخدم: {str(e)}")
        return jsonify({'success': False, 'message': 'حدث خطأ أثناء الحذف'}), 500

# مسار إضافة/تعديل مصروف
@app.route('/save_expense', methods=['POST'])
def save_expense():
    if 'user' not in session or session['user'] != 'ابراهيم':
        return jsonify({'success': False, 'message': 'غير مصرح'}), 403
    
    try:
        expense_id = request.form.get('expense_id')
        if expense_id:  # تعديل مصروف موجود
            expense = Expense.query.get(expense_id)
            if not expense:
                return jsonify({'success': False, 'message': 'المصروف غير موجود'}), 404
        else:  # إضافة جديد
            expense = Expense()
        
        # تحديث البيانات
        expense.date = request.form['date']
        expense.amount = float(request.form['amount'])
        expense.description = request.form['description']
        expense.paid_by = session['user']
        
        if not expense_id:
            db.session.add(expense)
        db.session.commit()
        
        # إنشاء إشعار للمدير
        create_notification(
            session['user'], 
            f'تمت إضافة مصروف جديد: {expense.description} بقيمة {expense.amount} روبل'
        )
        
        return jsonify({'success': True, 'message': 'تم حفظ المصروف بنجاح'})
    
    except Exception as e:
        db.session.rollback()
        logging.error(f"خطأ في حفظ المصروف: {str(e)}")
        return jsonify({'success': False, 'message': 'حدث خطأ أثناء الحفظ'}), 500

# مسار الحصول على بيانات مصروف
@app.route('/get_expense/<int:expense_id>', methods=['GET'])
def get_expense(expense_id):
    if 'user' not in session or session['user'] != 'ابراهيم':
        return jsonify({'success': False, 'message': 'غير مصرح'}), 403
    
    expense = Expense.query.get(expense_id)
    if not expense:
        return jsonify({'success': False, 'message': 'المصروف غير موجود'}), 404
    
    return jsonify({
        'success': True,
        'expense': {
            'id': expense.id,
            'date': expense.date,
            'amount': expense.amount,
            'description': expense.description
        }
    })

# مسار حذف مصروف
@app.route('/delete_expense/<int:expense_id>', methods=['POST'])
def delete_expense(expense_id):
    if 'user' not in session or session['user'] != 'ابراهيم':
        flash('ليس لديك صلاحية لهذا الإجراء', 'danger')
        return redirect(url_for('review_transactions'))
    
    try:
        expense = Expense.query.get(expense_id)
        if expense:
            db.session.delete(expense)
            db.session.commit()
            
            # إنشاء إشعار للمدير
            create_notification(
                session['user'], 
                f'تم حذف المصروف: {expense.description}'
            )
            
            flash('تم حذف المصروف بنجاح', 'success')
        else:
            flash('المصروف غير موجود', 'danger')
    except Exception as e:
        db.session.rollback()
        logging.error(f"خطأ في حذف مصروف: {str(e)}")
        flash('حدث خطأ أثناء حذف المصروف', 'danger')
    
    return redirect(url_for('review_transactions'))

@app.route('/mark_notification_read/<int:notification_id>', methods=['POST'])
def mark_notification_read(notification_id):
    if 'user' not in session:
        return jsonify({'success': False, 'message': 'يجب تسجيل الدخول'}), 401
    
    notification = Notification.query.get(notification_id)
    if not notification:
        return jsonify({'success': False, 'message': 'الإشعار غير موجود'}), 404
    
    # التحقق من أن المستخدم الحالي هو صاحب الإشعار
    user = User.query.filter_by(username=session['user']).first()
    if not user or notification.user_id != user.id:
        return jsonify({'success': False, 'message': 'غير مصرح'}), 403
    
    notification.is_read = True
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/notifications')
def notifications():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    user = User.query.filter_by(username=session['user']).first()
    if not user:
        flash('المستخدم غير موجود', 'danger')
        return redirect(url_for('login'))
    
    # جلب جميع الإشعارات
    all_notifications = Notification.query.filter_by(user_id=user.id).order_by(Notification.timestamp.desc()).all()
    
    return render_template('notifications.html', 
                          all_notifications=all_notifications,
                          user=session['user'])
@app.route('/employee/requests', endpoint='employee_requests_page')
def list_employee_requests():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    # جلب جميع الطلبات غير المكتملة
    requests = ServiceRequest.query.filter(
        ServiceRequest.status.in_(['جديد', 'قيد المعالجة'])
    ).order_by(ServiceRequest.request_date.desc()).all()
    
    return render_template('employee_requests.html', requests=requests)
# مسارات الموظفين لطلبات العملاء
@app.route('/employee/requests')
def employee_requests():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    requests = ServiceRequest.query.filter(
        ServiceRequest.status.in_(['جديد', 'قيد المعالجة'])
    ).order_by(ServiceRequest.request_date.desc()).all()
    
    return render_template('employee_requests.html', requests=requests)

@app.route('/view_request/<int:request_id>')
def view_request(request_id):
    if 'user' not in session and 'customer_id' not in session:
        return redirect(url_for('index'))
    
    request = ServiceRequest.query.get_or_404(request_id)
    
    # التحقق من الصلاحية
    if 'customer_id' in session and request.customer_id != session['customer_id']:
        flash('ليس لديك صلاحية لعرض هذا الطلب', 'danger')
        return redirect(url_for('customer_dashboard'))
    
    return render_template('view_request.html', request=request)

@app.route('/create_transaction_from_request/<int:request_id>')
def create_transaction_from_request(request_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    
    # جلب طلب الخدمة
    service_request = ServiceRequest.query.get_or_404(request_id)
    
    # جلب بيانات العميل المرتبط بالطلب
    customer = Customer.query.get(service_request.customer_id)
    
    # جلب الملفات المرفقة بالطلب
    files = RequestFile.query.filter_by(request_id=request_id).all()
    
    return render_template('create_transaction.html', 
                           request=service_request,
                           customer=customer,
                           files=files,
                           services=SERVICES)

@app.route('/save_transaction_from_request/<int:request_id>', methods=['POST'])
def save_transaction_from_request(request_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    
    try:
        # جلب طلب الخدمة الأصلي
        service_request = ServiceRequest.query.get_or_404(request_id)
        customer = Customer.query.get(service_request.customer_id)
        
        # إنشاء المعاملة الجديدة
        transaction = Transaction(
            date=datetime.now().strftime('%Y-%m-%d'),
            time=datetime.now().strftime('%H:%M'),
            user=session['user'],
            client_name=customer.name,
            phone=customer.phone,
            office_location=request.form['office_location'],
            services=json.dumps([{
                "name": service_request.service_type,
                "price": float(request.form['total']),
                "status": "قيد التنفيذ"
            }], ensure_ascii=False),
            total=float(request.form['total']),
            payment_status='لاحقاً',  # تذهب للديون تلقائياً
            payment_method='كاش',
            paid_amount=0.0,
            remaining_amount=float(request.form['total']),
            status='قيد التنفيذ',
            notes=service_request.description or '',
            is_pending=True
        )
        db.session.add(transaction)
        db.session.flush()  # للحصول على ID
        
        # نسخ الملفات الأصلية من الطلب إلى المعاملة
        files = RequestFile.query.filter_by(request_id=request_id).all()
        for file in files:
            # بناء المسار الكامل للملف الأصلي
            src_path = os.path.join(BASE_DIR, 'static', file.file_path)
            
            if os.path.exists(src_path):
                # اسم الملف فقط
                filename = os.path.basename(file.file_path)
                
                # إنشاء مجلد الوجهة إذا لم يكن موجوداً
                dest_folder = os.path.join(app.config['UPLOAD_FOLDER'], str(transaction.id))
                os.makedirs(dest_folder, exist_ok=True)
                
                # المسار الجديد للملف
                dest_path = os.path.join(dest_folder, filename)
                
                # نسخ الملف
                shutil.copy2(src_path, dest_path)
                
                # إنشاء سجل الملف الجديد
                new_file_path = os.path.join('transaction_files', str(transaction.id), filename).replace('\\', '/')
                file_record = TransactionFile(
                    transaction_id=transaction.id,
                    file_path=new_file_path,
                    file_type=file.file_type
                )
                db.session.add(file_record)
        
        # حفظ الملفات الجديدة المرفقة
        if 'document_files' in request.files:
            files = request.files.getlist('document_files')
            for file in files:
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    transaction_folder = os.path.join(app.config['UPLOAD_FOLDER'], str(transaction.id))
                    os.makedirs(transaction_folder, exist_ok=True)
                    filepath = os.path.join(transaction_folder, filename)
                    file.save(filepath)
                    
                    ext = filename.rsplit('.', 1)[1].lower()
                    file_type = 'word' if ext in ['doc', 'docx'] else 'pdf' if ext == 'pdf' else 'image'
                    
                    file_record = TransactionFile(
                        transaction_id=transaction.id,
                        file_path=os.path.join('transaction_files', str(transaction.id), filename).replace('\\', '/'),
                        file_type=file_type
                    )
                    db.session.add(file_record)
        
        # تحديث حالة الطلب الأصلي
        service_request.status = 'مكتمل'
        service_request.transaction_id = transaction.id
        db.session.commit()
        
        flash('تم إنشاء المعاملة بنجاح وإضافة الطلب إلى ديون العميل', 'success')
        return redirect(url_for('employee_requests'))
    
    except Exception as e:
        db.session.rollback()
        logging.error(f"خطأ في إنشاء المعاملة: {str(e)}")
        flash(f'حدث خطأ أثناء إنشاء المعاملة: {str(e)}', 'danger')
        return redirect(url_for('create_transaction_from_request', request_id=request_id))

# وظيفة مساعدة لإنشاء إشعار للعميل
def create_notification_for_customer(customer_id, message, link=None):
    """إنشاء إشعار جديد للعميل"""
    # في هذا المثال، سنقوم بإرسال بريد إلكتروني أو رسالة نصية للعميل
    # يمكن تطويرها لاستخدام نظام الإشعارات الداخلي
    pass

def wait_for_db():
    max_retries = 5
    retry_delay = 3
    
    for i in range(max_retries):
        try:
            db.engine.connect()
            print("✅ تم الاتصال بنجاح بقاعدة البيانات")
            return True
        except OperationalError:
            print(f"⌛ محاولة {i+1}/{max_retries}: قاعدة البيانات غير جاهزة، إعادة المحاولة بعد {retry_delay} ثواني...")
            time.sleep(retry_delay)
    print("❌ فشل الاتصال بقاعدة البيانات بعد عدة محاولات")
    return False
def wait_for_db():
    max_retries = 10
    retry_delay = 5
    
    for i in range(max_retries):
        try:
            db.engine.connect()
            print("✅ تم الاتصال بنجاح بقاعدة البيانات")
            return True
        except OperationalError:
            print(f"⌛ محاولة {i+1}/{max_retries}: قاعدة البيانات غير جاهزة، إعادة المحاولة بعد {retry_delay} ثواني...")
            time.sleep(retry_delay)
    print("❌ فشل الاتصال بقاعدة البيانات بعد عدة محاولات")
    return False

if __name__ == '__main__':
    with app.app_context():
        if wait_for_db():
            db.create_all()
            print("✅ تم إنشاء الجداول بنجاح")
            
            # إنشاء المستخدمين الافتراضيين
            default_users = [
                ("مصطفى", "1234", "user"),
                ("محمد", "5678", "user"),
                ("ابراهيم", "123456789**", "admin")
            ]
            
            for username, password, role in default_users:
                user = User.query.filter_by(username=username).first()
                if not user:
                    new_user = User(
                        username=username,
                        password=generate_password_hash(password),
                        role=role
                    )
                    db.session.add(new_user)
                    print(f"تم إنشاء المستخدم: {username}")
            
            db.session.commit()
            print("تم تهيئة قاعدة البيانات بنجاح")
        else:
            print("❌ فشل تهيئة التطبيق بسبب مشاكل في قاعدة البيانات")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
