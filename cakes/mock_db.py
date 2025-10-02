# Mock Database for Development (No MongoDB Required)
# This allows the application to run without MongoDB for testing

from datetime import datetime, timedelta

class MockCollection:
    def __init__(self, name):
        self.name = name
        self.data = []
    
    def find(self, query=None):
        if query is None:
            query = {}
        return MockCursor(self.data, query)
    
    def find_one(self, query):
        if query is None:
            query = {}
        for item in self.data:
            if self._matches_query(item, query):
                return item
        return None
    
    def insert_one(self, document):
        document['_id'] = f"mock_{len(self.data) + 1}"
        self.data.append(document)
        return MockResult(document['_id'])
    
    def update_one(self, query, update):
        for i, item in enumerate(self.data):
            if self._matches_query(item, query):
                if '$set' in update:
                    self.data[i].update(update['$set'])
                return MockResult(item.get('_id'))
        return MockResult(None)
    
    def delete_one(self, query):
        for i, item in enumerate(self.data):
            if self._matches_query(item, query):
                del self.data[i]
                return MockResult(item.get('_id'))
        return MockResult(None)
    
    def delete_many(self, query):
        count = 0
        for i in range(len(self.data) - 1, -1, -1):
            if self._matches_query(self.data[i], query):
                del self.data[i]
                count += 1
        return MockResult(count)
    
    def count_documents(self, query=None):
        if query is None:
            query = {}
        count = 0
        for item in self.data:
            if self._matches_query(item, query):
                count += 1
        return count
    
    def distinct(self, field):
        values = set()
        for item in self.data:
            if field in item:
                values.add(item[field])
        return list(values)
    
    def aggregate(self, pipeline):
        # Simple aggregation for basic operations
        if pipeline and '$group' in pipeline[0]:
            group_op = pipeline[0]['$group']
            if group_op.get('_id') is None and 'total_sales' in group_op:
                total = sum(item.get('total_amount', 0) for item in self.data)
                return [{'total_sales': total}]
        return []
    
    def _matches_query(self, item, query):
        for key, value in query.items():
            if key == '_id':
                if item.get('_id') != value:
                    return False
            elif key == '$ne':
                if item.get('_id') == value:
                    return False
            elif isinstance(value, dict) and '$regex' in value:
                import re
                pattern = value['$regex']
                flags = 0
                if value.get('$options') == 'i':
                    flags = re.IGNORECASE
                if not re.search(pattern, str(item.get(key, '')), flags):
                    return False
            elif item.get(key) != value:
                return False
        return True

class MockCursor:
    def __init__(self, data, query):
        self.data = data
        self.query = query
        self.filtered_data = [item for item in data if self._matches_query(item, query)]
        self.index = 0
        self.limit_val = None
        self.skip_val = 0
        self.sort_val = None
    
    def sort(self, field, direction):
        self.sort_val = (field, direction)
        return self
    
    def limit(self, n):
        self.limit_val = n
        return self
    
    def skip(self, n):
        self.skip_val = n
        return self
    
    def __iter__(self):
        return self
    
    def __next__(self):
        if self.index >= len(self.filtered_data):
            raise StopIteration
        
        item = self.filtered_data[self.index]
        self.index += 1
        return item
    
    def __list__(self):
        return list(self)
    
    def _matches_query(self, item, query):
        for key, value in query.items():
            if key == '_id':
                if item.get('_id') != value:
                    return False
            elif key == '$ne':
                if item.get('_id') == value:
                    return False
            elif isinstance(value, dict) and '$regex' in value:
                import re
                pattern = value['$regex']
                flags = 0
                if value.get('$options') == 'i':
                    flags = re.IGNORECASE
                if not re.search(pattern, str(item.get(key, '')), flags):
                    return False
            elif item.get(key) != value:
                return False
        return True

class MockResult:
    def __init__(self, inserted_id):
        self.inserted_id = inserted_id

class MockDatabase:
    def __init__(self):
        self.collections = {}
    
    def __getattr__(self, name):
        if name not in self.collections:
            self.collections[name] = MockCollection(name)
        return self.collections[name]

