from flask import Blueprint
from app.models import Posts, Medicines, Addmp, CustomerOrder
from app import db
from app.utils import render_page, admin_required

reports_bp = Blueprint('reports', __name__)


@reports_bp.route('/reports')
@admin_required
def reports():
    total_pharmacies = Posts.query.count()
    admin_orders = Medicines.query.count()
    customer_orders_count = CustomerOrder.query.count()
    total_orders = admin_orders + customer_orders_count

    pending = Medicines.query.filter_by(status='Pending').count()
    approved = Medicines.query.filter_by(status='Approved').count()
    delivered = Medicines.query.filter_by(status='Delivered').count()

    admin_revenue = db.session.query(
        db.func.coalesce(db.func.sum(Medicines.amount), 0)
    ).filter(Medicines.status == 'Delivered').scalar() or 0

    customer_revenue = db.session.query(
        db.func.coalesce(db.func.sum(CustomerOrder.amount), 0)
    ).filter(CustomerOrder.status == 'Delivered').scalar() or 0

    total_revenue = int(admin_revenue) + int(customer_revenue)
    total_medicines_catalog = Addmp.query.count()

    # Top medicines
    medicine_counter = {}
    for order in Medicines.query.all():
        for med in [m.strip() for m in (order.medicines or '').split(',') if m.strip()]:
            medicine_counter[med] = medicine_counter.get(med, 0) + 1
    top_medicines = sorted(medicine_counter.items(), key=lambda x: x[1], reverse=True)[:5]

    # Revenue by pharmacy
    pharmacy_revenue = []
    for post in Posts.query.all():
        rev = db.session.query(
            db.func.coalesce(db.func.sum(Medicines.amount), 0)
        ).filter(Medicines.mid == str(post.mid), Medicines.status == 'Delivered').scalar() or 0
        pharmacy_revenue.append((post.medical_name, int(rev)))
    pharmacy_revenue.sort(key=lambda x: x[1], reverse=True)

    return render_page('reports/reports.html',
                       total_pharmacies=total_pharmacies,
                       total_orders=total_orders,
                       admin_orders=admin_orders,
                       customer_orders=customer_orders_count,
                       total_revenue=total_revenue,
                       total_medicines_catalog=total_medicines_catalog,
                       pending=pending,
                       approved=approved,
                       delivered=delivered,
                       top_medicines=top_medicines,
                       pharmacy_revenue=pharmacy_revenue)
