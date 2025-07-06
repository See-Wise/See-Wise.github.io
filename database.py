import sqlite3
import os
from datetime import datetime

DATABASE_NAME = 'inventory.db'

def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    """Initialize database with required tables"""
    conn = get_db_connection()
    
    # Create products table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS products (
            product_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL DEFAULT 0.0,
            location TEXT NOT NULL,
            description TEXT
        )
    ''')
    
    # Create inventory table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS inventory (
            product_id INTEGER PRIMARY KEY,
            quantity REAL DEFAULT 0.0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products (product_id)
        )
    ''')
    
    # Create transactions table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            trans_id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            type TEXT NOT NULL CHECK (type IN ('IN', 'OUT')),
            quantity REAL NOT NULL,
            note TEXT,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products (product_id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("Database initialized successfully!")

def add_product(name, price, location, description=""):
    """Add a new product"""
    conn = get_db_connection()
    cursor = conn.execute(
        'INSERT INTO products (name, price, location, description) VALUES (?, ?, ?, ?)',
        (name, price, location, description)
    )
    product_id = cursor.lastrowid
    
    # Initialize inventory for new product
    conn.execute(
        'INSERT INTO inventory (product_id, quantity) VALUES (?, 0.0)',
        (product_id,)
    )
    
    conn.commit()
    conn.close()
    return product_id

def get_all_products():
    """Get all products with their current inventory"""
    conn = get_db_connection()
    products = conn.execute('''
        SELECT p.product_id, p.name, p.price, p.location, p.description, 
               COALESCE(i.quantity, 0) as quantity,
               i.updated_at
        FROM products p
        LEFT JOIN inventory i ON p.product_id = i.product_id
        ORDER BY p.name
    ''').fetchall()
    conn.close()
    return products

def get_product_by_id(product_id):
    """Get a specific product by ID"""
    conn = get_db_connection()
    product = conn.execute('''
        SELECT p.product_id, p.name, p.price, p.location, p.description, 
               COALESCE(i.quantity, 0) as quantity
        FROM products p
        LEFT JOIN inventory i ON p.product_id = i.product_id
        WHERE p.product_id = ?
    ''', (product_id,)).fetchone()
    conn.close()
    return product

def update_stock(product_id, transaction_type, quantity, note=""):
    """Update stock with a transaction"""
    conn = get_db_connection()
    
    # Get current quantity
    current = conn.execute(
        'SELECT quantity FROM inventory WHERE product_id = ?', 
        (product_id,)
    ).fetchone()
    
    if current is None:
        # Initialize if doesn't exist
        conn.execute(
            'INSERT INTO inventory (product_id, quantity) VALUES (?, 0.0)',
            (product_id,)
        )
        current_qty = 0.0
    else:
        current_qty = current['quantity']
    
    # Calculate new quantity
    if transaction_type == 'IN':
        new_qty = current_qty + quantity
    else:  # OUT
        new_qty = max(0, current_qty - quantity)  # Prevent negative stock
    
    # Update inventory
    conn.execute(
        'UPDATE inventory SET quantity = ?, updated_at = CURRENT_TIMESTAMP WHERE product_id = ?',
        (new_qty, product_id)
    )
    
    # Record transaction
    conn.execute(
        'INSERT INTO transactions (product_id, type, quantity, note) VALUES (?, ?, ?, ?)',
        (product_id, transaction_type, quantity, note)
    )
    
    conn.commit()
    conn.close()
    return new_qty

def get_transactions(product_id=None, limit=50):
    """Get transaction history"""
    conn = get_db_connection()
    
    if product_id:
        transactions = conn.execute('''
            SELECT t.trans_id, t.product_id, p.name as product_name, 
                   t.type, t.quantity, t.note, t.date
            FROM transactions t
            JOIN products p ON t.product_id = p.product_id
            WHERE t.product_id = ?
            ORDER BY t.date DESC
            LIMIT ?
        ''', (product_id, limit)).fetchall()
    else:
        transactions = conn.execute('''
            SELECT t.trans_id, t.product_id, p.name as product_name, 
                   t.type, t.quantity, t.note, t.date
            FROM transactions t
            JOIN products p ON t.product_id = p.product_id
            ORDER BY t.date DESC
            LIMIT ?
        ''', (limit,)).fetchall()
    
    conn.close()
    return transactions

def search_products(query, location=None):
    """Search products by name or location"""
    conn = get_db_connection()
    
    if location:
        products = conn.execute('''
            SELECT p.product_id, p.name, p.price, p.location, p.description, 
                   COALESCE(i.quantity, 0) as quantity
            FROM products p
            LEFT JOIN inventory i ON p.product_id = i.product_id
            WHERE (p.name LIKE ? OR p.description LIKE ?) AND p.location LIKE ?
            ORDER BY p.name
        ''', (f'%{query}%', f'%{query}%', f'%{location}%')).fetchall()
    else:
        products = conn.execute('''
            SELECT p.product_id, p.name, p.price, p.location, p.description, 
                   COALESCE(i.quantity, 0) as quantity
            FROM products p
            LEFT JOIN inventory i ON p.product_id = i.product_id
            WHERE p.name LIKE ? OR p.description LIKE ? OR p.location LIKE ?
            ORDER BY p.name
        ''', (f'%{query}%', f'%{query}%', f'%{query}%')).fetchall()
    
    conn.close()
    return products

def delete_product(product_id):
    """Delete a product and its related data"""
    conn = get_db_connection()
    
    # Delete transactions first (foreign key constraint)
    conn.execute('DELETE FROM transactions WHERE product_id = ?', (product_id,))
    
    # Delete inventory
    conn.execute('DELETE FROM inventory WHERE product_id = ?', (product_id,))
    
    # Delete product
    conn.execute('DELETE FROM products WHERE product_id = ?', (product_id,))
    
    conn.commit()
    conn.close()

def update_product(product_id, name, price, location, description=""):
    """Update product information"""
    conn = get_db_connection()
    conn.execute(
        'UPDATE products SET name = ?, price = ?, location = ?, description = ? WHERE product_id = ?',
        (name, price, location, description, product_id)
    )
    conn.commit()
    conn.close()

def get_locations():
    """Get all unique storage locations"""
    conn = get_db_connection()
    locations = conn.execute(
        'SELECT DISTINCT location FROM products ORDER BY location'
    ).fetchall()
    conn.close()
    return [loc['location'] for loc in locations]

if __name__ == '__main__':
    init_database()