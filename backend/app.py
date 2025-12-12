#!/usr/bin/env python3
"""
Cloudnautic Shop - Backend API
E-commerce microservice with Flask
"""

import os
import logging
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
import secrets

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    'DATABASE_URL', 
    'sqlite:///cloudnautic.db'  # Use SQLite for local development
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', secrets.token_urlsafe(32))
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', secrets.token_urlsafe(32))

# Initialize extensions
db = SQLAlchemy(app)
jwt = JWTManager(app)
CORS(app)

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    stock_quantity = db.Column(db.Integer, default=0)
    category = db.Column(db.String(50))
    image_url = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'price': self.price,
            'stock_quantity': self.stock_quantity,
            'category': self.category,
            'image_url': self.image_url,
            'created_at': self.created_at.isoformat()
        }

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)

# Root route
@app.route('/')
def root():
    """Root endpoint with API information"""
    return jsonify({
        'service': 'Cloudnautic Shop Backend API',
        'version': '1.0.0',
        'status': 'running',
        'endpoints': {
            'health': '/health',
            'products': '/api/products',
            'categories': '/api/categories',
            'auth': {
                'register': '/api/auth/register',
                'login': '/api/auth/login'
            },
            'orders': '/api/orders'
        }
    }), 200

# Health check endpoint
@app.route('/health')
def health_check():
    """Health check endpoint for load balancer"""
    try:
        # Check database connection
        from sqlalchemy import text
        db.session.execute(text('SELECT 1'))
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'service': 'cloudnautic-backend'
        }), 200
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

# Authentication endpoints
@app.route('/api/auth/register', methods=['POST'])
def register():
    """Register a new user"""
    try:
        data = request.get_json()
        
        if User.query.filter_by(email=data['email']).first():
            return jsonify({'error': 'Email already exists'}), 400
        
        user = User(
            email=data['email'],
            name=data['name']
        )
        user.set_password(data['password'])
        
        db.session.add(user)
        db.session.commit()
        
        access_token = create_access_token(identity=user.id)
        
        return jsonify({
            'message': 'User registered successfully',
            'access_token': access_token,
            'user': {
                'id': user.id,
                'email': user.email,
                'name': user.name
            }
        }), 201
        
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        return jsonify({'error': 'Registration failed'}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Login user"""
    try:
        data = request.get_json()
        
        user = User.query.filter_by(email=data['email']).first()
        
        if user and user.check_password(data['password']):
            access_token = create_access_token(identity=user.id)
            return jsonify({
                'access_token': access_token,
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'name': user.name
                }
            }), 200
        
        return jsonify({'error': 'Invalid credentials'}), 401
        
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return jsonify({'error': 'Login failed'}), 500

# Product endpoints
@app.route('/api/products', methods=['GET'])
def get_products():
    """Get all products with optional filtering"""
    try:
        category = request.args.get('category')
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        
        query = Product.query
        
        if category:
            query = query.filter_by(category=category)
        
        products = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        return jsonify({
            'products': [product.to_dict() for product in products.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': products.total,
                'pages': products.pages
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Get products error: {str(e)}")
        return jsonify({'error': 'Failed to fetch products'}), 500

@app.route('/api/products/<int:product_id>', methods=['GET'])
def get_product(product_id):
    """Get a specific product by ID"""
    try:
        product = Product.query.get_or_404(product_id)
        return jsonify(product.to_dict()), 200
        
    except Exception as e:
        logger.error(f"Get product error: {str(e)}")
        return jsonify({'error': 'Product not found'}), 404

@app.route('/api/products', methods=['POST'])
@jwt_required()
def create_product():
    """Create a new product (admin only)"""
    try:
        data = request.get_json()
        
        product = Product(
            name=data['name'],
            description=data.get('description', ''),
            price=float(data['price']),
            stock_quantity=int(data.get('stock_quantity', 0)),
            category=data.get('category', ''),
            image_url=data.get('image_url', '')
        )
        
        db.session.add(product)
        db.session.commit()
        
        return jsonify(product.to_dict()), 201
        
    except Exception as e:
        logger.error(f"Create product error: {str(e)}")
        return jsonify({'error': 'Failed to create product'}), 500

# Order endpoints
@app.route('/api/orders', methods=['POST'])
@jwt_required()
def create_order():
    """Create a new order"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        order = Order(
            user_id=user_id,
            total_amount=0  # Will be calculated
        )
        
        db.session.add(order)
        db.session.flush()  # To get order ID
        
        total_amount = 0
        
        for item in data['items']:
            product = Product.query.get(item['product_id'])
            if not product or product.stock_quantity < item['quantity']:
                return jsonify({'error': f'Insufficient stock for product {product.name}'}), 400
            
            order_item = OrderItem(
                order_id=order.id,
                product_id=item['product_id'],
                quantity=item['quantity'],
                price=product.price
            )
            
            total_amount += product.price * item['quantity']
            product.stock_quantity -= item['quantity']
            
            db.session.add(order_item)
        
        order.total_amount = total_amount
        db.session.commit()
        
        return jsonify({
            'order_id': order.id,
            'total_amount': total_amount,
            'status': 'created'
        }), 201
        
    except Exception as e:
        logger.error(f"Create order error: {str(e)}")
        return jsonify({'error': 'Failed to create order'}), 500

