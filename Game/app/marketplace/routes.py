# app/marketplace/routes.py

from flask import render_template, url_for, flash, redirect, request, abort, current_app, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import User, Product, Purchase, CartItem, PaymentTransaction
# Import new form: VerifyMpesaForm
from app.marketplace.forms import ProductForm, PurchaseForm, AddToCartForm, CheckoutForm, VerifyMpesaForm
from app.utils import save_picture
from app.marketplace import marketplace
import os
from functools import wraps
import json
import requests # Needed for M-Pesa API calls (simulated)
from datetime import datetime
from decimal import Decimal # Good practice for currency calculations
import secrets # Needed for generating unique IDs
import time # Needed for simulated M-Pesa timestamp


# Decorators remain unchanged
def buyer_required(f):
    """Decorator to ensure user has buyer access (solved challenges or admin)"""
    @wraps(f) # Use wraps to preserve original function info
    @login_required
    def decorated_function(*args, **kwargs):
        # Check admin status first (User model has_access checks only admin now)
        if current_user.has_access_to_buyer_features(): # This just checks if role is admin
            return f(*args, **kwargs)

        # For non-admins, check challenge requirement directly in the decorator
        easy_challenges_required = current_app.config.get('EASY_CHALLENGES_REQUIRED_FOR_BUYER', 0)
        easy_challenges_solved = current_user.get_solved_easy_count() # Call the method to get the count

        if easy_challenges_solved >= easy_challenges_required:
             return f(*args, **kwargs) # Access granted based on solved challenges
        else:
             flash('You must solve {} easy challenges to access buyer features!'.format(easy_challenges_required), 'warning')
             return redirect(url_for('access')) # Redirect to access requirements page

    return decorated_function


def seller_required(f):
    """Decorator to ensure user has seller access (solved challenges or admin)"""
    @wraps(f) # Use wraps to preserve original function info
    @login_required
    def decorated_function(*args, **kwargs):
         # Check admin status first (User model has_access checks only admin now)
        if current_user.has_access_to_seller_features(): # This just checks if role is admin
            return f(*args, **kwargs)

        # For non-admins, check challenge requirement directly in the decorator
        hard_challenges_required = current_app.config.get('HARD_CHALLENGES_REQUIRED_FOR_SELLER', 0)
        hard_challenges_solved = current_user.get_solved_hard_count() # Call the method to get the count

        if hard_challenges_solved >= hard_challenges_required:
             return f(*args, **kwargs) # Access granted based on solved challenges
        else:
             flash('You must solve {} hard challenges to access seller features!'.format(hard_challenges_required), 'warning')
             return redirect(url_for('access')) # Redirect to access requirements page

    return decorated_function


# Marketplace Home / Product Listing (Accessible to Buyer/Seller/Admin)
@marketplace.route('/')
@buyer_required # Requires buyer access
def product_list():
    page = request.args.get('page', 1, type=int)
    products = Product.query.filter_by(available=True).order_by(Product.date_posted.desc()).paginate(page=page, per_page=current_app.config.get('CHALLENGES_PER_PAGE', 10)) # Reuse challenge page size config
    return render_template('marketplace/product_list.html', title='Marketplace', products=products)

# View Single Product (Accessible to Buyer/Seller/Admin)
@marketplace.route('/product/<int:product_id>', methods=['GET', 'POST'])
@buyer_required # Requires buyer access to view details and potentially add to cart
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)

    # Use AddToCartForm on product detail page
    add_to_cart_form = AddToCartForm()
    # Remove the old PurchaseForm if it's not used anymore

    # Handle Add To Cart submission
    if add_to_cart_form.validate_on_submit() and product.available and product.seller_id != current_user.id:
        quantity = add_to_cart_form.quantity.data
        # Check if the item is already in the cart
        cart_item = CartItem.query.filter_by(user_id=current_user.id, product_id=product.id).first()

        if cart_item:
            # Update quantity if item already exists
            cart_item.quantity += quantity
        else:
            # Add new item to cart
            cart_item = CartItem(user_id=current_user.id, product_id=product.id, quantity=quantity)
            db.session.add(cart_item)

        db.session.commit()
        flash(f'{quantity} x "{product.name}" added to your cart!', 'success')
        return redirect(url_for('marketplace.view_cart')) # Redirect to cart after adding


    return render_template('marketplace/product_detail.html', title=product.name,
                           product=product, add_to_cart_form=add_to_cart_form)


