# app/auth/routes.py

from flask import render_template, url_for, flash, redirect, request, session
from flask_login import login_user, current_user, logout_user, login_required
from app import db, bcrypt # db and bcrypt are initialized in app/__init__.py
from app.models import User # Only User needed directly here
from app.auth.forms import RegistrationForm, LoginForm, AdminRegistrationForm
from app.auth import auth
# Import current_app and Config to check requirements in profile/upgrade routes
from flask import current_app as app # Import current_app

# Admin registration key - in a real app, you'd store this securely or use a better solution
ADMIN_REGISTRATION_KEY = "secure_admin_key_12345"

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(
            username=form.username.data,
            email=form.email.data,
            password=hashed_password,
            role=form.role.data # User's chosen role is saved, but access is based on challenges
        )
        db.session.add(user)
        db.session.commit()
        flash(f'Account created for {form.username.data}! You can now log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html', title='Register', form=form)

@auth.route('/admin_register', methods=['GET', 'POST'])
def admin_register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = AdminRegistrationForm()
    if form.validate_on_submit():
        if form.admin_key.data != ADMIN_REGISTRATION_KEY:
            flash('Invalid admin registration key!', 'danger')
            return render_template('auth/admin_register.html', title='Admin Registration', form=form)

        # Check if an admin already exists (optional check)
        existing_admin = User.query.filter_by(role='admin').first()
        if existing_admin:
             flash('An admin account already exists. Please contact the administrator.', 'warning')
             return render_template('auth/admin_register.html', title='Admin Registration', form=form)


        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(
            username=form.username.data,
            email=form.email.data,
            password=hashed_password,
            role='admin' # Role is set to admin
        )
        db.session.add(user)
        db.session.commit()
        flash(f'Admin account created for {form.username.data}! You can now log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/admin_register.html', title='Admin Registration', form=form)


@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        # Redirect authenticated users based on their *potential* access level
        # This is more complex now as role != access
        easy_required = app.config.get('EASY_CHALLENGES_REQUIRED_FOR_BUYER', 0)
        hard_required = app.config.get('HARD_CHALLENGES_REQUIRED_FOR_SELLER', 0)
        easy_solved = current_user.get_solved_easy_count() # Use new methods
        hard_solved = current_user.get_solved_hard_count() # Use new methods

        if current_user.role == 'admin':
             return redirect(url_for('admin.dashboard'))
        elif hard_solved >= hard_required: # Check seller access first (higher tier)
            return redirect(url_for('marketplace.seller_dashboard'))
        elif easy_solved >= easy_required: # Then check buyer access
            return redirect(url_for('marketplace.buyer_dashboard'))
        else: # Default for Enthusiast or those not meeting reqs
            return redirect(url_for('challenges.list'))


    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')

            # Redirect based on user's *actual* access level after successful login
            easy_required = app.config.get('EASY_CHALLENGES_REQUIRED_FOR_BUYER', 0)
            hard_required = app.config.get('HARD_CHALLENGES_REQUIRED_FOR_SELLER', 0)
            easy_solved = user.get_solved_easy_count() # Use new methods on the logged-in user object
            hard_solved = user.get_solved_hard_count() # Use new methods

            if user.role == 'admin':
                redirect_url = next_page or url_for('admin.dashboard')
            elif hard_solved >= hard_required: # Seller access
                 redirect_url = next_page or url_for('marketplace.seller_dashboard')
            elif easy_solved >= easy_required: # Buyer access
                 redirect_url = next_page or url_for('marketplace.buyer_dashboard')
            else:  # No marketplace access yet
                redirect_url = next_page or url_for('challenges.list')

            return redirect(redirect_url)
        else:
            flash('Login failed. Please check email and password.', 'danger')

    return render_template('auth/login.html', title='Login', form=form)

@auth.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@auth.route('/profile')
@login_required
def profile():
    # Get all solved counts using the dict method
    all_solved_counts = current_user.get_all_solved_counts_dict()

    easy_count = all_solved_counts.get('easy', 0)
    medium_count = all_solved_counts.get('medium', 0)
    hard_count = all_solved_counts.get('hard', 0)

    # Get requirements from config
    easy_required = app.config.get('EASY_CHALLENGES_REQUIRED_FOR_BUYER', 0)
    hard_required = app.config.get('HARD_CHALLENGES_REQUIRED_FOR_SELLER', 0)

    # Determine if user meets requirements (even if they already have the role)
    meets_buyer_req = easy_count >= easy_required
    meets_seller_req = hard_count >= hard_required

    # Determine if upgrade buttons should be shown on the profile page
    # Show upgrade to buyer button if they meet requirements AND are not already seller/admin role
    show_upgrade_buyer = meets_buyer_req and current_user.role not in ['seller', 'admin']
    # Show upgrade to seller button if they meet requirements AND are not already admin role
    show_upgrade_seller = meets_seller_req and current_user.role != 'admin'


    return render_template('auth/profile.html', title='Profile',
                          easy_count=easy_count, medium_count=medium_count, hard_count=hard_count,
                          easy_required=easy_required, hard_required=hard_required, # Pass requirements
                          show_upgrade_buyer=show_upgrade_buyer, show_upgrade_seller=show_upgrade_seller # Pass button flags
                          )

@auth.route('/upgrade_role/<role>')
@login_required
# No access decorator here, login is sufficient. Eligibility check is inside.
def upgrade_role(role):
    # Get requirements from config
    easy_required = app.config.get('EASY_CHALLENGES_REQUIRED_FOR_BUYER', 0)
    hard_required = app.config.get('HARD_CHALLENGES_REQUIRED_FOR_SELLER', 0)

    # Get current solved counts using the dict method
    all_solved_counts = current_user.get_all_solved_counts_dict()
    easy_solved = all_solved_counts.get('easy', 0)
    hard_solved = all_solved_counts.get('hard', 0)

    # Recalculate eligibility based on *current* counts
    can_be_buyer = easy_solved >= easy_required
    can_be_seller = hard_solved >= hard_required

    # Perform the upgrade logic based on requested role and eligibility
    if role == 'buyer':
        # Check if they are eligible AND are not already a higher role
        if can_be_buyer and current_user.role not in ['buyer', 'seller', 'admin']:
             current_user.role = 'buyer' # Update the role string
             db.session.commit()
             flash('Your account has been upgraded to Buyer status! You can now access buyer features.', 'success')
        else:
             # Provide specific feedback
             if current_user.role in ['buyer', 'seller', 'admin']:
                  flash(f'You are already a {current_user.role.capitalize()} and cannot upgrade to Buyer.', 'info')
             else:
                  flash(f'You need to solve {easy_required - easy_solved} more Easy challenges to qualify for Buyer status.', 'danger')

    elif role == 'seller':
         # Check if they are eligible AND are not already admin role
         if can_be_seller and current_user.role != 'admin':
             current_user.role = 'seller' # Update the role string
             db.session.commit()
             flash('Your account has been upgraded to Seller status! You can now access seller features.', 'success')
         else:
            # Provide specific feedback
            if current_user.role == 'admin':
                 flash('You are already an Admin and cannot upgrade to Seller.', 'info')
            else:
                 flash(f'You need to solve {hard_required - hard_solved} more Hard challenges to qualify for Seller status.', 'danger')
    else:
        flash('Invalid role upgrade request.', 'danger')

    return redirect(url_for('auth.profile'))