# Initialize mock database with sample data
def init_mock_db():
    db = MockDatabase()
    
    # Sample cakes data with your original categories and real images
    sample_cakes = [
        {
            '_id': 'cake_1',
            'name': 'Chocolate Delight',
            'price': 45000,
            'description': 'Rich chocolate cake with creamy frosting and chocolate shavings. Perfect for chocolate lovers who want an indulgent treat.',
            'category': 'chocolate cakes',
            'image': '/static/cake_uploads/ChocolateCake.jpg',
            'ingredients': ['Flour', 'Cocoa powder', 'Sugar', 'Eggs', 'Butter', 'Chocolate chips'],
            'allergens': ['Gluten', 'Dairy', 'Eggs'],
            'serving_size': '8-10 people',
            'preparation_time': '24-48 hours'
        },
        {
            '_id': 'cake_2',
            'name': 'Vanilla Dream',
            'price': 35000,
            'description': 'Classic vanilla cake with buttercream frosting and fresh berries. A timeless favorite that never goes out of style.',
            'category': 'Vanilla Cake',
            'image': '/static/cake_uploads/VanillaCake.jpg',
            'ingredients': ['Flour', 'Sugar', 'Eggs', 'Butter', 'Vanilla extract', 'Fresh berries'],
            'allergens': ['Gluten', 'Dairy', 'Eggs'],
            'serving_size': '6-8 people',
            'preparation_time': '24-48 hours'
        },
        {
            '_id': 'cake_3',
            'name': 'Red Velvet Royal',
            'price': 55000,
            'description': 'Luxurious red velvet cake with cream cheese frosting. Elegant and sophisticated, perfect for special occasions.',
            'category': 'Wedding Cake',
            'image': '/static/cake_uploads/weddingCake.jpg',
            'ingredients': ['Flour', 'Cocoa powder', 'Red food coloring', 'Buttermilk', 'Cream cheese', 'Butter'],
            'allergens': ['Gluten', 'Dairy', 'Eggs'],
            'serving_size': '12-15 people',
            'preparation_time': '48-72 hours'
        },
        {
            '_id': 'cake_4',
            'name': 'Orange Zest Special',
            'price': 40000,
            'description': 'Fresh orange cake with citrus glaze and candied orange peel. A refreshing and tangy delight.',
            'category': 'Orange Cake',
            'image': '/static/cake_uploads/orangeCake.jpg',
            'ingredients': ['Flour', 'Sugar', 'Eggs', 'Orange juice', 'Orange zest', 'Butter'],
            'allergens': ['Gluten', 'Dairy', 'Eggs'],
            'serving_size': '6-8 people',
            'preparation_time': '24-48 hours'
        },
        {
            '_id': 'cake_5',
            'name': 'Mini Vanilla Cupcakes',
            'price': 15000,
            'description': 'Delicious mini vanilla cupcakes perfect for parties and events. Bite-sized treats that pack big flavor.',
            'category': 'Mini Cake',
            'image': '/static/cake_uploads/Vanilla-Cupcakes-Square-2024.webp',
            'ingredients': ['Flour', 'Sugar', 'Eggs', 'Butter', 'Vanilla extract', 'Frosting'],
            'allergens': ['Gluten', 'Dairy', 'Eggs'],
            'serving_size': '12 mini cupcakes',
            'preparation_time': '12-24 hours'
        },
        {
            '_id': 'cake_6',
            'name': 'Fresh Bread Loaf',
            'price': 8000,
            'description': 'Freshly baked bread made with traditional methods. Perfect for breakfast or as a side with meals.',
            'category': 'Bread',
            'image': '/static/cake_uploads/bread.jpg',
            'ingredients': ['Flour', 'Water', 'Yeast', 'Salt', 'Sugar'],
            'allergens': ['Gluten'],
            'serving_size': '8-10 slices',
            'preparation_time': '4-6 hours'
        },
        {
            '_id': 'cake_7',
            'name': 'Chocolate Chip Cookies',
            'price': 12000,
            'description': 'Classic chocolate chip cookies with a perfect balance of crispy edges and chewy centers.',
            'category': 'Cookies',
            'image': '/static/cake_uploads/classic-chocolate-chip-cookies.jpg',
            'ingredients': ['Flour', 'Butter', 'Brown sugar', 'Chocolate chips', 'Eggs', 'Vanilla'],
            'allergens': ['Gluten', 'Dairy', 'Eggs'],
            'serving_size': '24 cookies',
            'preparation_time': '2-4 hours'
        },
        {
            '_id': 'cake_8',
            'name': 'Ready Chocolate Cake',
            'price': 25000,
            'description': 'Pre-made chocolate cake ready for immediate enjoyment. Perfect when you need something sweet right away.',
            'category': 'Ready Cake',
            'image': '/static/cake_uploads/Chocolate-Cake-8-1-scaled-354x354.webp',
            'ingredients': ['Flour', 'Cocoa powder', 'Sugar', 'Eggs', 'Butter', 'Chocolate'],
            'allergens': ['Gluten', 'Dairy', 'Eggs'],
            'serving_size': '6-8 people',
            'preparation_time': 'Ready to serve'
        }
    ]
    
    # Add sample data to collections
    for cake in sample_cakes:
        db.cakes.insert_one(cake)
    
    # Sample users
    sample_users = [
        {
            '_id': 'user_1',
            'email': 'admin@fyncakes.com',
            'username': 'admin',
            'first_name': 'Admin',
            'last_name': 'User',
            'role': 'admin',
            'password': 'hashed_password'
        },
        {
            '_id': 'user_2',
            'email': 'customer@example.com',
            'username': 'customer1',
            'first_name': 'John',
            'last_name': 'Doe',
            'role': 'customer',
            'password': 'hashed_password'
        }
    ]
    
    for user in sample_users:
        db.users.insert_one(user)
    
    # Sample orders
    sample_orders = [
        {
            '_id': 'order_1',
            'order_id': 'FYN-1001',
            'customer_email': 'customer@example.com',
            'products': [sample_cakes[0]],
            'total_amount': 45000,
            'payment_status': 'completed',
            'order_status': 'delivered',
            'delivery_date': '2024-01-15',
            'customer_phone': '0758123456',
            'order_placed_at': '2024-01-10'
        }
    ]
    
    for order in sample_orders:
        db.orders.insert_one(order)
    
    # Initialize comments collection
    sample_comments = [
        {
            '_id': 'comment_1',
            'name': 'Sarah Johnson',
            'email': 'sarah.j@email.com',
            'comment': 'Absolutely delicious cakes! The attention to detail and the flavors are amazing. FynCakes is our go-to for every family celebration. The wedding cake they made for us was absolutely perfect!',
            'rating': 5,
            'approved': True,
            'created_at': datetime.now() - timedelta(days=5)
        },
        {
            '_id': 'comment_2',
            'name': 'Michael Davis',
            'email': 'michael.d@email.com',
            'comment': 'FynCakes made our wedding day extra special with the most beautiful and delicious cake. Thank you for the wonderful experience and impeccable service! Highly recommended!',
            'rating': 5,
            'approved': True,
            'created_at': datetime.now() - timedelta(days=3)
        },
        {
            '_id': 'comment_3',
            'name': 'Grace Mbabazi',
            'email': 'grace.m@email.com',
            'comment': 'The best bakery in Kampala! Their cakes are not only beautiful but incredibly delicious. The team is professional and always delivers on time. Five stars!',
            'rating': 5,
            'approved': True,
            'created_at': datetime.now() - timedelta(days=1)
        },
        {
            '_id': 'comment_4',
            'name': 'David Kato',
            'email': 'david.k@email.com',
            'comment': 'Amazing service and even better cakes! The chocolate cake was to die for. Will definitely order again for my daughter\'s birthday next month.',
            'rating': 5,
            'approved': True,
            'created_at': datetime.now() - timedelta(hours=12)
        },
        {
            '_id': 'comment_5',
            'name': 'Jennifer Namukasa',
            'email': 'jennifer.n@email.com',
            'comment': 'Professional, creative, and absolutely delicious! FynCakes exceeded all our expectations. The cake was the highlight of our celebration.',
            'rating': 5,
            'approved': True,
            'created_at': datetime.now() - timedelta(hours=6)
        }
    ]
    
    for comment in sample_comments:
        db.comments.insert_one(comment)
    
    return db