# Create New Product (Seller/Admin Only)
@marketplace.route('/product/new', methods=['GET', 'POST'])
@seller_required # Requires seller access
def create_product():
    form = ProductForm()
    if form.validate_on_submit():
        picture_file = None
        # Check if an image file was provided in the form data
        if form.image.data and form.image.data.filename:
             # Check if the file type is allowed (using current_app.config)
            allowed_extensions = current_app.config.get('ALLOWED_EXTENSIONS', set())
            if '.' in form.image.data.filename and \
               form.image.data.filename.rsplit('.', 1)[1].lower() in allowed_extensions:
                # Call the save_picture function
                picture_file = save_picture(form.image.data, folder='product_pics')
                if picture_file is None: # Check if saving failed (e.g. permissions)
                     flash('Failed to save product image.', 'danger')
                     # Decide how to handle: Allow creation without image? Or block?
                     # For now, the logic below allows creation without image if saving failed.
            else:
                flash('Invalid file type for image. Allowed types are: {}.'.format(', '.join(allowed_extensions)), 'danger')
                picture_file = None # Ensure picture_file is None if type is invalid

        # Check if the form was submitted without an image file, OR if an image was submitted AND saved successfully
        if not form.image.data.filename or (form.image.data.filename and picture_file is not None):
            product = Product(
                name=form.name.data,
                description=form.description.data,
                price=form.price.data,
                seller_id=current_user.id,
                # Store the returned relative path in the database
                image_file=picture_file if picture_file is not None else 'default_product.jpg' # Use default if saving failed or no file uploaded
            )
            db.session.add(product)
            db.session.commit()
            flash('Your product has been created!', 'success')
            return redirect(url_for('marketplace.product_detail', product_id=product.id))
        # If form.image.data.filename was true but picture_file is None, flash message handled above.
        # The form will re-render with validation errors.


    return render_template('marketplace/create_product.html', title='Create Product', form=form)


# Seller Dashboard (Seller/Admin Only)
@marketplace.route('/seller_dashboard')
@seller_required # Requires seller access
def seller_dashboard():
    # List products created by the current user
    seller_products = Product.query.filter_by(seller_id=current_user.id).order_by(Product.date_posted.desc()).all()

    # List sales related to the current user's products
    # Note: This requires joining Purchase with Product and filtering by seller_id
    sales = db.session.query(Purchase, Product).join(Product).filter(Product.seller_id == current_user.id).order_by(Purchase.purchase_date.desc()).all()

    return render_template('marketplace/seller_dashboard.html', title='Seller Dashboard',
                           seller_products=seller_products, sales=sales)

# Buyer Dashboard (Buyer/Seller/Admin Only)
@marketplace.route('/buyer_dashboard')
@buyer_required # Requires buyer access
def buyer_dashboard():
    # List purchases made by the current user
    user_purchases = Purchase.query.filter_by(buyer_id=current_user.id).order_by(Purchase.purchase_date.desc()).all()

    # Also show recent payment transactions
    # Filter transactions to show only those related to marketplace purchases (if you add order_id linking)
    # For now, show all user transactions
    recent_transactions = PaymentTransaction.query.filter_by(user_id=current_user.id).order_by(PaymentTransaction.transaction_time.desc()).limit(10).all()


    return render_template('marketplace/buyer_dashboard.html', title='Buyer Dashboard',
                           user_purchases=user_purchases,
                           recent_transactions=recent_transactions)


# Route to toggle product availability (Seller/Admin Only)
@marketplace.route('/toggle_product/<int:product_id>')
@seller_required # Assuming only seller/admin can toggle their product
def toggle_product(product_id):
    product = Product.query.get_or_404(product_id)

    # Ensure the current user is the seller of the product, or an admin
    if product.seller_id != current_user.id and current_user.role != 'admin':
        abort(403) # Forbidden

    product.available = not product.available
    db.session.commit()

    status = "activated" if product.available else "deactivated"
    flash(f'Product "{product.name}" marked as {status}!', 'success')

    # Redirect based on role
    if current_user.role == 'admin':
        # Redirect to a relevant admin page, maybe admin product list if one exists
        # For now, back to admin dashboard or users
        # flash("Admin action performed: Product availability toggled.", 'info') # Added extra flash for context
        return redirect(url_for('admin.manage_users')) # Or create admin product management page
    else: # seller
        return redirect(url_for('marketplace.seller_dashboard'))

