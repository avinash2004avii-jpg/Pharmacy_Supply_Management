import logging
from flask import Blueprint, request, redirect, flash
from app import db
from app.models import Posts, Medicines
from app.utils import render_page, admin_required, log_action, valid_phone

logger = logging.getLogger(__name__)
pharmacy_bp = Blueprint('pharmacy', __name__)


@pharmacy_bp.route('/dashboard')
@admin_required
def dashboard():
    from datetime import datetime
    from app.models import Addmp, CustomerOrder

    page = request.args.get('page', 1, type=int)
    search_q = request.args.get('q', '').strip()

    query = Posts.query
    if search_q:
        query = query.filter(
            Posts.medical_name.ilike(f'%{search_q}%') |
            Posts.owner_name.ilike(f'%{search_q}%') |
            Posts.address.ilike(f'%{search_q}%')
        )
    pagination = query.order_by(Posts.mid.asc()).paginate(page=page, per_page=10, error_out=False)

    all_orders = Medicines.query.all()
    total_pharmacies = Posts.query.count()
    total_orders = Medicines.query.count() + CustomerOrder.query.count()
    pending_orders = Medicines.query.filter_by(status='Pending').count()
    approved_orders = Medicines.query.filter_by(status='Approved').count()
    delivered_orders = Medicines.query.filter_by(status='Delivered').count()
    total_medicines = Addmp.query.count()

    orders_by_status = {'Pending': pending_orders, 'Approved': approved_orders, 'Delivered': delivered_orders}

    now = datetime.utcnow()
    monthly_keys = []
    for i in range(5, -1, -1):
        month = now.month - i
        year = now.year
        while month <= 0:
            month += 12
            year -= 1
        monthly_keys.append(f'{year}-{month:02d}')

    counts_map = {k: 0 for k in monthly_keys}
    for o in all_orders:
        if o.created_at:
            k = o.created_at.strftime('%Y-%m')
            if k in counts_map:
                counts_map[k] += 1

    monthly_labels = [datetime.strptime(k, '%Y-%m').strftime('%b %Y') for k in monthly_keys]
    monthly_counts = [counts_map[k] for k in monthly_keys]

    return render_page('pharmacy/dashboard.html',
                       posts=pagination.items,
                       pagination=pagination,
                       search_q=search_q,
                       total_pharmacies=total_pharmacies,
                       total_orders=total_orders,
                       pending_orders=pending_orders,
                       approved_orders=approved_orders,
                       delivered_orders=delivered_orders,
                       total_medicines=total_medicines,
                       orders_by_status=orders_by_status,
                       monthly_labels=monthly_labels,
                       monthly_counts=monthly_counts)


@pharmacy_bp.route('/insert', methods=['GET', 'POST'])
@admin_required
def insert():
    if request.method == 'POST':
        try:
            mid_value = request.form.get('mid', '').strip()
            medical_name = request.form.get('medical_name', '').strip()
            owner_name = request.form.get('owner_name', '').strip()
            phone_no = request.form.get('phone_no', '').strip()
            address = request.form.get('address', '').strip()

            if not all([mid_value, medical_name, owner_name, phone_no, address]):
                flash('All fields are required.', 'danger')
                return render_page('pharmacy/insert.html')

            if not mid_value.isdigit():
                flash('Pharmacy ID must be a number.', 'danger')
                return render_page('pharmacy/insert.html')

            if Posts.query.filter_by(mid=int(mid_value)).first():
                flash('Pharmacy ID already exists. Use a different ID.', 'danger')
                return render_page('pharmacy/insert.html')

            push = Posts(mid=int(mid_value), medical_name=medical_name,
                         owner_name=owner_name, phone_no=phone_no, address=address)
            db.session.add(push)
            db.session.commit()
            log_action(push.mid, 'PHARMACY_INSERTED')
            flash(f'Pharmacy "{medical_name}" registered successfully!', 'success')
            return redirect('/dashboard')
        except Exception as e:
            logger.error('Insert pharmacy error: %s', e)
            db.session.rollback()
            flash('Error registering pharmacy. Please try again.', 'danger')
    return render_page('pharmacy/insert.html')


@pharmacy_bp.route('/edit/<int:mid>', methods=['GET', 'POST'])
@admin_required
def edit(mid):
    post = Posts.query.filter_by(mid=mid).first_or_404()
    if request.method == 'POST':
        medical_name = request.form.get('medical_name', '').strip()
        owner_name = request.form.get('owner_name', '').strip()
        phone_no = request.form.get('phone_no', '').strip()
        address = request.form.get('address', '').strip()

        if not all([medical_name, owner_name, phone_no, address]):
            flash('All fields are required.', 'danger')
            return render_page('pharmacy/edit.html', post=post)

        post.medical_name = medical_name
        post.owner_name = owner_name
        post.phone_no = phone_no
        post.address = address
        db.session.commit()
        log_action(mid, 'PHARMACY_UPDATED')
        flash('Pharmacy updated successfully.', 'success')
        return redirect('/dashboard')
    return render_page('pharmacy/edit.html', post=post)


@pharmacy_bp.route('/delete/<int:mid>', methods=['POST'])
@admin_required
def delete(mid):
    post = Posts.query.filter_by(mid=mid).first_or_404()
    name = post.medical_name
    log_action(post.mid, 'PHARMACY_DELETED')
    db.session.delete(post)
    db.session.commit()
    flash(f'Pharmacy "{name}" deleted.', 'warning')
    return redirect('/dashboard')


# Compatibility aliases
@pharmacy_bp.route('/pharmacies')
@admin_required
def pharmacies_alias():
    return redirect('/dashboard')
