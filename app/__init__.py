import json
import os
import secrets
from datetime import datetime, timedelta

from dotenv import load_dotenv
from flask import Flask, redirect, session, request, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash

load_dotenv()

db = SQLAlchemy()

try:
    from flask_migrate import Migrate
    migrate_ext = Migrate()
except Exception:
    migrate_ext = None


def resolve_database_url() -> str:
    db_url = os.environ.get('DATABASE_URL', '').strip()
    if db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://', 'postgresql+psycopg2://', 1)
    elif db_url.startswith('postgresql://') and 'psycopg2' not in db_url:
        db_url = db_url.replace('postgresql://', 'postgresql+psycopg2://', 1)
    if not db_url:
        db_url = 'sqlite:///pharmacy.db'
    return db_url


def create_app():
    app = Flask(__name__, template_folder='../templates', static_folder='../static')

    # Load config
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config.json')
    with open(config_path, 'r', encoding='utf-8') as f:
        params = json.load(f).get('params', {})

    app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['SQLALCHEMY_DATABASE_URI'] = resolve_database_url()
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['APP_NAME'] = params.get('app_name', 'Pharmacy Supply Management System')
    app.config['SESSION_TIMEOUT_MINUTES'] = int(os.environ.get('SESSION_TIMEOUT_MINUTES', '30'))
    app.config['SEED_DATA_ENABLED'] = os.environ.get('SEED_DATA', 'true').lower() == 'true'

    # Admin credentials
    admin_username = os.environ.get('ADMIN_USERNAME') or os.environ.get('ADMIN_USER') or 'owner'
    admin_hash = os.environ.get('ADMIN_PASSWORD_HASH', '').strip()
    admin_raw = os.environ.get('ADMIN_PASSWORD') or os.environ.get('ADMIN_PASS')
    if not admin_hash and admin_raw:
        admin_hash = generate_password_hash(admin_raw)
    if not admin_hash:
        print('WARNING: No admin password set. Using default ChangeMe@123 - update your .env file!')
        admin_hash = generate_password_hash('ChangeMe@123')

    app.config['ADMIN_USERNAME'] = admin_username
    app.config['ADMIN_PASSWORD_HASH'] = admin_hash

    db.init_app(app)
    if migrate_ext:
        migrate_ext.init_app(app, db)

    # Register blueprints
    from app.auth.routes import auth_bp
    from app.pharmacy.routes import pharmacy_bp
    from app.orders.routes import orders_bp
    from app.inventory.routes import inventory_bp
    from app.customer.routes import customer_bp
    from app.reports.routes import reports_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(pharmacy_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(inventory_bp)
    app.register_blueprint(customer_bp)
    app.register_blueprint(reports_bp)

    # Public routes
    from app.main_routes import main_bp
    app.register_blueprint(main_bp)

    # CSRF token context processor
    @app.context_processor
    def inject_globals():
        def generate_csrf():
            if '_csrf_token' not in session:
                session['_csrf_token'] = secrets.token_hex(16)
            return session['_csrf_token']
        return dict(csrf_token=generate_csrf, app_name=app.config['APP_NAME'])

    # Session timeout + CSRF guard
    @app.before_request
    def security_guards():
        endpoint = request.endpoint or ''
        if endpoint.startswith('static'):
            return

        now_ts = datetime.utcnow().timestamp()
        prev_ts = session.get('last_activity')
        timeout = app.config['SESSION_TIMEOUT_MINUTES'] * 60

        if prev_ts and (now_ts - prev_ts > timeout):
            session.clear()
            flash('Session expired due to inactivity. Please login again.', 'warning')
            if endpoint.startswith('customer'):
                return redirect('/customer/login')
            return redirect('/login')

        session['last_activity'] = now_ts

        if request.method == 'POST':
            sess_token = session.get('_csrf_token')
            form_token = request.form.get('csrf_token')
            if not sess_token or not form_token or sess_token != form_token:
                flash('Security check failed. Please try again.', 'danger')
                return redirect(request.referrer or '/')

    # Error handlers
    @app.errorhandler(404)
    def not_found(_e):
        from flask import render_template
        return render_template('errors/404.html', app_name=app.config['APP_NAME']), 404

    @app.errorhandler(500)
    def server_error(_e):
        from flask import render_template
        return render_template('errors/500.html', app_name=app.config['APP_NAME']), 500

    # Init DB on startup
    with app.app_context():
        _init_database(app)

    return app


def _init_database(app):
    from app.models import Posts, Medicines, Addmp, Addpd, Logs, Customer, CustomerOrder
    from sqlalchemy import inspect as sa_inspect
    from sqlalchemy.exc import SQLAlchemyError

    db.create_all()

    try:
        Posts.query.count()
        Medicines.query.count()
        inspector = sa_inspect(db.engine)
        cols = [c['name'] for c in inspector.get_columns('medicines')]
        if not {'status', 'created_at'}.issubset(set(cols)):
            raise SQLAlchemyError('Schema outdated')
        if 'customers' not in inspector.get_table_names():
            raise SQLAlchemyError('Missing customers table')
    except SQLAlchemyError:
        db.session.rollback()
        print('WARNING: Schema mismatch - recreating tables...')
        db.drop_all()
        db.create_all()

    if app.config['SEED_DATA_ENABLED']:
        _seed(app)


def _seed(app):
    from app.models import Posts, Medicines, Addmp, Addpd, Logs, Customer, CustomerOrder
    from werkzeug.security import generate_password_hash

    if Posts.query.count() == 0:
        db.session.add_all([
            Posts(mid=101, medical_name='CityCare Pharmacy', owner_name='Rahul Sharma', phone_no='9876543210', address='MG Road, Pune'),
            Posts(mid=102, medical_name='HealthPlus Medicals', owner_name='Anita Verma', phone_no='9876501234', address='Baner, Pune'),
            Posts(mid=103, medical_name='MedEase Store', owner_name='Suresh Patel', phone_no='9823456780', address='Koregaon Park, Pune'),
        ])

    if Addmp.query.count() == 0:
        db.session.add_all([
            Addmp(medicine='Paracetamol'), Addmp(medicine='Amoxicillin'),
            Addmp(medicine='Ibuprofen'), Addmp(medicine='Azithromycin'),
            Addmp(medicine='Cetirizine'), Addmp(medicine='Metformin'),
            Addmp(medicine='Omeprazole'), Addmp(medicine='Atorvastatin'),
        ])

    if Addpd.query.count() == 0:
        db.session.add_all([
            Addpd(product='Surgical Mask'), Addpd(product='Hand Sanitizer'),
            Addpd(product='Digital Thermometer'), Addpd(product='Blood Pressure Monitor'),
            Addpd(product='Gloves (Box)'), Addpd(product='Bandage Roll'),
        ])

    if Medicines.query.count() == 0:
        db.session.add_all([
            Medicines(mid='101', name='Rahul Sharma', medicines='Paracetamol, Ibuprofen', products='Surgical Mask', email='rahul@citycare.com', amount=2500, status='Delivered', created_at=datetime.utcnow() - timedelta(days=28)),
            Medicines(mid='102', name='Anita Verma', medicines='Amoxicillin', products='Hand Sanitizer', email='anita@healthplus.com', amount=1800, status='Pending', created_at=datetime.utcnow() - timedelta(days=3)),
            Medicines(mid='101', name='Rahul Sharma', medicines='Cetirizine', products='Digital Thermometer', email='rahul@citycare.com', amount=3300, status='Approved', created_at=datetime.utcnow() - timedelta(days=15)),
            Medicines(mid='103', name='Suresh Patel', medicines='Metformin, Omeprazole', products='Gloves (Box)', email='suresh@medease.com', amount=4100, status='Delivered', created_at=datetime.utcnow() - timedelta(days=40)),
        ])

    if Logs.query.count() == 0:
        db.session.add_all([
            Logs(mid='101', action='PHARMACY_INSERTED', date='2026-03-18 10:00:00'),
            Logs(mid='102', action='PHARMACY_INSERTED', date='2026-03-18 10:05:00'),
            Logs(mid='103', action='PHARMACY_INSERTED', date='2026-03-18 10:10:00'),
        ])

    if Customer.query.count() == 0:
        db.session.add(Customer(
            full_name='Demo Customer',
            email='customer@example.com',
            password_hash=generate_password_hash('Customer@123')
        ))

    if CustomerOrder.query.count() == 0:
        cust = Customer.query.filter_by(email='customer@example.com').first()
        if cust:
            db.session.add_all([
                CustomerOrder(customer_id=cust.id, medicines='Paracetamol', products='Surgical Mask', amount=700, status='Pending'),
                CustomerOrder(customer_id=cust.id, medicines='Ibuprofen', products='Hand Sanitizer', amount=920, status='Delivered'),
            ])

    db.session.commit()
    print('Seed data loaded.')
