 #app/challenges/routes.py

from flask import render_template, url_for, flash, redirect, request, current_app # Import current_app
from flask_login import login_required, current_user
from app import db # db is initialized in app/__init__.py
from app.models import Challenge, SolvedChallenge, User # User needed for leaderboard
from app.challenges.forms import SolveForm # Import the form
from app.utils import verify_challenge_solution # Import the verification logic
from app.challenges import challenges # Import the blueprint
from sqlalchemy import desc, func # Import func for counts
# from app.config import Config # Config is accessed via current_app.config now


@challenges.route('/')
@login_required
def list():
    # Get filter parameters from request args
    difficulty = request.args.get('difficulty', 'all')
    encryption_type = request.args.get('encryption_type', 'all') # Keep filter for crypto type
    category = request.args.get('category', 'all') # Get category filter

    page = request.args.get('page', 1, type=int)

    # Base query for active challenges
    query = Challenge.query.filter_by(is_active=True)

    # Apply filters
    if difficulty != 'all':
        query = query.filter_by(difficulty=difficulty)
    if encryption_type != 'all':
        query = query.filter_by(encryption_type=encryption_type)
    if category != 'all': # Apply category filter
        query = query.filter_by(category=category)


    # Get paginated results
    challenges_list = query.order_by(Challenge.date_created.desc()).paginate(page=page, per_page=current_app.config.get('CHALLENGES_PER_PAGE', 10))

    # Get the challenges the current user has solved
    solved_challenge_ids = [sc.challenge_id for sc in SolvedChallenge.query.filter_by(user_id=current_user.id).all()]

    # Get counts for the sidebar filters
    # Base query for counts (only active challenges)
    count_query_base = Challenge.query.filter_by(is_active=True)

    # Get total count
    total_count = count_query_base.count()

    # Get difficulty counts
    difficulty_counts_result = count_query_base.with_entities(Challenge.difficulty, func.count(Challenge.id)).group_by(Challenge.difficulty).all()
    difficulty_counts = dict(difficulty_counts_result)
    # Ensure all difficulties are present
    for d in ['easy', 'medium', 'hard']:
        difficulty_counts[d] = difficulty_counts.get(d, 0)


    # Get encryption type counts (only count challenges that *have* an encryption type set)
    encryption_counts_result = count_query_base.filter(Challenge.encryption_type.isnot(None)).with_entities(Challenge.encryption_type, func.count(Challenge.id)).group_by(Challenge.encryption_type).all()
    encryption_counts = dict(encryption_counts_result)
    # Ensure all defined encryption types from config are present
    for et in current_app.config.get('ENCRYPTION_TYPES', []):
       encryption_counts[et] = encryption_counts.get(et, 0)


    # Get category counts
    category_counts_result = count_query_base.with_entities(Challenge.category, func.count(Challenge.id)).group_by(Challenge.category).all()
    category_counts = dict(category_counts_result)
     # Ensure all categories from config are present
    all_categories = current_app.config.get('CHALLENGE_CATEGORIES', [])
    for cat in all_categories:
        category_counts[cat] = category_counts.get(cat, 0)


    # Get user solved count
    user_solved_count = len(solved_challenge_ids)


    # Consolidate counts
    counts = {
        'all': total_count,
        'difficulty': difficulty_counts,
        'encryption_type': encryption_counts,
        'category': category_counts,
        'solved_by_user': user_solved_count
    }


    return render_template('challenges/list.html', title='Challenges',
                          challenges=challenges_list, counts=counts,
                          solved_ids=solved_challenge_ids,
                          current_difficulty=difficulty,
                          current_encryption_type=encryption_type,
                          current_category=category, # Pass current category filter
                          all_categories=all_categories # Pass list of all categories for sidebar
                          )