# Route to delete product (Seller/Admin Only)
@marketplace.route('/delete_product/<int:product_id>')
@seller_required # Assuming only seller/admin can delete their product
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)

     # Ensure the current user is the seller of the product, or an admin
    if product.seller_id != current_user.id and current_user.role != 'admin':
        abort(403) # Forbidden

    # Optional: Prevent deletion if product has purchases (or handle purchases)
    # Or allow deletion but mark purchases as associated with a deleted product
    if Purchase.query.filter_by(product_id=product.id).first():
        flash('Cannot delete a product that has been purchased.', 'warning')
        if current_user.role == 'admin':
             return redirect(url_for('admin.manage_users')) # Or admin product management page
        else:
             return redirect(url_for('marketplace.seller_dashboard'))

    # Delete product image if it exists and is not the default
    if product.image_file and product.image_file != 'default_product.jpg':
        try:
            # Use app.root_path for reliable path construction
            image_path = os.path.join(current_app.root_path, current_app.config['UPLOAD_FOLDER'], product.image_file) # Corrected path
            if os.path.exists(image_path):
                os.remove(image_path)
        except Exception as e:
            print(f"Error deleting image file: {e}") # Log error, but don't stop deletion

    # Also delete associated cart items
    CartItem.query.filter_by(product_id=product.id).delete()
    db.session.delete(product)
    db.session.commit()

    flash(f'Product "{product.name}" has been deleted.', 'success')

    if current_user.role == 'admin':
        return redirect(url_for('admin.manage_users')) # Or admin product management page
    else: # seller
        return redirect(url_for('marketplace.seller_dashboard'))


# Enthusiast dashboard (simple redirect for now) - Redirects to challenges list
@marketplace.route('/enthusiast_dashboard') # Not linked in navbar, but exists
@login_required
def enthusiast_dashboard():
    # Redirect non-enthusiasts away
    if current_user.role != 'enthusiast':
        # Decorators handle access for buyer/seller/admin links in navbar
        # If somehow they get here, send them to a relevant page
        return redirect(url_for('index')) # Or their respective dashboards if they qualify

    # Check if user has buyer access requirements (even if not buyer role yet)
    easy_required = current_app.config.get('EASY_CHALLENGES_REQUIRED_FOR_BUYER', 0)
    easy_solved = current_user.get_solved_easy_count()
    can_access_buyer = easy_solved >= easy_required

     # Check if user has seller access requirements (even if not seller role yet)
    hard_required = current_app.config.get('HARD_CHALLENGES_REQUIRED_FOR_SELLER', 0)
    hard_solved = current_user.get_solved_hard_count()
    can_access_seller = hard_solved >= hard_required

    # Redirect qualifying users to appropriate dashboard if they aren't already there by role check
    if can_access_seller:
         flash('You have Seller access. Redirecting to Seller Dashboard.', 'info')
         return redirect(url_for('marketplace.seller_dashboard'))
    elif can_access_buyer:
        flash('You have Buyer access. Redirecting to Buyer Dashboard.', 'info')
        return redirect(url_for('marketplace.buyer_dashboard'))
    else: # Enthusiast who doesn't meet buyer requirements yet
        flash('As an Enthusiast, solve challenges to gain marketplace access!', 'info')
        return redirect(url_for('challenges.list')) # Enthusiasts focus on challenges


# --- Cart Routes ---

@marketplace.route('/cart')
@login_required # Anyone logged in can see their cart
def view_cart():
    # Get cart items for the current user, ordered by when added (implicitly by id)
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()

    # Calculate subtotal
    subtotal = Decimal('0.00')
    for item in cart_items:
        # Ensure item.product is loaded and exists
        if item.product:
             subtotal += Decimal(str(item.product.price)) * Decimal(str(item.quantity))
        else:
             # Handle case where product might have been deleted
             print(f"Warning: Product {item.product_id} for cart item {item.id} not found.")
             # Optionally remove orphaned cart item - safer to do this in a cleanup job,
             # but can do it here if product is critical for display/calculation
             # db.session.delete(item)
             # db.session.commit()


    # Check if user has buyer access *at the moment* for checkout button visibility
    # This check is redundant if the decorator already passed, but harmless
    can_checkout = current_user.has_access_to_buyer_features() or (current_user.get_solved_easy_count() >= current_app.config.get('EASY_CHALLENGES_REQUIRED_FOR_BUYER', 0))

    return render_template('marketplace/cart.html', title='Shopping Cart',
                           cart_items=cart_items, subtotal=subtotal, can_checkout=can_checkout)


