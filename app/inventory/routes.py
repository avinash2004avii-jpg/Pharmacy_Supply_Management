import csv
import io
import logging
from flask import Blueprint, request, redirect, flash, make_response
from app import db
from app.models import Addmp, Addpd, Logs
from app.utils import render_page, admin_required

logger = logging.getLogger(__name__)
inventory_bp = Blueprint('inventory', __name__)


@inventory_bp.route('/search', methods=['GET', 'POST'])
@admin_required
def search():
    result = None
    search_term = ''
    if request.method == 'POST':
        search_term = request.form.get('search', '').strip()
        if search_term:
            med = Addmp.query.filter(Addmp.medicine.ilike(f'%{search_term}%')).first()
            prod = Addpd.query.filter(Addpd.product.ilike(f'%{search_term}%')).first()
            if med or prod:
                flash(f'"{search_term}" is available in inventory.', 'success')
                result = True
            else:
                flash(f'"{search_term}" was not found in inventory.', 'danger')
                result = False
    return render_page('inventory/search.html', result=result, search_term=search_term)


@inventory_bp.route('/addmp', methods=['POST'])
@admin_required
def addmp():
    name = request.form.get('medicine', '').strip()
    if name:
        if Addmp.query.filter(Addmp.medicine.ilike(name)).first():
            flash(f'Medicine "{name}" already exists.', 'info')
        else:
            db.session.add(Addmp(medicine=name))
            db.session.commit()
            flash(f'Medicine "{name}" added successfully.', 'success')
    return redirect('/search')


@inventory_bp.route('/addpd', methods=['POST'])
@admin_required
def addpd():
    name = request.form.get('product', '').strip()
    if name:
        if Addpd.query.filter(Addpd.product.ilike(name)).first():
            flash(f'Product "{name}" already exists.', 'info')
        else:
            db.session.add(Addpd(product=name))
            db.session.commit()
            flash(f'Product "{name}" added successfully.', 'success')
    return redirect('/search')


@inventory_bp.route('/delete-medicine/<int:sno>', methods=['POST'])
@admin_required
def delete_medicine(sno):
    item = Addmp.query.get_or_404(sno)
    name = item.medicine
    db.session.delete(item)
    db.session.commit()
    flash(f'Medicine "{name}" removed from catalog.', 'warning')
    return redirect('/items')


@inventory_bp.route('/delete-product/<int:sno>', methods=['POST'])
@admin_required
def delete_product(sno):
    item = Addpd.query.get_or_404(sno)
    name = item.product
    db.session.delete(item)
    db.session.commit()
    flash(f'Product "{name}" removed from catalog.', 'warning')
    return redirect('/items2')


@inventory_bp.route('/items')
@admin_required
def items():
    page = request.args.get('page', 1, type=int)
    q = request.args.get('q', '').strip()
    query = Addmp.query
    if q:
        query = query.filter(Addmp.medicine.ilike(f'%{q}%'))
    pagination = query.order_by(Addmp.medicine.asc()).paginate(page=page, per_page=20, error_out=False)
    return render_page('inventory/items.html', posts=pagination.items, pagination=pagination, search_q=q)


@inventory_bp.route('/items2')
@admin_required
def items2():
    page = request.args.get('page', 1, type=int)
    q = request.args.get('q', '').strip()
    query = Addpd.query
    if q:
        query = query.filter(Addpd.product.ilike(f'%{q}%'))
    pagination = query.order_by(Addpd.product.asc()).paginate(page=page, per_page=20, error_out=False)
    return render_page('inventory/items2.html', posts=pagination.items, pagination=pagination, search_q=q)


@inventory_bp.route('/logs')
@admin_required
def logs():
    page = request.args.get('page', 1, type=int)
    action_filter = request.args.get('action', '').strip()
    query = Logs.query
    if action_filter:
        query = query.filter(Logs.action.ilike(f'%{action_filter}%'))
    pagination = query.order_by(Logs.id.desc()).paginate(page=page, per_page=15, error_out=False)
    return render_page('inventory/details.html', posts=pagination.items,
                       pagination=pagination, action_filter=action_filter)


@inventory_bp.route('/logs/export/csv')
@admin_required
def export_logs_csv():
    rows = Logs.query.order_by(Logs.id.desc()).all()
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(['Log ID', 'Shop ID', 'Action', 'Date & Time'])
    for r in rows:
        w.writerow([r.id, r.mid, r.action, r.date])
    resp = make_response(buf.getvalue())
    resp.headers['Content-Type'] = 'text/csv'
    resp.headers['Content-Disposition'] = 'attachment; filename=audit_logs.csv'
    return resp


# Alias
@inventory_bp.route('/activity-logs')
@admin_required
def activity_logs_alias():
    return redirect('/logs')
