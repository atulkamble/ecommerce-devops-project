#!/usr/bin/env python3
"""
Unit tests for Cloudnautic Shop Backend API
"""

import unittest
import json
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db, User, Product

class CloudnauticAPITest(unittest.TestCase):
    
    def setUp(self):
        """Set up test environment"""
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app = app.test_client()
        
        with app.app_context():
            db.create_all()
            self.create_test_data()
    
    def tearDown(self):
        """Clean up after tests"""
        with app.app_context():
            db.session.remove()
            db.drop_all()
    
    def create_test_data(self):
        """Create test data"""
        # Create test products
        product1 = Product(
            name="Test Laptop",
            description="Test laptop description",
            price=999.99,
            stock_quantity=10,
            category="Electronics"
        )
        product2 = Product(
            name="Test Phone",
            description="Test phone description",
            price=599.99,
            stock_quantity=5,
            category="Electronics"
        )
        
        db.session.add(product1)
        db.session.add(product2)
        db.session.commit()
    
    def test_health_check(self):
        """Test health check endpoint"""
        response = self.app.get('/health')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'healthy')
        self.assertEqual(data['service'], 'cloudnautic-backend')
    
    def test_get_products(self):
        """Test get products endpoint"""
        response = self.app.get('/api/products')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertIn('products', data)
        self.assertIn('pagination', data)
        self.assertEqual(len(data['products']), 2)
    
    def test_get_product_by_id(self):
        """Test get specific product endpoint"""
        response = self.app.get('/api/products/1')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data['name'], 'Test Laptop')
        self.assertEqual(data['price'], 999.99)
    
    def test_get_nonexistent_product(self):
        """Test get non-existent product"""
        response = self.app.get('/api/products/999')
        self.assertEqual(response.status_code, 404)
    
    def test_get_categories(self):
        """Test get categories endpoint"""
        response = self.app.get('/api/categories')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertIn('Electronics', data)
    
    def test_user_registration(self):
        """Test user registration"""
        user_data = {
            'name': 'Test User',
            'email': 'test@example.com',
            'password': 'testpass123'
        }
        
        response = self.app.post('/api/auth/register', 
                               data=json.dumps(user_data),
                               content_type='application/json')
        
        self.assertEqual(response.status_code, 201)
        
        data = json.loads(response.data)
        self.assertIn('access_token', data)
        self.assertEqual(data['user']['email'], 'test@example.com')
    
    def test_user_login(self):
        """Test user login"""
        # First register a user
        user_data = {
            'name': 'Test User',
            'email': 'test@example.com',
            'password': 'testpass123'
        }
        
        self.app.post('/api/auth/register', 
                     data=json.dumps(user_data),
                     content_type='application/json')
        
        # Then try to login
        login_data = {
            'email': 'test@example.com',
            'password': 'testpass123'
        }
        
        response = self.app.post('/api/auth/login',
                               data=json.dumps(login_data),
                               content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertIn('access_token', data)
    
    def test_invalid_login(self):
        """Test invalid login credentials"""
        login_data = {
            'email': 'nonexistent@example.com',
            'password': 'wrongpassword'
        }
        
        response = self.app.post('/api/auth/login',
                               data=json.dumps(login_data),
                               content_type='application/json')
        
        self.assertEqual(response.status_code, 401)
        
        data = json.loads(response.data)
        self.assertIn('error', data)

if __name__ == '__main__':
    # Run tests with coverage if available
    try:
        import coverage
        cov = coverage.Coverage()
        cov.start()
        
        unittest.main()
        
        cov.stop()
        cov.save()
        print("\nCoverage Report:")
        cov.report()
    except ImportError:
        unittest.main()