# Update cart item quantity (via form or AJAX)
# Using simple form submission for now from cart.html
@marketplace.route('/cart/update/<int:item_id>', methods=['POST'])
@login_required
def update_cart_item(item_id):
    cart_item = CartItem.query.get_or_404(item_id)

    # Ensure the cart item belongs to the current user
    if cart_item.user_id != current_user.id:
        abort(403) # Forbidden

    # Using a simple form for quantity update from the template
    try:
        new_quantity = int(request.form.get('quantity'))
        if new_quantity < 1:
            # Optionally delete item if quantity is 0 or less, or just set to 1
            # For now, just flash warning for less than 1
            flash('Quantity must be at least 1.', 'warning')
        else:
            cart_item.quantity = new_quantity
            db.session.commit()
            flash('Cart item quantity updated.', 'success')
    except (ValueError, TypeError):
        flash('Invalid quantity.', 'danger')

    return redirect(url_for('marketplace.view_cart'))


# Remove item from cart
@marketplace.route('/cart/remove/<int:item_id>', methods=['POST'])
@login_required
def remove_from_cart(item_id):
    cart_item = CartItem.query.get_or_404(item_id)

    # Ensure the cart item belongs to the current user
    if cart_item.user_id != current_user.id:
        abort(403) # Forbidden

    db.session.delete(cart_item)
    db.session.commit()
    flash('Item removed from cart.', 'success')

    return redirect(url_for('marketplace.view_cart'))


# --- Checkout and Payment Routes ---

@marketplace.route('/checkout', methods=['GET', 'POST'])
@buyer_required # Requires buyer access to checkout
def checkout():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()

    if not cart_items:
        flash('Your cart is empty.', 'warning')
        return redirect(url_for('marketplace.view_cart'))

    subtotal = Decimal('0.00')
    for item in cart_items:
         if item.product:
            subtotal += Decimal(str(item.product.price)) * Decimal(str(item.quantity))

    # Use a CheckoutForm (if defined with fields like phone number)
    form = CheckoutForm()

    # Handle payment initiation (Simulated M-Pesa LIPA NA MPESA ONLINE)
    # In a real app, this POST would trigger the M-Pesa API call
    if form.validate_on_submit(): # Or just check if request.method == 'POST' if no form fields
        total_amount = float(subtotal) # M-Pesa API typically needs float or integer amount

        # Basic validation for M-Pesa amount
        mpesa_min_amount = current_app.config.get('MPESA_MIN_AMOUNT', 1.00)
        if total_amount < mpesa_min_amount:
             flash(f'Minimum checkout amount is {mpesa_min_amount} KES.', 'danger')
             return redirect(url_for('marketplace.view_cart'))

        # M-Pesa LIPA NA MPESA ONLINE requires a user phone number
        # You'd get this from a form field or user profile (ensure format 254...)
        # Let's hardcode a placeholder phone number for simulation, or add a form field
        # phone_number = form.phone_number.data # If you added phone_number to CheckoutForm
        phone_number = '254700000000' # Placeholder - REPLACE WITH ACTUAL USER INPUT OR PROFILE DATA!


        # --- SIMULATED M-PESA API CALL ---
        # In a real integration, generate timestamp, calculate password, make API request
        # Use current_app.config.get('MPESA_SHORTCODE'), etc.
        # requests.post(MPESA_API_URL, json={...}, headers={...})

        # Simulate API response (successful initiation)
        # Generate a unique CheckoutRequestID for this initiation
        simulated_checkout_id = f"sim_{current_user.id}_{int(time.time())}_{secrets.token_hex(8)}" # Use secrets here


        # Create a PaymentTransaction record (status 'initiated')
        transaction = PaymentTransaction(
            user_id=current_user.id,
            amount=total_amount,
            status='initiated',
            payment_method='mpesa',
            mpesa_checkout_request_id = simulated_checkout_id, # Store the simulated ID
            # mpesa_payload = json.dumps({"simulated_request_payload": "..."}) # Optional: store request payload
        )
        db.session.add(transaction)
        db.session.commit() # Commit to get transaction.id if needed, but ID is auto-generated

        # Assume simulated API initiation is successful
        flash('Simulated M-Pesa STK Push initiated. You would now receive a prompt on your phone.', 'info')

        # Redirect user to a status page to wait or enter code
        return redirect(url_for('marketplace.checkout_status', transaction_id=transaction.id))


    # GET request or form validation failed
    return render_template('marketplace/checkout.html', title='Checkout',
                           cart_items=cart_items, subtotal=subtotal, form=form) # Pass form


