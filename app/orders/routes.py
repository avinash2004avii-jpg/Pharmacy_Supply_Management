import csv
import io
import logging
from datetime import datetime
from flask import Blueprint, request, redirect, flash, make_response
from app import db
from app.models import Medicines, Posts
from app.utils import render_page, admin_required, log_action, valid_email

logger = logging.getLogger(__name__)
orders_bp = Blueprint('orders', __name__)

VALID_STATUSES = {'Pending', 'Approved', 'Delivered'}


@orders_bp.route('/medicines', methods=['GET', 'POST'])
@admin_required
def medicine():
    from app.models import Addmp, Addpd
    pharmacies = Posts.query.order_by(Posts.medical_name.asc()).all()
    medicines_list = Addmp.query.order_by(Addmp.medicine.asc()).all()
    products_list = Addpd.query.order_by(Addpd.product.asc()).all()
    if request.method == 'POST':
        try:
            pharmacy_id = request.form.get('mid', '').strip()
            contact_name = request.form.get('name', '').strip()
            medicine_items = request.form.get('medicines', '').strip()
            product_items = request.form.get('products', '').strip()
            email = request.form.get('email', '').strip()
            amount = request.form.get('amount', '').strip()

            if not all([pharmacy_id, contact_name, medicine_items, product_items, email, amount]):
                flash('All fields are required.', 'danger')
                return render_page('orders/medicine.html', pharmacies=pharmacies,
                                   medicines_list=medicines_list, products_list=products_list)

            if not valid_email(email):
                flash('Invalid email format.', 'danger')
                return render_page('orders/medicine.html', pharmacies=pharmacies,
                                   medicines_list=medicines_list, products_list=products_list)

            try:
                amount_int = int(amount)
                if amount_int <= 0:
                    raise ValueError
            except ValueError:
                flash('Amount must be a positive number.', 'danger')
                return render_page('orders/medicine.html', pharmacies=pharmacies,
                                   medicines_list=medicines_list, products_list=products_list)

            if not Posts.query.filter_by(mid=int(pharmacy_id)).first():
                flash('Pharmacy ID not found. Register pharmacy first.', 'danger')
                return render_page('orders/medicine.html', pharmacies=pharmacies,
                                   medicines_list=medicines_list, products_list=products_list)

            entry = Medicines(mid=pharmacy_id, name=contact_name,
                              medicines=medicine_items, products=product_items,
                              email=email, amount=amount_int, status='Pending',
                              created_at=datetime.utcnow())
            db.session.add(entry)
            db.session.commit()
            log_action(entry.mid, 'ORDER_INSERTED')
            flash('Order placed successfully!', 'success')
            return redirect('/orders')
        except Exception as e:
            logger.error('Place order error: %s', e)
            db.session.rollback()
            flash('Error placing order. Please check all fields.', 'danger')
    return render_page('orders/medicine.html', pharmacies=pharmacies,
                       medicines_list=medicines_list, products_list=products_list)


@orders_bp.route('/orders')
@admin_required
def orders():
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '').strip()
    search_q = request.args.get('q', '').strip()

    query = Medicines.query
    if status_filter and status_filter in VALID_STATUSES:
        query = query.filter_by(status=status_filter)
    if search_q:
        query = query.filter(
            Medicines.name.ilike(f'%{search_q}%') |
            Medicines.medicines.ilike(f'%{search_q}%') |
            Medicines.mid.ilike(f'%{search_q}%')
        )

    pagination = query.order_by(Medicines.id.desc()).paginate(page=page, per_page=10, error_out=False)
    return render_page('orders/post.html',
                       posts=pagination.items,
                       pagination=pagination,
                       status_filter=status_filter,
                       search_q=search_q)


@orders_bp.route('/orders/<int:order_id>/status', methods=['POST'])
@admin_required
def update_order_status(order_id):
    order = Medicines.query.filter_by(id=order_id).first_or_404()
    new_status = request.form.get('status', '').strip()
    if new_status not in VALID_STATUSES:
        flash('Invalid status.', 'danger')
        return redirect('/orders')
    order.status = new_status
    db.session.commit()
    log_action(order.mid, f'ORDER_{new_status.upper()}')
    flash(f'Order #{order.id} updated to {new_status}.', 'success')
    return redirect('/orders')


@orders_bp.route('/delete-order/<int:id>', methods=['POST'])
@admin_required
def delete_order(id):
    post = Medicines.query.filter_by(id=id).first_or_404()
    log_action(post.mid, 'ORDER_DELETED')
    db.session.delete(post)
    db.session.commit()
    flash('Order deleted.', 'warning')
    return redirect('/orders')


@orders_bp.route('/orders/export/csv')
@admin_required
def export_orders_csv():
    rows = Medicines.query.order_by(Medicines.id.desc()).all()
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(['Order ID', 'Pharmacy ID', 'Contact Name', 'Medicines', 'Products', 'Email', 'Amount', 'Status', 'Created At'])
    for r in rows:
        w.writerow([r.id, r.mid, r.name, r.medicines, r.products, r.email, r.amount, r.status,
                    r.created_at.strftime('%Y-%m-%d %H:%M:%S') if r.created_at else ''])
    resp = make_response(buf.getvalue())
    resp.headers['Content-Type'] = 'text/csv'
    resp.headers['Content-Disposition'] = 'attachment; filename=orders_export.csv'
    return resp


@orders_bp.route('/orders/print')
@admin_required
def print_orders():
    rows = Medicines.query.order_by(Medicines.id.desc()).all()
    return render_page('orders/orders_print.html', posts=rows,
                       generated_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))


# Compatibility alias
@orders_bp.route('/medicines-list')
@admin_required
def medicines_list_alias():
    return redirect('/orders')