@app.route('/api/orders', methods=['GET'])
@jwt_required()
def get_user_orders():
    """Get user's orders"""
    try:
        user_id = get_jwt_identity()
        orders = Order.query.filter_by(user_id=user_id).all()
        
        return jsonify([{
            'id': order.id,
            'total_amount': order.total_amount,
            'status': order.status,
            'created_at': order.created_at.isoformat()
        } for order in orders]), 200
        
    except Exception as e:
        logger.error(f"Get orders error: {str(e)}")
        return jsonify({'error': 'Failed to fetch orders'}), 500

# Categories endpoint
@app.route('/api/categories', methods=['GET'])
def get_categories():
    """Get all product categories"""
    try:
        categories = db.session.query(Product.category).distinct().all()
        return jsonify([cat[0] for cat in categories if cat[0]]), 200
        
    except Exception as e:
        logger.error(f"Get categories error: {str(e)}")
        return jsonify({'error': 'Failed to fetch categories'}), 500

# Initialize database and sample data
def init_db():
    """Initialize database with sample data"""
    db.create_all()
    
    # Check if we already have data
    if Product.query.first():
        return
    
    # Sample products
    sample_products = [
        Product(
            name="MacBook Pro 16\"",
            description="Apple MacBook Pro with M2 Pro chip",
            price=2499.99,
            stock_quantity=10,
            category="Electronics",
            image_url="https://via.placeholder.com/300x300?text=MacBook"
        ),
        Product(
            name="iPhone 15 Pro",
            description="Latest iPhone with titanium design",
            price=999.99,
            stock_quantity=25,
            category="Electronics",
            image_url="https://via.placeholder.com/300x300?text=iPhone"
        ),
        Product(
            name="Nike Air Max",
            description="Comfortable running shoes",
            price=129.99,
            stock_quantity=50,
            category="Shoes",
            image_url="https://via.placeholder.com/300x300?text=Nike"
        ),
        Product(
            name="Gaming Chair",
            description="Ergonomic gaming chair with RGB lighting",
            price=299.99,
            stock_quantity=15,
            category="Furniture",
            image_url="https://via.placeholder.com/300x300?text=Chair"
        ),
        Product(
            name="Wireless Headphones",
            description="Premium noise-cancelling headphones",
            price=199.99,
            stock_quantity=30,
            category="Electronics",
            image_url="https://via.placeholder.com/300x300?text=Headphones"
        )
    ]
    
    for product in sample_products:
        db.session.add(product)
    
    db.session.commit()
    logger.info("Database initialized with sample data")

if __name__ == '__main__':
    with app.app_context():
        init_db()
    
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=os.getenv('FLASK_ENV') == 'development')