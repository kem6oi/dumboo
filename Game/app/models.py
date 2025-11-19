# app/models.py

from datetime import datetime
from flask_login import UserMixin
from app import db, login_manager
from flask import current_app as app # Import current_app to access config within model methods
# Do NOT import other models from app.models here to avoid circular imports within the file.


@login_manager.user_loader
def load_user(user_id):
    try:
        return User.query.get(int(user_id))
    except (ValueError, TypeError):
        # Handle invalid user_id from corrupted session data
        return None

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='enthusiast')  # admin, seller, buyer, enthusiast
    date_registered = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    # Relationships (referencing other models by string name is common and avoids import issues here)
    solved_challenges = db.relationship('SolvedChallenge', backref='user', lazy=True)
    products = db.relationship('Product', backref='seller', lazy=True)
    purchases = db.relationship('Purchase', backref='buyer', lazy=True)
    # Add relationship to CartItem
    cart_items = db.relationship('CartItem', backref='buyer', lazy=True)


    def __repr__(self):
        return f"User('{self.username}', '{self.email}', '{self.role}')"

    # --- Methods for getting solved counts and checking access ---

    def get_solved_easy_count(self):
        # Assuming Challenge and SolvedChallenge are defined later in this file and available in namespace
        count = SolvedChallenge.query.join(Challenge).filter( # Using the relationship join style
            SolvedChallenge.user_id == self.id,
            Challenge.difficulty == 'easy'
        ).count()
        return count

    def get_solved_medium_count(self):
         count = SolvedChallenge.query.join(Challenge).filter(
             SolvedChallenge.user_id == self.id,
             Challenge.difficulty == 'medium'
         ).count()
         return count

    def get_solved_hard_count(self):
         count = SolvedChallenge.query.join(Challenge).filter(
             SolvedChallenge.user_id == self.id,
             Challenge.difficulty == 'hard'
         ).count()
         return count

    def get_all_solved_counts_dict(self):
        # This method is good for gathering all counts for display on the profile page
        counts = {}
        # Query solved counts grouped by difficulty
        # Use Challenge.difficulty directly as it should be mapped for queries within this method execution
        solved_by_difficulty = db.session.query(
            Challenge.difficulty, db.func.count(SolvedChallenge.id)
        ).join(SolvedChallenge).filter(
            SolvedChallenge.user_id == self.id
        ).group_by(Challenge.difficulty).all()

        for difficulty, count in solved_by_difficulty:
            counts[difficulty] = count

        # Ensure all standard difficulties are represented, even if count is 0
        for d in ['easy', 'medium', 'hard']:
            if d not in counts:
                counts[d] = 0

        return counts


    def get_solved_count_by_category(self, category):
        # Add a method to get counts by category
        count = SolvedChallenge.query.join(Challenge).filter(
            SolvedChallenge.user_id == self.id,
            Challenge.category == category
        ).count()
        return count

    # Add method to get count of items in the cart
    def get_cart_item_count(self):
        # Assuming CartItem is defined later
        # Count the *number of unique products* in the cart, not total quantity
        # For total quantity, sum(CartItem.quantity)
        return CartItem.query.filter_by(user_id=self.id).count()
        # Or for total quantity:
        # total_quantity = db.session.query(db.func.sum(CartItem.quantity)).filter_by(user_id=self.id).scalar()
        # return total_quantity if total_quantity is not None else 0


    # Simplified access checks - rely on decorators to do the challenge checks
    # These methods now only check if the user is admin (as implemented previously)
    def has_access_to_buyer_features(self):
        """Returns True if user is admin. Challenge check is in decorator."""
        return self.role == 'admin'

    def has_access_to_seller_features(self):
        """Returns True if user is admin. Challenge check is in decorator."""
        return self.role == 'admin'


# --- Model definitions follow. Order matters for relationships defined by string name ---