# --- M-Pesa Callback URL (Webhook) ---
# This route is called by M-Pesa API (or your simulation), not users directly.
# It must be publicly accessible and not require login.
@marketplace.route('/mpesa_callback', methods=['POST'])
# @csrf.exempt # If you implement CSRF protection globally
def mpesa_callback():
    # --- SIMULATED M-PESA CALLBACK HANDLING ---
    # This callback logic might be less critical if manual verification is the primary flow,
    # but it's essential for a real system's reliability. Keep it for completeness.
    print("Received simulated M-Pesa callback.")
    # In a real app, verify callback authenticity (IP, headers, checksum)

    try:
        callback_data = request.get_json()
        print("Callback Data:", json.dumps(callback_data, indent=2)) # Log incoming data

        # Example parsing based on typical LNM Online callback structure
        body = callback_data.get("Body", {})
        stk_callback = body.get("stkCallback", {})
        checkout_request_id = stk_callback.get("CheckoutRequestID")
        result_code = stk_callback.get("ResultCode")
        result_desc = stk_callback.get("ResultDesc")
        callback_metadata_items = stk_callback.get("CallbackMetadata", {}).get("Item", [])

        mpesa_receipt_number = None
        # amount = None # Can get from callback, but verify against transaction amount
        # phone_number = None # Can get from callback, but verify

        # Extract data from CallbackMetadata
        for item in callback_metadata_items:
            if item.get("Name") == "MpesaReceiptNumber":
                mpesa_receipt_number = item.get("Value")
            elif item.get("Name") == "Amount":
                # amount = item.get("Value") # Don't rely on this for verification, use stored transaction amount
                pass # We'll get amount from our DB transaction
            elif item.get("Name") == "PhoneNumber":
                # phone_number = item.get("Value") # Don't rely on this for verification
                pass

        # Find the corresponding transaction in your database
        # Use the CheckoutRequestID from the callback
        transaction = PaymentTransaction.query.filter_by(mpesa_checkout_request_id=checkout_request_id).first()

        if transaction:
            # Store the full payload for debugging/record-keeping
            transaction.mpesa_payload = json.dumps(callback_data)
            # Update transaction time from callback if available and reliable
            # transaction.transaction_time = datetime.utcnow() # Or parse timestamp from callback


            if result_code == 0: # Success
                # Verify that the transaction wasn't already completed/failed
                if transaction.status == 'initiated':
                    transaction.status = 'completed'
                    transaction.mpesa_receipt_number = mpesa_receipt_number
                    # Verify amount and phone number against the transaction/order data if possible
                    # E.g. if abs(transaction.amount - float(amount)) > 0.01: log discrepancy!
                    # Ensure the phone number matches the one used to initiate if stored

                    db.session.commit()
                    print(f"Transaction {transaction.id} completed successfully via callback. Receipt: {mpesa_receipt_number}")

                    # --- Process the Order: Create Purchases and Clear Cart ---
                    # Move this logic to a separate function or the manual verification route
                    # It's safer to process the order *after* you are certain the payment is confirmed,
                    # either by a reliable callback OR manual verification.
                    # For this manual verification approach, let's NOT process the order here.
                    # The manual verification route will handle creating purchases and clearing the cart.
                    pass # Do nothing here except update transaction status

                elif transaction.status == 'completed':
                    print(f"Warning: Received duplicate callback for completed transaction {transaction.id}. Receipt: {mpesa_receipt_number}")
                    # Handle duplicate callbacks gracefully
                    pass
                else:
                    print(f"Warning: Received success callback for transaction {transaction.id} with unexpected status {transaction.status}. Receipt: {mpesa_receipt_number}")
                    # Log this anomaly
                    transaction.status = 'completed_late_callback' # Or similar status
                    transaction.mpesa_receipt_number = mpesa_receipt_number
                    db.session.commit() # Save the status change


            else: # Failed or Cancelled callback
                # Do NOT process the order
                if transaction.status == 'initiated': # Only update if still pending
                     transaction.status = 'failed' # Or 'cancelled' based on ResultCode
                     db.session.commit()
                     print(f"Transaction {transaction.id} failed via callback. Result Code: {result_code}, Description: {result_desc}")
                else:
                     print(f"Warning: Received callback for transaction {transaction.id} with non-initiated status ({transaction.status}). Result Code: {result_code}")


            # M-Pesa expects a specific response format (usually a JSON success/error)
            # Always return a 200 OK if you processed the callback successfully
            return jsonify({"ResultCode": 0, "ResultDesc": "Callback received successfully"}), 200

        else:
            print(f"Error: Transaction with CheckoutRequestID {checkout_request_id} not found in DB during callback.")
            # This could indicate a problem. Log the full callback_data.
            return jsonify({"ResultCode": 1, "ResultDesc": "Transaction not found"}), 404 # Or appropriate error code


    except Exception as e:
        print(f"Error processing M-Pesa callback: {e}")
        # Log the error details properly
        return jsonify({"ResultCode": 1, "ResultDesc": "Internal server error"}), 500


