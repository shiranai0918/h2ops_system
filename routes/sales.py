from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_required, current_user
from models import Sale, SaleItem, Product, Customer, InventoryLog
from extensions import db

sales_bp = Blueprint('sales', __name__)


@sales_bp.route('/')
@login_required
def index():
    # Redirect root /sales to the order creation form
    return redirect(url_for('sales.create'))


@sales_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create(): 
    active_branch_id = session.get('active_branch_id')
    
    # Base queries for selection
    p_query = Product.query
    c_query = Customer.query
    
    if active_branch_id:
        p_query = p_query.filter(Product.branch_id == active_branch_id)
        c_query = c_query.filter(Customer.branch_id == active_branch_id)
        
    products = p_query.all()
    customers = c_query.all()
    
    if request.method == 'POST':
        customer_id = request.form.get('customer_id') or None
        payment_method = request.form.get('payment_method', 'Cash')
        
        # In a real app this would be a dynamic array of items from frontend
        # For simplicity, we process one primary ordered item from form
        product_id = request.form.get('product_id')
        quantity = int(request.form.get('quantity', 1))
        
        product = Product.query.get(product_id)
        if not product or product.current_stock < quantity:
            flash('Invalid product or insufficient stock.', 'danger')
            return redirect(url_for('sales.create'))
            
        subtotal = product.price * quantity
        
        # Create Sale
        sale = Sale(
            customer_id=customer_id,
            user_id=current_user.id,
            total_amount=subtotal,
            payment_method=payment_method,
            branch_id=active_branch_id or current_user.branch_id
        )
        db.session.add(sale)
        db.session.flush() # Get sale ID
        
        # Create Sale Item
        item = SaleItem(
            sale_id=sale.id,
            product_id=product.id,
            quantity=quantity,
            price=product.price,
            subtotal=subtotal
        )
        db.session.add(item)
        
        # Deduct Inventory
        product.current_stock -= quantity
        log = InventoryLog(
            product_id=product.id,
            change_amount=-quantity,
            log_type='OUT',
            reason=f'Sale #{sale.id}',
            branch_id=sale.branch_id
        )
        db.session.add(log)
        
        db.session.commit()
        flash('Sale recorded successfully.', 'success')
        return redirect(url_for('sales.create'))
        
    return render_template('sales/create.html', products=products, customers=customers)
