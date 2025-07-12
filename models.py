from app import db
from datetime import datetime
from sqlalchemy import Index

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