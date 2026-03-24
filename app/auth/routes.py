import secrets
from flask import Blueprint, request, session, redirect, flash, current_app
from werkzeug.security import check_password_hash, generate_password_hash
from app.models import Customer
from app import db
from app.utils import render_page, is_admin_logged_in, is_customer_logged_in, valid_email

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if is_admin_logged_in():
        return redirect('/dashboard')
    if request.method == 'POST':
        username = request.form.get('uname', '').strip()
        password = request.form.get('password', '').strip()
        if (username == current_app.config['ADMIN_USERNAME'] and
                check_password_hash(current_app.config['ADMIN_PASSWORD_HASH'], password)):
            session.clear()
            session['role'] = 'admin'
            session['admin_user'] = username
            session['_csrf_token'] = secrets.token_hex(16)
            flash('Welcome back! Logged in successfully.', 'success')
            return redirect('/dashboard')
        flash('Invalid admin credentials. Please try again.', 'danger')
    return render_page('auth/login.html')


@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect('/login')


@auth_bp.route('/customer/register', methods=['GET', 'POST'])
def customer_register():
    if is_customer_logged_in():
        return redirect('/customer/catalog')
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()

        errors = []
        if not all([full_name, email, password]):
            errors.append('All fields are required.')
        elif not valid_email(email):
            errors.append('Enter a valid email address.')
        elif len(password) < 6:
            errors.append('Password must be at least 6 characters.')
        elif Customer.query.filter_by(email=email).first():
            errors.append('Email already registered. Please login.')

        if errors:
            for e in errors:
                flash(e, 'danger')
            return render_page('auth/customer_register.html')

        customer = Customer(
            full_name=full_name,
            email=email,
            password_hash=generate_password_hash(password),
        )
        db.session.add(customer)
        db.session.commit()
        flash('Account created successfully! Please login.', 'success')
        return redirect('/customer/login')
    return render_page('auth/customer_register.html')


@auth_bp.route('/customer/login', methods=['GET', 'POST'])
def customer_login():
    if is_customer_logged_in():
        return redirect('/customer/catalog')
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()
        customer = Customer.query.filter_by(email=email).first()
        if customer and check_password_hash(customer.password_hash, password):
            session.clear()
            session['role'] = 'customer'
            session['customer_id'] = customer.id
            session['customer_name'] = customer.full_name
            session['_csrf_token'] = secrets.token_hex(16)
            flash(f'Welcome, {customer.full_name}!', 'success')
            return redirect('/customer/catalog')
        flash('Invalid email or password.', 'danger')
    return render_page('auth/customer_login.html')


@auth_bp.route('/customer/logout')
def customer_logout():
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect('/customer/login')
