from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime, date
import os

app = Flask(__name__)
app.secret_key = 'swtchtech-secret-2024-xK9#mN'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///swtchtech.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ─── MODELS ───────────────────────────────────────────────────────────────────

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='sales')
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    description = db.Column(db.String(255))
    products = db.relationship('Product', backref='category', lazy=True)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    sku = db.Column(db.String(80), unique=True, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    description = db.Column(db.Text)
    cost_price = db.Column(db.Float, nullable=False, default=0)
    selling_price = db.Column(db.Float, nullable=False, default=0)
    quantity = db.Column(db.Integer, nullable=False, default=0)
    low_stock_threshold = db.Column(db.Integer, default=5)
    brand = db.Column(db.String(100))
    model = db.Column(db.String(100))
    active = db.Column(db.Boolean, default=True)
    deleted = db.Column(db.Boolean, default=False)          # soft-delete flag
    deleted_at = db.Column(db.DateTime)
    deleted_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    delete_reason = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def profit_margin(self):
        if self.cost_price > 0:
            return round(((self.selling_price - self.cost_price) / self.cost_price) * 100, 1)
        return 0

    @property
    def stock_status(self):
        if self.quantity == 0:
            return 'out'
        elif self.quantity <= self.low_stock_threshold:
            return 'low'
        return 'ok'

class Sale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(50), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref='sales')
    customer_name = db.Column(db.String(120), default='Walk-in Customer')
    customer_phone = db.Column(db.String(30))
    total_amount = db.Column(db.Float, nullable=False, default=0)
    payment_method = db.Column(db.String(30), default='cash')
    notes = db.Column(db.Text)
    status = db.Column(db.String(20), default='completed')  # completed / returned
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    items = db.relationship('SaleItem', backref='sale', lazy=True, cascade='all, delete-orphan')

class SaleItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey('sale.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    product = db.relationship('Product')
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    subtotal = db.Column(db.Float, nullable=False)
    returned = db.Column(db.Boolean, default=False)
    returned_qty = db.Column(db.Integer, default=0)

class StockMovement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    product = db.relationship('Product')
    movement_type = db.Column(db.String(20), nullable=False)  # in / out / adjustment / return / restock
    quantity = db.Column(db.Integer, nullable=False)
    reference = db.Column(db.String(100))
    notes = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ReturnRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey('sale.id'), nullable=False)
    sale = db.relationship('Sale')
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    product = db.relationship('Product')
    quantity = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.String(255))
    restock = db.Column(db.Boolean, default=False)
    processed_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    processor = db.relationship('User')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ─── DECORATORS ───────────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        if session.get('role') != 'admin':
            flash('Access denied. Admins only.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated

# ─── AUTH ─────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return redirect(url_for('dashboard') if 'user_id' in session else url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form.get('username','').strip(), active=True).first()
        if user and check_password_hash(user.password_hash, request.form.get('password','')):
            session.update({'user_id': user.id, 'username': user.username, 'role': user.role, 'full_name': user.full_name})
            flash(f'Welcome back, {user.full_name}!', 'success')
            return redirect(url_for('dashboard'))
        flash('Invalid username or password.', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# ─── DASHBOARD ────────────────────────────────────────────────────────────────

@app.route('/dashboard')
@login_required
def dashboard():
    today = date.today()
    today_start = datetime.combine(today, datetime.min.time())
    today_sales = Sale.query.filter(Sale.created_at >= today_start, Sale.status == 'completed').all()
    today_revenue = sum(s.total_amount for s in today_sales)
    total_products = Product.query.filter_by(active=True, deleted=False).count()
    low_stock = Product.query.filter(Product.quantity <= Product.low_stock_threshold, Product.quantity > 0, Product.active == True, Product.deleted == False).count()
    out_of_stock = Product.query.filter_by(quantity=0, active=True, deleted=False).count()
    total_revenue = db.session.query(db.func.sum(Sale.total_amount)).filter_by(status='completed').scalar() or 0
    total_sales = Sale.query.filter_by(status='completed').count()
    recent_sales = Sale.query.order_by(Sale.created_at.desc()).limit(5).all()
    low_stock_products = Product.query.filter(Product.quantity <= Product.low_stock_threshold, Product.active == True, Product.deleted == False).order_by(Product.quantity.asc()).limit(5).all()
    deleted_count = Product.query.filter_by(deleted=True).count()
    return render_template('dashboard.html', today_revenue=today_revenue, today_count=len(today_sales),
        total_products=total_products, low_stock=low_stock, out_of_stock=out_of_stock,
        total_revenue=total_revenue, total_sales=total_sales, recent_sales=recent_sales,
        low_stock_products=low_stock_products, deleted_count=deleted_count)

# ─── INVENTORY ────────────────────────────────────────────────────────────────

@app.route('/inventory')
@login_required
def inventory():
    search = request.args.get('search', '')
    category_id = request.args.get('category', '')
    status = request.args.get('status', '')
    q = Product.query.filter_by(active=True, deleted=False)
    if search:
        q = q.filter(db.or_(Product.name.ilike(f'%{search}%'), Product.sku.ilike(f'%{search}%'), Product.brand.ilike(f'%{search}%')))
    if category_id:
        q = q.filter_by(category_id=int(category_id))
    if status == 'low':
        q = q.filter(Product.quantity <= Product.low_stock_threshold, Product.quantity > 0)
    elif status == 'out':
        q = q.filter_by(quantity=0)
    products = q.order_by(Product.name).all()
    categories = Category.query.all()
    return render_template('inventory.html', products=products, categories=categories, search=search, selected_category=category_id, selected_status=status)

@app.route('/inventory/add', methods=['GET', 'POST'])
@login_required
def add_product():
    if request.method == 'POST':
        sku = request.form.get('sku', '').strip()
        # Allow restoring a deleted product with same SKU
        existing = Product.query.filter_by(sku=sku).first()
        if existing and not existing.deleted:
            flash('SKU already exists.', 'error')
            return redirect(url_for('add_product'))
        if existing and existing.deleted:
            flash('A deleted product has this SKU. Please use a different SKU or restore the deleted product.', 'error')
            return redirect(url_for('add_product'))
        p = Product(
            name=request.form.get('name'), sku=sku,
            category_id=int(request.form.get('category_id')),
            description=request.form.get('description'),
            cost_price=float(request.form.get('cost_price', 0)),
            selling_price=float(request.form.get('selling_price', 0)),
            quantity=int(request.form.get('quantity', 0)),
            low_stock_threshold=int(request.form.get('low_stock_threshold', 5)),
            brand=request.form.get('brand'), model=request.form.get('model')
        )
        db.session.add(p)
        db.session.flush()
        if p.quantity > 0:
            db.session.add(StockMovement(product_id=p.id, movement_type='in', quantity=p.quantity, reference='Initial Stock', user_id=session['user_id']))
        db.session.commit()
        flash(f'Product "{p.name}" added!', 'success')
        return redirect(url_for('inventory'))
    categories = Category.query.all()
    return render_template('product_form.html', product=None, categories=categories, action='Add')

@app.route('/inventory/edit/<int:pid>', methods=['GET', 'POST'])
@login_required
def edit_product(pid):
    p = Product.query.get_or_404(pid)
    if p.deleted:
        flash('Cannot edit a deleted product.', 'error')
        return redirect(url_for('inventory'))
    if request.method == 'POST':
        old_qty = p.quantity
        p.name = request.form.get('name')
        p.category_id = int(request.form.get('category_id'))
        p.description = request.form.get('description')
        p.cost_price = float(request.form.get('cost_price', 0))
        p.selling_price = float(request.form.get('selling_price', 0))
        new_qty = int(request.form.get('quantity', 0))
        p.low_stock_threshold = int(request.form.get('low_stock_threshold', 5))
        p.brand = request.form.get('brand')
        p.model = request.form.get('model')
        p.updated_at = datetime.utcnow()
        if new_qty != old_qty:
            diff = new_qty - old_qty
            db.session.add(StockMovement(product_id=p.id, movement_type='adjustment', quantity=abs(diff),
                reference='Manual Adjustment', notes=f'Qty changed from {old_qty} to {new_qty}', user_id=session['user_id']))
            p.quantity = new_qty
        db.session.commit()
        flash('Product updated!', 'success')
        return redirect(url_for('inventory'))
    categories = Category.query.all()
    return render_template('product_form.html', product=p, categories=categories, action='Edit')

# ── HARD DELETE (admin only, product must have been returned/has 0 qty) ───────
@app.route('/inventory/delete/<int:pid>', methods=['POST'])
@admin_required
def delete_product(pid):
    p = Product.query.get_or_404(pid)
    reason = request.form.get('reason', '').strip()
    # Soft-delete: mark as deleted, keep record
    p.deleted = True
    p.active = False
    p.deleted_at = datetime.utcnow()
    p.deleted_by = session['user_id']
    p.delete_reason = reason or 'Removed by admin'
    db.session.commit()
    flash(f'Product "{p.name}" has been deleted. You can restock/restore it from the Deleted Products page.', 'success')
    return redirect(url_for('inventory'))

# ── DELETED PRODUCTS (admin only) ─────────────────────────────────────────────
@app.route('/inventory/deleted')
@admin_required
def deleted_products():
    products = Product.query.filter_by(deleted=True).order_by(Product.deleted_at.desc()).all()
    return render_template('deleted_products.html', products=products)

# ── RESTOCK DELETED PRODUCT (admin only) ──────────────────────────────────────
@app.route('/inventory/restock/<int:pid>', methods=['POST'])
@admin_required
def restock_deleted(pid):
    p = Product.query.get_or_404(pid)
    if not p.deleted:
        flash('Product is not deleted.', 'error')
        return redirect(url_for('inventory'))
    qty = int(request.form.get('quantity', 0))
    new_price = request.form.get('selling_price', '').strip()
    new_cost  = request.form.get('cost_price', '').strip()
    # Restore product
    p.deleted = False
    p.active = True
    p.deleted_at = None
    p.deleted_by = None
    p.delete_reason = None
    p.quantity = qty
    if new_price:
        p.selling_price = float(new_price)
    if new_cost:
        p.cost_price = float(new_cost)
    p.updated_at = datetime.utcnow()
    if qty > 0:
        db.session.add(StockMovement(product_id=p.id, movement_type='restock', quantity=qty,
            reference='Restock after restore', notes='Admin restocked deleted product', user_id=session['user_id']))
    db.session.commit()
    flash(f'"{p.name}" restored and restocked with {qty} units!', 'success')
    return redirect(url_for('deleted_products'))

# ── PERMANENT DELETE (admin only) ─────────────────────────────────────────────
@app.route('/inventory/permanent-delete/<int:pid>', methods=['POST'])
@admin_required
def permanent_delete(pid):
    p = Product.query.get_or_404(pid)
    if not p.deleted:
        flash('Only soft-deleted products can be permanently deleted.', 'error')
        return redirect(url_for('deleted_products'))
    name = p.name
    # Remove stock movements first
    StockMovement.query.filter_by(product_id=p.id).delete()
    db.session.delete(p)
    db.session.commit()
    flash(f'"{name}" has been permanently deleted from the system.', 'success')
    return redirect(url_for('deleted_products'))

@app.route('/inventory/stock/<int:pid>', methods=['POST'])
@login_required
def update_stock(pid):
    p = Product.query.get_or_404(pid)
    qty = int(request.form.get('quantity', 0))
    move_type = request.form.get('type', 'in')
    notes = request.form.get('notes', '')
    if move_type == 'in':
        p.quantity += qty
    elif move_type == 'out':
        if qty > p.quantity:
            flash('Insufficient stock!', 'error')
            return redirect(url_for('inventory'))
        p.quantity -= qty
    db.session.add(StockMovement(product_id=p.id, movement_type=move_type, quantity=qty, reference='Manual Stock Update', notes=notes, user_id=session['user_id']))
    db.session.commit()
    flash('Stock updated!', 'success')
    return redirect(url_for('inventory'))

# ─── SALES ────────────────────────────────────────────────────────────────────

@app.route('/sales')
@login_required
def sales():
    sales_list = Sale.query.order_by(Sale.created_at.desc()).all()
    return render_template('sales.html', sales=sales_list)

@app.route('/sales/new', methods=['GET', 'POST'])
@login_required
def new_sale():
    if request.method == 'POST':
        data = request.get_json()
        if not data or not data.get('items'):
            return jsonify({'success': False, 'error': 'No items'}), 400
        inv_num = f"INV-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        sale = Sale(invoice_number=inv_num, user_id=session['user_id'],
            customer_name=data.get('customer_name', 'Walk-in Customer'),
            customer_phone=data.get('customer_phone', ''),
            payment_method=data.get('payment_method', 'cash'),
            notes=data.get('notes', ''))
        db.session.add(sale)
        db.session.flush()
        total = 0
        for item in data['items']:
            product = Product.query.get(item['product_id'])
            if not product or product.quantity < item['quantity']:
                db.session.rollback()
                return jsonify({'success': False, 'error': f'Insufficient stock for {product.name if product else "unknown"}'}), 400
            subtotal = item['quantity'] * item['unit_price']
            db.session.add(SaleItem(sale_id=sale.id, product_id=product.id, quantity=item['quantity'], unit_price=item['unit_price'], subtotal=subtotal))
            product.quantity -= item['quantity']
            db.session.add(StockMovement(product_id=product.id, movement_type='out', quantity=item['quantity'], reference=inv_num, user_id=session['user_id']))
            total += subtotal
        sale.total_amount = total
        db.session.commit()
        return jsonify({'success': True, 'invoice': inv_num, 'total': total, 'sale_id': sale.id})
    products = Product.query.filter(Product.active == True, Product.deleted == False, Product.quantity > 0).all()
    return render_template('new_sale.html', products=products)

@app.route('/sales/<int:sid>')
@login_required
def view_sale(sid):
    sale = Sale.query.get_or_404(sid)
    return render_template('view_sale.html', sale=sale)

# ── PROCESS RETURN ─────────────────────────────────────────────────────────────
@app.route('/sales/<int:sid>/return', methods=['GET', 'POST'])
@login_required
def process_return(sid):
    sale = Sale.query.get_or_404(sid)
    if request.method == 'POST':
        data = request.get_json()
        items = data.get('items', [])
        if not items:
            return jsonify({'success': False, 'error': 'No items selected for return'})
        restock = data.get('restock', False)
        # Only admin can restock
        if restock and session.get('role') != 'admin':
            return jsonify({'success': False, 'error': 'Only admins can restock returned items'})
        for item in items:
            si = SaleItem.query.get(item['sale_item_id'])
            if not si or si.sale_id != sale.id:
                continue
            qty = int(item['quantity'])
            if qty <= 0 or qty > (si.quantity - si.returned_qty):
                continue
            si.returned_qty += qty
            if si.returned_qty >= si.quantity:
                si.returned = True
            rr = ReturnRecord(sale_id=sale.id, product_id=si.product_id, quantity=qty,
                reason=data.get('reason', ''), restock=restock, processed_by=session['user_id'])
            db.session.add(rr)
            if restock:
                si.product.quantity += qty
                db.session.add(StockMovement(product_id=si.product_id, movement_type='return', quantity=qty,
                    reference=sale.invoice_number, notes=f'Returned & restocked. Reason: {data.get("reason","")}', user_id=session['user_id']))
        # Mark sale as returned if all items returned
        all_returned = all(i.returned for i in sale.items)
        if all_returned:
            sale.status = 'returned'
        db.session.commit()
        return jsonify({'success': True})
    returns = ReturnRecord.query.filter_by(sale_id=sid).all()
    return render_template('process_return.html', sale=sale, returns=returns)

# ─── CATEGORIES ───────────────────────────────────────────────────────────────

@app.route('/categories')
@admin_required
def categories():
    return render_template('categories.html', categories=Category.query.all())

@app.route('/categories/add', methods=['POST'])
@admin_required
def add_category():
    name = request.form.get('name', '').strip()
    if not name:
        flash('Name required.', 'error')
        return redirect(url_for('categories'))
    if Category.query.filter_by(name=name).first():
        flash('Category already exists.', 'error')
        return redirect(url_for('categories'))
    db.session.add(Category(name=name, description=request.form.get('description','')))
    db.session.commit()
    flash(f'Category "{name}" added!', 'success')
    return redirect(url_for('categories'))

@app.route('/categories/delete/<int:cid>', methods=['POST'])
@admin_required
def delete_category(cid):
    c = Category.query.get_or_404(cid)
    if c.products:
        flash('Cannot delete category with products.', 'error')
    else:
        db.session.delete(c)
        db.session.commit()
        flash('Category deleted.', 'success')
    return redirect(url_for('categories'))

# ─── USERS ────────────────────────────────────────────────────────────────────

@app.route('/users')
@admin_required
def users():
    return render_template('users.html', users=User.query.all())

@app.route('/users/add', methods=['GET', 'POST'])
@admin_required
def add_user():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        if User.query.filter_by(username=username).first():
            flash('Username taken.', 'error')
            return redirect(url_for('add_user'))
        db.session.add(User(username=username, password_hash=generate_password_hash(request.form.get('password')),
            role=request.form.get('role','sales'), full_name=request.form.get('full_name'), email=request.form.get('email')))
        db.session.commit()
        flash('User created!', 'success')
        return redirect(url_for('users'))
    return render_template('user_form.html', user=None)

@app.route('/users/edit/<int:uid>', methods=['GET', 'POST'])
@admin_required
def edit_user(uid):
    u = User.query.get_or_404(uid)
    if request.method == 'POST':
        u.full_name = request.form.get('full_name')
        u.email = request.form.get('email')
        u.role = request.form.get('role','sales')
        u.active = 'active' in request.form
        pw = request.form.get('password','').strip()
        if pw:
            u.password_hash = generate_password_hash(pw)
        db.session.commit()
        flash('User updated!', 'success')
        return redirect(url_for('users'))
    return render_template('user_form.html', user=u)

@app.route('/users/delete/<int:uid>', methods=['POST'])
@admin_required
def delete_user(uid):
    if uid == session['user_id']:
        flash("You can't delete yourself.", 'error')
        return redirect(url_for('users'))
    u = User.query.get_or_404(uid)
    u.active = False
    db.session.commit()
    flash(f'User "{u.username}" deactivated.', 'success')
    return redirect(url_for('users'))

# ─── REPORTS ──────────────────────────────────────────────────────────────────

@app.route('/reports')
@admin_required
def reports():
    from sqlalchemy import func
    sales_data = db.session.query(func.date(Sale.created_at).label('day'), func.sum(Sale.total_amount).label('total'), func.count(Sale.id).label('count')).filter_by(status='completed').group_by(func.date(Sale.created_at)).order_by(func.date(Sale.created_at).desc()).limit(30).all()
    top_products = db.session.query(Product.name, func.sum(SaleItem.quantity).label('sold'), func.sum(SaleItem.subtotal).label('revenue')).join(SaleItem, Product.id == SaleItem.product_id).group_by(Product.id).order_by(func.sum(SaleItem.subtotal).desc()).limit(10).all()
    total_revenue = db.session.query(func.sum(Sale.total_amount)).filter_by(status='completed').scalar() or 0
    total_sales = Sale.query.filter_by(status='completed').count()
    return_count = ReturnRecord.query.count()
    return render_template('reports.html', sales_data=sales_data, top_products=top_products, total_revenue=total_revenue, total_sales=total_sales, return_count=return_count)

@app.route('/stock-history')
@login_required
def stock_history():
    movements = StockMovement.query.order_by(StockMovement.created_at.desc()).limit(100).all()
    return render_template('stock_history.html', movements=movements)

# ─── API ──────────────────────────────────────────────────────────────────────

@app.route('/api/products')
@login_required
def api_products():
    products = Product.query.filter(Product.active == True, Product.deleted == False, Product.quantity > 0).all()
    return jsonify([{'id': p.id, 'name': p.name, 'sku': p.sku, 'selling_price': p.selling_price, 'quantity': p.quantity, 'brand': p.brand or '', 'category': p.category.name} for p in products])

# ─── INIT ─────────────────────────────────────────────────────────────────────

def init_db():
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username='admin').first():
            db.session.add(User(username='admin', password_hash=generate_password_hash('admin123'), role='admin', full_name='System Administrator', email='admin@swtchtech.com'))
        if not User.query.filter_by(username='sales1').first():
            db.session.add(User(username='sales1', password_hash=generate_password_hash('sales123'), role='sales', full_name='Sales Staff', email='sales@swtchtech.com'))
        for cat in ['Laptops','Smartphones','Tablets','Accessories','Cables & Chargers','Storage','Audio']:
            if not Category.query.filter_by(name=cat).first():
                db.session.add(Category(name=cat))
        db.session.commit()
        print("DB ready. admin/admin123 | sales1/sales123")

if __name__ == '__main__':
    init_db()
    app.run(debug=False, host='0.0.0.0', port=5000)