@challenges.route('/<int:challenge_id>', methods=['GET', 'POST'])
@login_required
def details(challenge_id):
    challenge = Challenge.query.get_or_404(challenge_id)

    # Check if challenge is active
    if not challenge.is_active:
        flash('This challenge is currently unavailable.', 'warning')
        return redirect(url_for('challenges.list'))

    # Check if user has already solved this challenge
    already_solved = SolvedChallenge.query.filter_by(
        user_id=current_user.id,
        challenge_id=challenge.id
    ).first() is not None

    form = SolveForm()

    if form.validate_on_submit():
        if already_solved:
            flash('You have already solved this challenge!', 'info')
        else:
            # Attempt to verify the solution using the updated utils function
            if verify_challenge_solution(form.solution.data, challenge):
                # Record the successful solution
                solved = SolvedChallenge(
                    user_id=current_user.id,
                    challenge_id=challenge.id
                )
                db.session.add(solved)
                db.session.commit()

                flash('Congratulations! You solved the challenge correctly!', 'success')
                already_solved = True # Update status so template shows solved

                # Check if user can now qualify for role upgrades (based on counts)
                easy_required = current_app.config.get('EASY_CHALLENGES_REQUIRED_FOR_BUYER', 0)
                hard_required = current_app.config.get('HARD_CHALLENGES_REQUIRED_FOR_SELLER', 0)

                # Use the get_solved_*_count methods which are now simple queries
                easy_solved_now = current_user.get_solved_easy_count()
                hard_solved_now = current_user.get_solved_hard_count()

                if current_user.role == 'enthusiast' and easy_solved_now >= easy_required:
                    flash(f'You\'ve solved enough easy challenges ({easy_solved_now}/{easy_required}) to qualify for Buyer status! Visit your profile to upgrade.', 'info')
                # Check seller eligibility based on cumulative hard solves
                # This check applies if they are enthusiast or buyer
                if current_user.role in ['enthusiast', 'buyer'] and hard_solved_now >= hard_required:
                    flash(f'You\'ve solved enough hard challenges ({hard_solved_now}/{hard_required}) to qualify for Seller status! Visit your profile to upgrade.', 'info')

            else:
                flash('Incorrect solution. Please try again!', 'danger')

    # Pass encryption types list for potential conditional display in template
    all_encryption_types = current_app.config.get('ENCRYPTION_TYPES', [])

    return render_template('challenges/details.html', title=challenge.title,
                          challenge=challenge, form=form, already_solved=already_solved,
                          all_encryption_types=all_encryption_types) # Pass encryption types


@challenges.route('/solved')
@login_required
def solved():
    page = request.args.get('page', 1, type=int)

    # Get all challenges solved by the current user
    solved_challenges = db.session.query(
        Challenge, SolvedChallenge
    ).join(
        SolvedChallenge, Challenge.id == SolvedChallenge.challenge_id
    ).filter(
        SolvedChallenge.user_id == current_user.id
    ).order_by(
        SolvedChallenge.solution_time.desc()
    ).paginate(page=page, per_page=current_app.config.get('CHALLENGES_PER_PAGE', 10))

    return render_template('challenges/solved.html', title='Solved Challenges',
                          solved_challenges=solved_challenges)

@challenges.route('/leaderboard')
@login_required # Leaderboard visible to logged-in users
def leaderboard():
    # Get users with the most solved challenges (Total)
    top_solvers = db.session.query(
        User.id, User.username, db.func.count(SolvedChallenge.id).label('solved_count')
    ).join(
        SolvedChallenge, User.id == SolvedChallenge.user_id
    ).group_by(
        User.id
    ).order_by(
        desc('solved_count')
    ).limit(20).all()

    # Get users with the most hard challenges solved
    top_hard_solvers = db.session.query(
        User.id, User.username, db.func.count(SolvedChallenge.id).label('hard_count')
    ).join(
        SolvedChallenge, User.id == SolvedChallenge.user_id
    ).join(
        Challenge, SolvedChallenge.challenge_id == Challenge.id
    ).filter(
        Challenge.difficulty == 'hard'
    ).group_by(
        User.id
    ).order_by(
        desc('hard_count')
    ).limit(10).all()

    return render_template('challenges/leaderboard.html', title='Leaderboard',
                          top_solvers=top_solvers, top_hard_solvers=top_hard_solvers)