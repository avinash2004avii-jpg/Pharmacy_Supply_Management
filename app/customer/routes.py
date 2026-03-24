import csv
import io
import logging
from flask import Blueprint, request, redirect, flash, make_response, session
from app import db
from app.models import Customer, CustomerOrder, Addmp, Addpd
from app.utils import render_page, customer_required

logger = logging.getLogger(__name__)
customer_bp = Blueprint('customer', __name__)


@customer_bp.route('/customer/catalog', methods=['GET', 'POST'])
@customer_required
def customer_catalog():
    customer = Customer.query.get_or_404(session['customer_id'])
    q = request.args.get('q', '').strip()

    meds_query = Addmp.query
    prods_query = Addpd.query
    if q:
        meds_query = meds_query.filter(Addmp.medicine.ilike(f'%{q}%'))
        prods_query = prods_query.filter(Addpd.product.ilike(f'%{q}%'))

    medicines_list = meds_query.order_by(Addmp.medicine.asc()).all()
    products_list = prods_query.order_by(Addpd.product.asc()).all()

    if request.method == 'POST':
        medicines = request.form.get('medicines', '').strip()
        products = request.form.get('products', '').strip()
        amount = request.form.get('amount', '').strip()

        if not all([medicines, products, amount]):
            flash('All fields are required.', 'danger')
            return render_page('customer/catalog.html', customer=customer,
                               medicines_list=medicines_list, products_list=products_list, search_q=q)
        try:
            amount_int = int(amount)
            if amount_int <= 0:
                raise ValueError
        except ValueError:
            flash('Amount must be a positive number.', 'danger')
            return render_page('customer/catalog.html', customer=customer,
                               medicines_list=medicines_list, products_list=products_list, search_q=q)

        try:
            order = CustomerOrder(customer_id=customer.id, medicines=medicines,
                                  products=products, amount=amount_int, status='Pending')
            db.session.add(order)
            db.session.commit()
            flash('Order placed successfully!', 'success')
            return redirect('/customer/orders')
        except Exception as e:
            logger.error('Customer order error: %s', e)
            db.session.rollback()
            flash('Unable to place order. Please try again.', 'danger')

    return render_page('customer/catalog.html', customer=customer,
                       medicines_list=medicines_list, products_list=products_list, search_q=q)


@customer_bp.route('/customer/orders')
@customer_required
def customer_orders():
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '').strip()
    query = CustomerOrder.query.filter_by(customer_id=session['customer_id'])
    if status_filter:
        query = query.filter_by(status=status_filter)
    pagination = query.order_by(CustomerOrder.id.desc()).paginate(page=page, per_page=10, error_out=False)
    return render_page('customer/orders.html', orders=pagination.items,
                       pagination=pagination, status_filter=status_filter)


@customer_bp.route('/customer/orders/<int:order_id>/cancel', methods=['POST'])
@customer_required
def customer_cancel_order(order_id):
    order = CustomerOrder.query.filter_by(id=order_id, customer_id=session['customer_id']).first_or_404()
    if order.status != 'Pending':
        flash('Only pending orders can be cancelled.', 'warning')
        return redirect('/customer/orders')
    order.status = 'Cancelled'
    db.session.commit()
    flash(f'Order #{order.id} cancelled.', 'info')
    return redirect('/customer/orders')


@customer_bp.route('/customer/orders/export/csv')
@customer_required
def export_customer_orders_csv():
    rows = CustomerOrder.query.filter_by(customer_id=session['customer_id']).order_by(CustomerOrder.id.desc()).all()
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(['Order ID', 'Medicines', 'Products', 'Amount', 'Status', 'Created At'])
    for r in rows:
        w.writerow([r.id, r.medicines, r.products, r.amount, r.status,
                    r.created_at.strftime('%Y-%m-%d %H:%M:%S') if r.created_at else ''])
    resp = make_response(buf.getvalue())
    resp.headers['Content-Type'] = 'text/csv'
    resp.headers['Content-Disposition'] = 'attachment; filename=my_orders.csv'
    return resp
