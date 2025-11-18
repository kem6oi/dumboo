# app/admin/routes.py

from flask import render_template, url_for, flash, redirect, request, jsonify, current_app # Import current_app
from flask_login import login_required, current_user
from app import db # db is initialized in app/__init__.py
from app.models import User, Challenge, SolvedChallenge, Product, Purchase # Import models
from app.admin.forms import CreateChallengeForm, ManageUserForm # Import forms
from app.utils import verify_challenge_solution # Keep verify for admin view (optional)
from app.admin import admin
import json
from functools import wraps # Needed for decorator
from sqlalchemy import func # Import func for counts

def admin_required(f):
    """Decorator to ensure user is an admin"""
    @wraps(f) # Use wraps to preserve original function info
    @login_required
    def decorated_function(*args, **kwargs):
        if current_user.role != 'admin':
            flash('You must be an admin to access this page!', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@admin.route('/dashboard')
@admin_required
def dashboard():
    # Get counts for the admin dashboard
    user_count = User.query.count()
    challenge_count = Challenge.query.count()
    product_count = Product.query.count()
    purchase_count = Purchase.query.count()

    # Recent activity (last 5 solved challenges)
    recent_solves = SolvedChallenge.query.order_by(SolvedChallenge.solution_time.desc()).limit(5).all()

    # Recent user registrations
    recent_users = User.query.order_by(User.date_registered.desc()).limit(5).all()

    return render_template('admin/dashboard.html', title='Admin Dashboard',
                          user_count=user_count, challenge_count=challenge_count,
                          product_count=product_count, purchase_count=purchase_count,
                          recent_solves=recent_solves, recent_users=recent_users)

@admin.route('/create_challenge', methods=['GET', 'POST'])
@admin_required
def create_challenge():
    form = CreateChallengeForm()

    # Set choices for SelectFields dynamically in the route
    categories = current_app.config.get('CHALLENGE_CATEGORIES', [])
    form.category.choices = [(c, c) for c in categories]
    # Add empty choice for encryption type as it's optional
    encryption_types = current_app.config.get('ENCRYPTION_TYPES', [])
    form.encryption_type.choices = [('', '--- Select Type (Crypto Only) ---')] + [(et, et.upper()) for et in encryption_types]


    if form.validate_on_submit():
        # Challenge data, flag, encryption_type, config_json are taken directly from form
        # No automatic encryption in the app during creation for flexibility
        challenge = Challenge(
            title=form.title.data,
            description=form.description.data,
            difficulty=form.difficulty.data,
            category=form.category.data,
            flag=form.flag.data, # Save the flag
            challenge_data=form.challenge_data.data, # Save challenge data blob
            encryption_type=form.encryption_type.data if form.encryption_type.data else None, # Save encryption type (nullable)
            config_json=form.config_json.data if form.config_json.data else None, # Save config JSON (nullable)
            created_by=current_user.id,
            is_active=True # Challenges are active by default on creation
        )

        db.session.add(challenge)
        db.session.commit()

        flash(f'Challenge "{form.title.data}" ({challenge.category}) has been created!', 'success')
        return redirect(url_for('admin.view_challenge', challenge_id=challenge.id))
    # If validation fails or it's a GET request, render the template
    return render_template('admin/create_challenge.html', title='Create Challenge', form=form)

@admin.route('/challenge/<int:challenge_id>/edit', methods=['GET', 'POST']) # New route for editing
@admin_required
def edit_challenge(challenge_id):
    """Admin route to edit an existing challenge."""
    challenge = Challenge.query.get_or_404(challenge_id)
    form = CreateChallengeForm(obj=challenge) # Populate form with existing challenge data

    # Set choices for SelectFields dynamically, like in create_challenge
    categories = current_app.config.get('CHALLENGE_CATEGORIES', [])
    form.category.choices = [(c, c) for c in categories]
    encryption_types = current_app.config.get('ENCRYPTION_TYPES', [])
    form.encryption_type.choices = [('', '--- Select Type (Crypto Only) ---')] + [(et, et.upper()) for et in encryption_types]


    if form.validate_on_submit():
        # Update challenge object with form data
        form.populate_obj(challenge) # Update challenge attributes from form
        # Ensure encryption_type and config_json are set to None if empty strings are submitted
        if not form.encryption_type.data:
            challenge.encryption_type = None
        if not form.config_json.data:
            challenge.config_json = None
        if not form.challenge_data.data:
             challenge.challenge_data = None


        db.session.commit()
        flash(f'Challenge "{challenge.title}" has been updated!', 'success')
        return redirect(url_for('admin.view_challenge', challenge_id=challenge.id))
    # else: # GET request or validation failed
        # Form is already populated with obj=challenge on GET

    return render_template('admin/edit_challenge.html', title=f'Edit Challenge - {challenge.title}',
                           form=form, challenge=challenge)

@admin.route('/challenge/<int:challenge_id>')
@admin_required
def view_challenge(challenge_id):
    challenge = Challenge.query.get_or_404(challenge_id)

    # Get solution count and users who solved
    solvers = User.query.join(SolvedChallenge).filter(SolvedChallenge.challenge_id == challenge_id).all()

    # Attempt verification using utils function for admin view (optional)
    # This requires a placeholder solution, maybe the flag itself, just to test the function
    # Verification logic expects submitted_solution, challenge object
    # test_verification_success = verify_challenge_solution(challenge.flag, challenge) # Test with correct flag
    # test_verification_fail = verify_challenge_solution("wrong_flag", challenge) # Test with wrong flag


    return render_template('admin/view_challenge.html', title=challenge.title,
                          challenge=challenge, solvers=solvers
                          # , test_verification_success=test_verification_success # Pass test results
                          # , test_verification_fail=test_verification_fail
                          )

@admin.route('/challenges')
@admin_required
def manage_challenges():
    page = request.args.get('page', 1, type=int)
    challenges = Challenge.query.order_by(Challenge.date_created.desc()).paginate(page=page, per_page=current_app.config.get('CHALLENGES_PER_PAGE', 10)) # Use config for per_page

    return render_template('admin/manage_challenges.html', title='Manage Challenges', challenges=challenges)

# toggle_challenge, delete_challenge, manage_users, edit_user, get_encryption_details, statistics routes remain largely unchanged,
# potentially needing minor updates if they display renamed columns (e.g., showing .flag instead of .original_text)

# Example update for get_encryption_details (now more generic config details)
@admin.route('/get_config_details/<int:challenge_id>') # Renamed route
@admin_required
def get_config_details(challenge_id):
    challenge = Challenge.query.get_or_404(challenge_id)

    details = {
        'category': challenge.category,
        'encryption_type': challenge.encryption_type,
        'challenge_data': challenge.challenge_data,
        'config_json': challenge.config_json,
        'flag': challenge.flag # Include flag for admin
    }

    return jsonify(details)


@admin.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
@admin_required
def edit_user(user_id): # <--- This is the function definition
    user = User.query.get_or_404(user_id)
    form = ManageUserForm()

    if form.validate_on_submit():
        if form.user_role.data == 'inactive':
            user.is_active = False
            flash(f'User {user.username} has been deactivated!', 'success')
        else:
            user.role = form.user_role.data
            user.is_active = True
            flash(f'User {user.username} has been updated to {form.user_role.data}!', 'success')

        db.session.commit()
        return redirect(url_for('admin.manage_users'))

    # Pre-fill form with current role
    form.user_role.data = user.role if user.is_active else 'inactive'

    return render_template('admin/edit_user.html', title=f'Edit User - {user.username}',
                          user=user, form=form)    


@admin.route('/users')
@admin_required
def manage_users(): # <--- This function name defines the endpoint suffix
    page = request.args.get('page', 1, type=int)
    users = User.query.order_by(User.date_registered.desc()).paginate(page=page, per_page=current_app.config.get('CHALLENGES_PER_PAGE', 10))

    return render_template('admin/manage_users.html', title='Manage Users', users=users)


@admin.route('/delete_challenge/<int:challenge_id>')
@admin_required
def delete_challenge(challenge_id): # <--- This is the function definition
    challenge = Challenge.query.get_or_404(challenge_id)

    # Check if any users have solved this challenge
    if SolvedChallenge.query.filter_by(challenge_id=challenge_id).first():
        flash('Cannot delete a challenge that has been solved by users!', 'danger')
        return redirect(url_for('admin.manage_challenges'))

    db.session.delete(challenge)
    db.session.commit()

    flash(f'Challenge "{challenge.title}" has been deleted!', 'success')
    return redirect(url_for('admin.manage_challenges'))


@admin.route('/toggle_challenge/<int:challenge_id>')
@admin_required
def toggle_challenge(challenge_id):
    """Admin route to toggle the active status of a challenge."""
    challenge = Challenge.query.get_or_404(challenge_id)

    # Ensure the challenge exists and isn't somehow None after get_or_404 (shouldn't happen)
    if not challenge:
        flash('Challenge not found!', 'danger')
        return redirect(url_for('admin.manage_challenges'))

    # Toggle the is_active status
    challenge.is_active = not challenge.is_active
    db.session.commit()

    status = "activated" if challenge.is_active else "deactivated"
    flash(f'Challenge "{challenge.title}" has been {status}!', 'success')

    # Redirect back to the manage challenges page
    return redirect(url_for('admin.manage_challenges'))


@admin.route('/statistics')
@admin_required
def statistics():
    # User statistics (unchanged)
    user_stats = {
        'total': User.query.count(),
        'admins': User.query.filter_by(role='admin').count(),
        'sellers': User.query.filter_by(role='seller').count(),
        'buyers': User.query.filter_by(role='buyer').count(),
        'enthusiasts': User.query.filter_by(role='enthusiast').count()
    }

    # Challenge statistics
    # Get difficulty counts
    challenge_counts_by_difficulty = db.session.query(
        Challenge.difficulty, func.count(Challenge.id)
    ).group_by(Challenge.difficulty).all()

    # Get category counts
    challenge_counts_by_category = db.session.query(
        Challenge.category, func.count(Challenge.id)
    ).group_by(Challenge.category).all()

    # Get encryption type counts (only for challenges where encryption_type is not null)
    challenge_counts_by_encryption = db.session.query(
        Challenge.encryption_type, func.count(Challenge.id)
    ).filter(Challenge.encryption_type.isnot(None)).group_by(Challenge.encryption_type).all()


    challenge_stats = {
        'total': Challenge.query.count(),
        'difficulty': dict(challenge_counts_by_difficulty),
        'category': dict(challenge_counts_by_category),
        'encryption_type': dict(challenge_counts_by_encryption)
    }
    # Ensure all defined categories from config are listed even if count is 0 for stats display
    all_categories = current_app.config.get('CHALLENGE_CATEGORIES', [])
    for c in all_categories:
         if c not in challenge_stats['category']: challenge_stats['category'][c] = 0
    # Ensure all difficulties are listed
    for d in ['easy', 'medium', 'hard']:
        if d not in challenge_stats['difficulty']: challenge_stats['difficulty'][d] = 0
    # Ensure standard encryption types from config are listed
    for et in current_app.config.get('ENCRYPTION_TYPES', []):
         if et not in challenge_stats['encryption_type']: challenge_stats['encryption_type'][et] = 0


    # Marketplace statistics (unchanged)
    marketplace_stats = {
        'products': Product.query.count(),
        'purchases': Purchase.query.count(),
        'active_products': Product.query.filter_by(available=True).count(),
        'completed_purchases': Purchase.query.filter_by(status='completed').count()
    }

    return render_template('admin/statistics.html', title='Platform Statistics',
                          user_stats=user_stats, challenge_stats=challenge_stats,
                          marketplace_stats=marketplace_stats)
