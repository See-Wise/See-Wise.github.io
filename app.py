from flask import Flask, request, jsonify, render_template, redirect, url_for, flash
from flask_cors import CORS
import database
import os

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change this in production
CORS(app)

# Initialize database on startup
database.init_database()

@app.route('/')
def index():
    """Home page - Inventory Overview"""
    products = database.get_all_products()
    locations = database.get_locations()
    return render_template('index.html', products=products, locations=locations)

@app.route('/products')
def products():
    """Products page"""
    all_products = database.get_all_products()
    locations = database.get_locations()
    return render_template('products.html', products=all_products, locations=locations)

@app.route('/add_product', methods=['GET', 'POST'])
def add_product():
    """Add new product"""
    if request.method == 'POST':
        try:
            name = request.form['name'].strip()
            price = float(request.form.get('price', 0))
            location = request.form['location'].strip()
            description = request.form.get('description', '').strip()
            
            if not name or not location:
                flash('Product name and location are required!', 'error')
                return redirect(url_for('add_product'))
            
            product_id = database.add_product(name, price, location, description)
            flash(f'Product "{name}" added successfully!', 'success')
            return redirect(url_for('index'))
            
        except ValueError:
            flash('Invalid price format!', 'error')
            return redirect(url_for('add_product'))
        except Exception as e:
            flash(f'Error adding product: {str(e)}', 'error')
            return redirect(url_for('add_product'))
    
    locations = database.get_locations()
    return render_template('add_product.html', locations=locations)