class Challenge(db.Model):
    # Define Challenge after User because User references it in relationships and methods
    id = db.Column(db.Integer, primary_key=True) # This is the challenge ID
    title = db.Column(db.String(100), nullable=False)

    # Column definitions
    description = db.Column(db.Text, nullable=False) # Description is required
    difficulty = db.Column(db.String(20), nullable=False)  # easy, medium, hard
    category = db.Column(db.String(50), nullable=False, default='Miscellaneous') # Category is required
    is_active = db.Column(db.Boolean, nullable=False, default=True) # Status is required

    # Modified fields to be generic for all challenge types
    challenge_data = db.Column(db.Text, nullable=True) # Optional data blob/instruction (ciphertext, file hash/path, URL)
    flag = db.Column(db.Text, nullable=False) # The required solution string

    # Fields specifically for Cryptography category (nullable now)
    encryption_type = db.Column(db.String(20), nullable=True) # Only relevant/required if category is 'Cryptography'
    config_json = db.Column(db.Text, nullable=True) # JSON string for type-specific configurations

    date_created = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False) # References User


    # Relationship to the User who created the challenge (references 'User' string)
    creator = db.relationship('User', backref='created_challenges', lazy=True)

    # Relationships - solvers relationship references SolvedChallenge (string name)
    solvers = db.relationship('SolvedChallenge', backref='challenge', lazy=True)

    def __repr__(self):
        return f"Challenge('{self.title}', '{self.category}', '{self.difficulty}', ID: {self.id})" # Add category and ID to repr


class SolvedChallenge(db.Model):
    # Define SolvedChallenge after User and Challenge because it references both
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False) # References User
    challenge_id = db.Column(db.Integer, db.ForeignKey('challenge.id'), nullable=False) # References Challenge
    solution_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    attempts = db.Column(db.Integer, nullable=False, default=1)

    # No relationships needed here back to User/Challenge as backrefs are used on User/Challenge

    def __repr__(self):
        return f"SolvedChallenge(User: {self.user_id}, Challenge: {self.challenge_id})"

class Product(db.Model):
    # Define Product after User because it references User
    id = db.Column(db.Integer, primary_key=True)
    # Column definitions
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)

    price = db.Column(db.Float, nullable=False)
    image_file = db.Column(db.String(100), nullable=True, default='default_product.jpg') # Increased length for path
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    seller_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False) # References User
    available = db.Column(db.Boolean, nullable=False, default=True)

    # Relationships - purchases and cart_items reference them by string name
    purchases = db.relationship('Purchase', backref='product', lazy=True)
    cart_items = db.relationship('CartItem', backref='product', lazy=True) # Add relationship to CartItem

    def __repr__(self):
        return f"Product('{self.name}', '${self.price}')"


class Purchase(db.Model):
    # Define Purchase after User and Product because it references both
    id = db.Column(db.Integer, primary_key=True)
    buyer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False) # References User
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False) # References Product
    quantity = db.Column(db.Integer, nullable=False, default=1)
    purchase_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    status = db.Column(db.String(20), nullable=False, default='pending')  # pending, completed, cancelled

    # No relationships needed here back to User/Product as backrefs are used on User/Product

    def __repr__(self):
        return f"Purchase(Buyer: {self.buyer_id}, Product: {self.product_id}, Quantity: {self.quantity})"


# --- New Models for Cart and Payment ---

class CartItem(db.Model):
    # Define CartItem after User and Product because it references both
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False) # References User
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False) # References Product
    quantity = db.Column(db.Integer, nullable=False, default=1)

    # Add a unique constraint to ensure one user has only one entry per product
    __table_args__ = (db.UniqueConstraint('user_id', 'product_id', name='_user_product_uc'),)

    # Relationships - relationships back to User/Product handled by backrefs

    def __repr__(self):
        return f"CartItem(User: {self.user_id}, Product: {self.product_id}, Quantity: {self.quantity})"

# PaymentTransaction model remains the same, but its usage changes slightly in routes
class PaymentTransaction(db.Model):
    # Define after User
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False) # References User
    # Optional: Link to a specific order/checkout session if you add one
    # order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=True)

    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), nullable=False, default='KES') # Assuming KES for M-Pesa
    status = db.Column(db.String(20), nullable=False, default='pending') # pending, initiated, completed, failed, cancelled
    transaction_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # M-Pesa Specific Fields (placeholders for typical data)
    mpesa_checkout_request_id = db.Column(db.String(100), nullable=True) # Unique ID from M-Pesa for transaction initiation
    mpesa_receipt_number = db.Column(db.String(100), nullable=True) # Unique ID from M-Pesa after completion
    mpesa_payload = db.Column(db.Text, nullable=True) # Store raw M-Pesa callback/response (careful with sensitive data)
    payment_method = db.Column(db.String(50), nullable=False, default='mpesa') # Could support other methods

    # No change to definition needed.

    def __repr__(self):
        return f"PaymentTransaction(User: {self.user_id}, Amount: {self.amount}, Status: {self.status})"