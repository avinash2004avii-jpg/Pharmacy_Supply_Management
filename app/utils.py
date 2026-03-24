import re
import logging
from datetime import datetime
from functools import wraps
from flask import session, redirect, flash, current_app, render_template
from app import db
from app.models import Logs

logger = logging.getLogger(__name__)


def is_admin_logged_in():
    return (session.get('role') == 'admin' and
            session.get('admin_user') == current_app.config['ADMIN_USERNAME'])


def is_customer_logged_in():
    return session.get('role') == 'customer' and bool(session.get('customer_id'))


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not is_admin_logged_in():
            flash('Please login as admin first.', 'warning')
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated


def customer_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not is_customer_logged_in():
            flash('Please login as a customer first.', 'warning')
            return redirect('/customer/login')
        return f(*args, **kwargs)
    return decorated


def render_page(template, **ctx):
    return render_template(template,
                           app_name=current_app.config['APP_NAME'],
                           **ctx)


def log_action(mid, action):
    try:
        entry = Logs(mid=str(mid), action=action,
                     date=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        db.session.add(entry)
        db.session.commit()
    except Exception as e:
        logger.error('log_action failed: %s', e)
        db.session.rollback()


def valid_email(email: str) -> bool:
    return bool(re.match(r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$', email or ''))


def valid_phone(phone: str) -> bool:
    return bool(re.match(r'^\+?[\d\s\-]{7,15}$', phone or ''))
