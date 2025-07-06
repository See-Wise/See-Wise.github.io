# 📱 Mini Inventory Mobile

A mobile-responsive inventory management system designed for small businesses. Built with Flask and optimized for mobile devices.

## ✨ Features

### 📦 Product Management
- ➕ Add new products with name, price, location, and description
- ✏️ Edit existing product information
- 🗑️ Delete products (with confirmation)
- 📍 Storage location management

### 📊 Inventory Tracking
- 📈 Real-time stock level monitoring
- 🟢 Color-coded stock status (High/Medium/Low/Out of Stock)
- 📋 Inventory overview with summary statistics
- 🏪 Location-based product organization

### 📥📤 Stock Operations
- ➕ **Stock In**: Add inventory with notes
- ➖ **Stock Out**: Remove inventory with validation
- 🚀 Quick quantity buttons for fast operations
- 👀 Live preview of stock changes

### 🔍 Search & Filter
- 🔎 Search products by name or description
- 📍 Filter by storage location
- 🏃‍♂️ Quick location shortcuts
- 📱 Mobile-optimized search interface

### 📈 Transaction History
- ⏰ Complete audit trail of all stock movements
- 🔄 Filter by product or date range
- 📝 Notes and timestamps for each transaction
- 📊 Easy-to-read transaction cards on mobile

### 📱 Mobile-First Design
- 📱 Responsive design that works on all devices
- 🏠 Bottom navigation for mobile
- 🎨 Touch-friendly interface
- ⚡ PWA support (can be installed as an app)

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the Application

```bash
python app.py
```

### 3. Access the Application

- **Local**: http://localhost:5000
- **Mobile**: http://YOUR_COMPUTER_IP:5000 (replace with your actual IP)

## 🔧 Setup Instructions

### Prerequisites
- Python 3.7 or higher
- pip (Python package manager)

### Installation Steps

1. **Clone or download the project files**
   ```bash
   # If you have git
   git clone <repository-url>
   cd mini-inventory-mobile
   ```

2. **Install Python dependencies**
   ```bash
   pip install Flask Flask-CORS
   ```

3. **Initialize the database**
   ```bash
   python database.py
   ```

4. **Start the application**
   ```bash
   python app.py
   ```

### 📱 Mobile Access Setup

To access from your mobile device:

1. **Find your computer's IP address**
   - Windows: `ipconfig`
   - Mac/Linux: `ifconfig` or `ip addr show`

2. **Make sure your mobile device is on the same Wi-Fi network**

3. **Open your mobile browser and go to**
   ```
   http://YOUR_COMPUTER_IP:5000
   ```

4. **Optional: Install as PWA**
   - Most modern browsers will show an "Add to Home Screen" option
   - This creates an app-like experience

## 💾 Database Schema

The application uses SQLite with three main tables:

### Products Table
- `product_id`: Unique identifier
- `name`: Product name
- `price`: Unit price
- `location`: Storage location
- `description`: Optional description

### Inventory Table
- `product_id`: Links to products
- `quantity`: Current stock level
- `updated_at`: Last update timestamp

### Transactions Table
- `trans_id`: Unique transaction ID
- `product_id`: Links to products
- `type`: 'IN' or 'OUT'
- `quantity`: Amount moved
- `note`: Optional note
- `date`: Transaction timestamp

## 🎯 Usage Guide

### Adding Your First Product

1. Click **"Add Product"** button
2. Fill in:
   - **Product Name** (required)
   - **Price** (optional, defaults to $0)
   - **Storage Location** (required)
   - **Description** (optional)
3. Click **"Add Product"**

### Managing Stock

#### Stock In (Adding Inventory)
1. Click the **green "+"** button next to a product
2. Enter the quantity to add
3. Add an optional note (e.g., "Received from supplier")
4. Click **"Add Stock"**

#### Stock Out (Removing Inventory)
1. Click the **yellow "-"** button next to a product
2. Enter the quantity to remove
3. Add an optional note (e.g., "Sold to customer")
4. Click **"Remove Stock"**

### Searching Products

1. Go to the **Search** tab
2. Enter search terms in the search box
3. Filter by location if needed
4. Use quick location buttons for faster filtering

### Viewing Transaction History

1. Go to the **History** tab
2. Filter by specific products if needed
3. Adjust the number of records shown
4. Review all stock movements with timestamps

## 🌟 Advanced Features

### PWA Installation
The app can be installed on mobile devices as a Progressive Web App:
1. Open the app in your mobile browser
2. Look for "Add to Home Screen" in browser menu
3. Follow the prompts to install
4. Access like a native app from your home screen

### Quick Actions
- **Mobile FAB**: Floating action button for quick product addition
- **Quick Quantities**: Preset buttons for common stock amounts
- **Touch Feedback**: Visual feedback for mobile interactions

### Stock Status Indicators
- 🟢 **Green**: Stock > 50 units (Good)
- 🟡 **Yellow**: Stock 11-50 units (Medium)
- 🔴 **Red**: Stock 0-10 units (Low/Critical)

## 🔧 Configuration

### Environment Variables
- `FLASK_ENV`: Set to 'development' for debug mode
- `HOST`: Host address (default: 0.0.0.0)
- `PORT`: Port number (default: 5000)

### Customization
- Modify `static/manifest.json` for PWA settings
- Adjust stock level thresholds in templates
- Customize colors in `base.html` CSS variables

## 🐛 Troubleshooting

### Common Issues

**Can't access from mobile device:**
- Check that both devices are on the same network
- Verify the IP address is correct
- Make sure firewall isn't blocking the port

**Database errors:**
- Run `python database.py` to recreate the database
- Check file permissions in the project directory

**Form submission issues:**
- Ensure JavaScript is enabled in your browser
- Try refreshing the page

## 📋 API Endpoints

The application also provides REST API endpoints:

- `GET /api/products` - Get all products
- `POST /api/products` - Add new product
- `POST /api/products/<id>/stock` - Update stock
- `GET /api/transactions` - Get transaction history
- `GET /api/search` - Search products

## 🎨 Technology Stack

- **Backend**: Python Flask
- **Database**: SQLite
- **Frontend**: HTML5, CSS3, JavaScript
- **UI Framework**: Bootstrap 5
- **Icons**: Bootstrap Icons
- **PWA**: Web App Manifest

## 📄 License

This project is open source and available under the MIT License.

## 🤝 Contributing

Feel free to submit issues and enhancement requests!

---

**Happy Inventory Managing! 📦✨**
