from datetime import datetime
from app import db


class Posts(db.Model):
    __tablename__ = 'posts'
    mid = db.Column(db.Integer, primary_key=True)
    medical_name = db.Column(db.String(120), nullable=False)
    owner_name = db.Column(db.String(200), nullable=False)
    phone_no = db.Column(db.String(20), nullable=False)
    address = db.Column(db.String(300), nullable=False)


class Medicines(db.Model):
    __tablename__ = 'medicines'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    mid = db.Column(db.String(50), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    medicines = db.Column(db.String(500), nullable=False)
    products = db.Column(db.String(500), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='Pending')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class Addmp(db.Model):
    __tablename__ = 'addmp'
    sno = db.Column(db.Integer, primary_key=True, autoincrement=True)
    medicine = db.Column(db.String(500), nullable=False)


class Addpd(db.Model):
    __tablename__ = 'addpd'
    sno = db.Column(db.Integer, primary_key=True, autoincrement=True)
    product = db.Column(db.String(500), nullable=False)


class Logs(db.Model):
    __tablename__ = 'logs'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    mid = db.Column(db.String(50), nullable=True)
    action = db.Column(db.String(100), nullable=False)
    date = db.Column(db.String(100), nullable=False)


class Customer(db.Model):
    __tablename__ = 'customers'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    full_name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class CustomerOrder(db.Model):
    __tablename__ = 'customer_orders'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    customer_id = db.Column(db.Integer, nullable=False)
    medicines = db.Column(db.String(500), nullable=False)
    products = db.Column(db.String(500), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='Pending')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