# --- Manual Checkout Status and Verification Route ---
@marketplace.route('/checkout/status/<int:transaction_id>', methods=['GET', 'POST'])
@login_required
def checkout_status(transaction_id):
    transaction = PaymentTransaction.query.get_or_404(transaction_id)
    if transaction.user_id != current_user.id:
        abort(403)

    verify_form = None
    if transaction.status in ['initiated', 'pending']:
        verify_form = VerifyMpesaForm()

        if verify_form.validate_on_submit():
            submitted_code = verify_form.mpesa_code.data.strip()

            expected_code = current_app.config.get('SIMULATED_MPESA_CONFIRMATION_CODE', "DEFAULT_CODE")

            # --- DEBUG PRINT STATEMENTS ---
            print(f"DEBUG: Submitted Code (stripped): '{submitted_code}'")
            print(f"DEBUG: Expected Code (from config): '{expected_code}'")
            print(f"DEBUG: Submitted Code (casefolded): '{submitted_code.casefold() if submitted_code else 'None or Empty'}'")
            print(f"DEBUG: Expected Code (casefolded): '{expected_code.casefold() if expected_code else 'None or Empty'}'")
            # --- END DEBUG PRINT STATEMENTS ---

            if expected_code and submitted_code.casefold() == expected_code.casefold():
                # ... (success logic) ...
                # Check if transaction is not already completed
                if transaction.status != 'completed':
                    transaction.status = 'completed' # Mark transaction as completed
                    transaction.mpesa_receipt_number = submitted_code # Store the submitted code as the receipt (in sim)
                    transaction.transaction_time = datetime.utcnow() # Update timestamp to completion time

                    db.session.commit()
                    print(f"Manual verification successful for Transaction {transaction.id}. Code: {submitted_code}")

                    # --- Process the Order: Create Purchases and Clear Cart ---
                    # (Keep the order processing logic here as provided in the last response)
                    user_cart_items = CartItem.query.filter_by(user_id=current_user.id).all()

                    if user_cart_items:
                        for item in user_cart_items:
                            if item.product and item.product.available: # Ensure product exists and is available
                                 purchase = Purchase(
                                     buyer_id=item.user_id,
                                     product_id=item.product_id,
                                     quantity=item.quantity,
                                     status='completed', # Mark purchase as completed
                                     # transaction_id = transaction.id # Add if column exists
                                 )
                                 db.session.add(purchase)
                            else:
                                 print(f"Warning: Skipping purchase for cart item {item.id} (Product not found or unavailable).")

                            db.session.delete(item) # Delete the cart item

                        db.session.commit() # Commit purchases and cart deletion
                        flash('Payment verified and purchase completed!', 'success')
                        print(f"Created Purchases and cleared cart for user {current_user.username}.")

                    else:
                         flash('Payment verified, but no items were found in your cart to purchase.', 'warning')
                         print(f"Warning: Transaction {transaction.id} manually verified, but no cart items found for user {current_user.id}.")

                    return redirect(url_for('marketplace.buyer_dashboard')) # Redirect after successful purchase

                else: # Transaction was already completed
                    flash('Payment was already marked as completed.', 'info')
                    return redirect(url_for('marketplace.buyer_dashboard'))


            else: # Verification Failed
                # Ensure expected_code exists before printing it in the message
                feedback_message = 'Incorrect M-Pesa confirmation code.'
                # Optional: You could add a hint if expected_code is known and not None
                # if expected_code and expected_code != "DEFAULT_CODE":
                #      feedback_message += f" (Expected format: {expected_code})"

                flash(feedback_message, 'danger')
                # Stay on the status page with the form
                # The template will re-render showing the form and the error message


    # GET request or verification form validation failed
    # Pass the form to the template even if validation failed, so errors are shown
    return render_template('marketplace/checkout_status.html', title='Transaction Status',
                           transaction=transaction, verify_form=verify_form)