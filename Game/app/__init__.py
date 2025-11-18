# app/__init__.py

from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_migrate import Migrate
import os

# Initialize extensions - Global variables
db = SQLAlchemy()
login_manager = LoginManager()
bcrypt = Bcrypt()
migrate = Migrate()

def create_app():
    app = Flask(__name__)
    app.config.from_object('app.config.Config')

    # Initialize extensions with app
    db.init_app(app)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    migrate.init_app(app, db) # Initialize Migrate with app AND db

    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'

    # Import and register blueprints
    from app.auth.routes import auth
    from app.admin.routes import admin
    from app.challenges import challenges
    from app.marketplace.routes import marketplace

    app.register_blueprint(auth)
    app.register_blueprint(admin)
    app.register_blueprint(challenges)
    app.register_blueprint(marketplace)

    # Import models (needed for create_all and migrate)
    from app.models import User, Challenge, Product, Purchase, SolvedChallenge

    # REMOVE the @app.before_first_request function entirely
    # db.create_all() will be handled elsewhere

    # Register main routes
    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/access')
    def access():
        return render_template('access.html')

    return app
