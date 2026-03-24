from flask import Blueprint, redirect
from app.models import Posts, Medicines, Addmp, CustomerOrder
from app.utils import render_page, is_admin_logged_in, is_customer_logged_in
from datetime import datetime

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    if is_admin_logged_in():
        return redirect('/dashboard')
    if is_customer_logged_in():
        return redirect('/customer/catalog')

    total_pharmacies = Posts.query.count()
    total_orders = Medicines.query.count() + CustomerOrder.query.count()
    total_medicines = Addmp.query.count()
    return render_page('index.html',
                       total_pharmacies=total_pharmacies,
                       total_orders=total_orders,
                       total_medicines=total_medicines)


@main_bp.route('/aboutus')
def aboutus():
    return render_page('aboutus.html')


@main_bp.route('/api/health')
def api_health():
    from flask import current_app
    return {
        'status': 'ok',
        'app': current_app.config['APP_NAME'],
        'timestamp': datetime.utcnow().isoformat(),
    }