@app.route('/edit_product/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    """Edit existing product"""
    product = database.get_product_by_id(product_id)
    if not product:
        flash('Product not found!', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        try:
            name = request.form['name'].strip()
            price = float(request.form.get('price', 0))
            location = request.form['location'].strip()
            description = request.form.get('description', '').strip()
            
            if not name or not location:
                flash('Product name and location are required!', 'error')
                return render_template('edit_product.html', product=product, locations=database.get_locations())
            
            database.update_product(product_id, name, price, location, description)
            flash(f'Product "{name}" updated successfully!', 'success')
            return redirect(url_for('index'))
            
        except ValueError:
            flash('Invalid price format!', 'error')
            return render_template('edit_product.html', product=product, locations=database.get_locations())
        except Exception as e:
            flash(f'Error updating product: {str(e)}', 'error')
            return render_template('edit_product.html', product=product, locations=database.get_locations())
    
    locations = database.get_locations()
    return render_template('edit_product.html', product=product, locations=locations)

@app.route('/delete_product/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    """Delete product"""
    try:
        product = database.get_product_by_id(product_id)
        if product:
            database.delete_product(product_id)
            flash(f'Product "{product["name"]}" deleted successfully!', 'success')
        else:
            flash('Product not found!', 'error')
    except Exception as e:
        flash(f'Error deleting product: {str(e)}', 'error')
    
    return redirect(url_for('index'))

@app.route('/stock_in/<int:product_id>', methods=['GET', 'POST'])
def stock_in(product_id):
    """Stock in operation"""
    product = database.get_product_by_id(product_id)
    if not product:
        flash('Product not found!', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        try:
            quantity = float(request.form['quantity'])
            note = request.form.get('note', '').strip()
            
            if quantity <= 0:
                flash('Quantity must be greater than 0!', 'error')
                return render_template('stock_in.html', product=product)
            
            new_qty = database.update_stock(product_id, 'IN', quantity, note)
            flash(f'Stock in successful! New quantity: {new_qty}', 'success')
            return redirect(url_for('index'))
            
        except ValueError:
            flash('Invalid quantity format!', 'error')
            return render_template('stock_in.html', product=product)
        except Exception as e:
            flash(f'Error processing stock in: {str(e)}', 'error')
            return render_template('stock_in.html', product=product)
    
    return render_template('stock_in.html', product=product)

@app.route('/stock_out/<int:product_id>', methods=['GET', 'POST'])
def stock_out(product_id):
    """Stock out operation"""
    product = database.get_product_by_id(product_id)
    if not product:
        flash('Product not found!', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        try:
            quantity = float(request.form['quantity'])
            note = request.form.get('note', '').strip()
            
            if quantity <= 0:
                flash('Quantity must be greater than 0!', 'error')
                return render_template('stock_out.html', product=product)
            
            if quantity > product['quantity']:
                flash(f'Insufficient stock! Available: {product["quantity"]}', 'error')
                return render_template('stock_out.html', product=product)
            
            new_qty = database.update_stock(product_id, 'OUT', quantity, note)
            flash(f'Stock out successful! New quantity: {new_qty}', 'success')
            return redirect(url_for('index'))
            
        except ValueError:
            flash('Invalid quantity format!', 'error')
            return render_template('stock_out.html', product=product)
        except Exception as e:
            flash(f'Error processing stock out: {str(e)}', 'error')
            return render_template('stock_out.html', product=product)
    
    return render_template('stock_out.html', product=product)

@app.route('/transactions')
def transactions():
    """View transaction history"""
    product_id = request.args.get('product_id', type=int)
    limit = request.args.get('limit', 50, type=int)
    
    transactions = database.get_transactions(product_id, limit)
    products = database.get_all_products()
    
    return render_template('transactions.html', 
                         transactions=transactions, 
                         products=products, 
                         selected_product_id=product_id)

@app.route('/search')
def search():
    """Search products"""
    query = request.args.get('q', '').strip()
    location = request.args.get('location', '').strip()
    
    if query or location:
        products = database.search_products(query, location if location else None)
    else:
        products = database.get_all_products()
    
    locations = database.get_locations()
    return render_template('search.html', 
                         products=products, 
                         locations=locations,
                         query=query, 
                         selected_location=location)

# API Routes for mobile app integration
@app.route('/api/products', methods=['GET'])
def api_get_products():
    """API: Get all products"""
    products = database.get_all_products()
    return jsonify([dict(product) for product in products])

@app.route('/api/products', methods=['POST'])
def api_add_product():
    """API: Add new product"""
    try:
        data = request.get_json()
        product_id = database.add_product(
            data['name'], 
            data.get('price', 0), 
            data['location'], 
            data.get('description', '')
        )
        return jsonify({'success': True, 'product_id': product_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/products/<int:product_id>/stock', methods=['POST'])
def api_update_stock(product_id):
    """API: Update stock"""
    try:
        data = request.get_json()
        new_qty = database.update_stock(
            product_id, 
            data['type'], 
            data['quantity'], 
            data.get('note', '')
        )
        return jsonify({'success': True, 'new_quantity': new_qty})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/transactions', methods=['GET'])
def api_get_transactions():
    """API: Get transactions"""
    product_id = request.args.get('product_id', type=int)
    limit = request.args.get('limit', 50, type=int)
    
    transactions = database.get_transactions(product_id, limit)
    return jsonify([dict(trans) for trans in transactions])

@app.route('/api/search', methods=['GET'])
def api_search():
    """API: Search products"""
    query = request.args.get('q', '')
    location = request.args.get('location', '')
    
    products = database.search_products(query, location if location else None)
    return jsonify([dict(product) for product in products])

@app.errorhandler(404)
def not_found(error):
    return render_template('error.html', message="Page not found"), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html', message="Internal server error"), 500

if __name__ == '__main__':
    # Check if running in development
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    # Get host and port from environment or use defaults
    host = os.environ.get('HOST', '0.0.0.0')  # 0.0.0.0 allows access from other devices
    port = int(os.environ.get('PORT', 5000))
    
    print(f"Starting Mini Inventory Mobile on {host}:{port}")
    print(f"Access from mobile: http://YOUR_COMPUTER_IP:{port}")
    
    app.run(host=host, port=port, debug=debug)